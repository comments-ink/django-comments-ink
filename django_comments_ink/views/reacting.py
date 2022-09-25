import logging

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import F
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic import DetailView, ListView

from django_comments_ink import (
    get_comment_reactions_enum,
    get_model as get_comment_model,
    get_object_reactions_enum,
    signals,
    utils,
)
from django_comments_ink.conf import settings
from django_comments_ink.models import CommentReaction, ObjectReaction
from django_comments_ink.views.base import (
    CommentsParamsMixin,
    JsonResponseMixin,
    SingleCommentView,
)
from django_comments_ink.views.templates import theme_dir, themed_templates


logger = logging.getLogger(__name__)

decorators = [csrf_protect, login_required]


# ---------------------------------------------------------
@method_decorator(decorators, name="dispatch")
class ReactToCommentView(SingleCommentView):
    http_method_names = ["get", "post"]
    check_option = "comment_reactions_enabled"
    template_list = themed_templates("react")
    template_list_js = themed_templates("reacted_js")
    context_object_name = "comment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_users_in_tooltip = getattr(
            settings, "COMMENTS_INK_MAX_USERS_IN_TOOLTIP", 10
        )
        context["max_users_in_tooltip"] = max_users_in_tooltip
        return context

    def perform_react(self):
        created = False
        reaction = self.request.POST["reaction"]
        creaction_qs = CommentReaction.objects.filter(
            reaction=reaction, comment=self.object
        )

        if creaction_qs.filter(authors=self.request.user).count() == 1:
            if creaction_qs[0].counter == 1:
                creaction_qs[0].delete_from_cache()
                creaction_qs.delete()
            else:
                creaction_qs.update(counter=F("counter") - 1)
                creaction_qs[0].delete_from_cache()
                creaction_qs[0].authors.remove(self.request.user)
        else:
            reaction_obj, created = CommentReaction.objects.get_or_create(
                reaction=reaction, comment=self.object
            )
            reaction_obj.authors.add(self.request.user)
            reaction_obj.counter += 1
            reaction_obj.save()

        signals.comment_got_a_reaction.send(
            sender=self.object.__class__,
            comment=self.object,
            reaction=reaction,
            created=created,
            request=self.request,
        )
        return created

    def get(self, request, comment_id, next=None):
        self.object = self.get_object(comment_id)

        user_reactions = []
        user_reactions_qs = CommentReaction.objects.filter(
            comment=self.object, authors=request.user
        )

        for reaction_obj in user_reactions_qs:
            user_reactions.append(
                get_comment_reactions_enum()(reaction_obj.reaction)
            )

        context = self.get_context_data(
            user_reactions=user_reactions, next=next
        )
        return self.render_to_response(context)

    def post(self, request, comment_id, next=None):
        self.object = self.get_object(comment_id)

        try:
            with transaction.atomic():
                created = self.perform_react()
        except Exception as exc:
            created = False
            logger.error(exc)

        if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
            template_list = self.get_template_names(is_ajax=True)
            context = self.get_context_data()
            status = 201 if created else 200
            return self.json_response(template_list, context, status)

        next_redirect_url = self.get_next_redirect_url(
            next or "comments-ink-react-done", c=self.object.pk
        )
        return HttpResponseRedirect(next_redirect_url)


# ---------------------------------------------------------
@method_decorator(decorators, name="dispatch")
class ReactToCommentDoneView(SingleCommentView):
    http_method_names = [
        "get",
    ]
    check_option = "comment_reactions_enabled"
    template_list = themed_templates("reacted")
    context_object_name = "comment"

    def get(self, request):
        comment_id = request.GET.get("c", None)
        self.object = self.get_object(comment_id)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


# ---------------------------------------------------------
class ReactedToCommentUserListView(ListView):
    http_method_names = ["get"]
    allow_empty = False
    paginate_by = settings.COMMENTS_INK_USERS_REACTED_PER_PAGE
    ordering = settings.COMMENTS_INK_USERS_REACTED_LIST_ORDER
    template_list = themed_templates("users_reacted_to_comment")

    def get_queryset(self):
        self.queryset = self.reaction.authors
        return super().get_queryset()

    def get_template_names(self):
        if self.template_list is None:
            raise ImproperlyConfigured(
                "ReactingUserListView requires either a definition of "
                "'template_list' or an implementation of 'get_template_names()'"
            )

        return [
            pth.format(
                theme_dir=theme_dir,
                app_label=self.comment.content_object._meta.app_label,
                model=self.comment.content_object._meta.model_name,
            )
            for pth in self.template_list
        ]

    def get(self, request, comment_id, reaction_value):
        self.comment = get_object_or_404(
            get_comment_model(),
            pk=comment_id,
            site__pk=utils.get_current_site_id(self.request),
        )
        self.reaction = get_object_or_404(
            CommentReaction, reaction=reaction_value, comment=self.comment
        )
        reaction_enum = get_comment_reactions_enum()(self.reaction.reaction)

        self.object_list = self.get_queryset()

        max_users_in_tooltip = settings.COMMENTS_INK_MAX_USERS_IN_TOOLTIP
        if self.object_list.count() <= max_users_in_tooltip:
            raise Http404(_("Not enough users"))

        context = self.get_context_data(
            comment=self.comment, reaction=reaction_enum
        )
        return self.render_to_response(context)


# ---------------------------------------------------------
# Implements react-to-object.


@method_decorator(decorators, name="dispatch")
class ReactToObjectView(CommentsParamsMixin, JsonResponseMixin, DetailView):
    http_method_names = ["post"]
    check_option = "object_reactions_enabled"
    template_list = []
    content_type = None
    object = None

    def get_content_type(self, content_type_id):
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
        except Exception:
            raise Http404(
                "ContentType with ID %d does not exist" % content_type_id
            )
        return content_type

    def get_object(self, content_type, object_pk):
        try:
            object = content_type.get_object_for_this_type(pk=object_pk)
        except Exception:
            raise Http404(
                "Object referenced by pair (ctype_id, obj_id): (%d, %d) "
                "does not exist" % (content_type.pk, object_pk)
            )

        if self.check_option == None:
            return object

        utils.check_option(self.check_option, content_type=content_type)
        options = utils.get_app_model_options(content_type=content_type)
        check_input_allowed_str = options.pop("check_input_allowed")
        check_func = import_string(check_input_allowed_str)
        target_obj = content_type.get_object_for_this_type(pk=object_pk)
        self.is_input_allowed = check_func(target_obj)

        if not self.is_input_allowed:
            raise Http404("Input is not allowed")
        else:
            return object

    def perform_react_to_object(self):
        """Save the user reaction and send the signal object_got_a_reaction."""
        created = False
        site = get_current_site(self.request)
        reaction = self.request.POST["reaction"]
        oreaction_qs = ObjectReaction.objects.filter(
            reaction=reaction,
            content_type=self.content_type,
            object_pk=self.object.pk,
            site=site,
        )

        if oreaction_qs.filter(authors=self.request.user).count() == 1:
            if oreaction_qs[0].counter == 1:
                oreaction_qs[0].delete_from_cache()
                oreaction_qs.delete()
            else:
                oreaction_qs.update(counter=F("counter") - 1)
                oreaction_qs[0].delete_from_cache()
                oreaction_qs[0].authors.remove(self.request.user)
        else:
            obj_reaction, created = ObjectReaction.objects.get_or_create(
                reaction=reaction,
                content_type=self.content_type,
                object_pk=self.object.pk,
                site=site,
            )
            obj_reaction.authors.add(self.request.user)
            obj_reaction.counter += 1
            obj_reaction.save()

        signals.object_got_a_reaction.send(
            sender=self.object.__class__,
            object=self.object,
            reaction=reaction,
            created=created,
            request=self.request,
        )
        return created

    def post(self, request, content_type_id, object_pk, next=None):
        self.content_type = self.get_content_type(content_type_id)
        self.object = self.get_object(self.content_type, object_pk)

        try:
            with transaction.atomic():
                self.perform_react_to_object()
        except Exception as exc:
            logger.error(exc)

        next_redirect_url = self.get_next_redirect_url(
            next or request.POST.get("next")
        )
        return HttpResponseRedirect(next_redirect_url)


# ---------------------------------------------------------
class ReactedToObjectUserListView(ListView):
    http_method_names = ["get"]
    allow_empty = False
    paginate_by = settings.COMMENTS_INK_USERS_REACTED_PER_PAGE
    ordering = settings.COMMENTS_INK_USERS_REACTED_LIST_ORDER
    template_list = themed_templates("users_reacted_to_object")

    def get_queryset(self):
        self.queryset = self.reaction.authors
        return super().get_queryset()

    def get_template_names(self):
        if self.template_list is None:
            raise ImproperlyConfigured(
                "ReactingUserListView requires either a definition of "
                "'template_list' or an implementation of 'get_template_names()'"
            )

        return [
            pth.format(
                theme_dir=theme_dir,
                app_label=self.ctype.app_label,
                model=self.ctype.model,
            )
            for pth in self.template_list
        ]

    def get(self, request, content_type_id, object_pk, reaction_value):
        try:
            self.ctype = ContentType.objects.get(pk=content_type_id)
            self.ctype.get_object_for_this_type(pk=object_pk)
        except Exception:
            raise Http404(
                "Object referenced by pair (ctype_id, obj_id): (%d, %d) "
                "does not exist" % (content_type_id, object_pk)
            )

        self.reaction = get_object_or_404(
            ObjectReaction,
            reaction=reaction_value,
            content_type=self.ctype,
            object_pk=object_pk,
            site=get_current_site(request),
        )
        reaction_enum = get_object_reactions_enum()(self.reaction.reaction)

        self.object_list = self.get_queryset()

        max_users_in_tooltip = settings.COMMENTS_INK_MAX_USERS_IN_TOOLTIP
        if self.object_list.count() <= max_users_in_tooltip:
            raise Http404(_("Not enough users"))

        context = self.get_context_data(
            object=self.reaction.content_object, reaction=reaction_enum
        )
        return self.render_to_response(context)
