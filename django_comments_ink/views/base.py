from urllib.parse import urlencode

from django.contrib.contenttypes.views import shortcut
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, resolve_url
from django.template import loader
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic.base import RedirectView

from django_comments_ink import get_model as get_comment_model
from django_comments_ink import signed, utils
from django_comments_ink.conf import settings
from django_comments_ink.models import InkComment, TmpInkComment
from django_comments_ink.views.templates import theme_dir


class CommentsParamsMixin:
    """A mixin for views to get django-comments-ink query string parameters."""

    comments_page_param = settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
    comments_page = None
    comments_folded_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
    comments_folded = None

    def set_comments_page(self, *args, **kwargs):
        if self.request.method == "GET":
            cpage = self.request.GET.get(self.comments_page_param, 1)
        elif self.request.method == "POST":
            cpage = self.request.POST.get(self.comments_page_param, 1)
        else:
            cpage = 1

        try:
            self.comments_page = int(cpage) if cpage != "last" else "last"
        except ValueError:
            raise Http404(
                _("Page is not “last”, nor can it be converted to an int.")
            )

    def set_comments_folded(self, *args, **kwargs):
        if self.request.method == "GET":
            cfolded = self.request.GET.get(self.comments_folded_param, "")
        elif self.request.method == "POST":
            cfolded = self.request.POST.get(self.comments_folded_param, "")
        else:
            cfolded = ""

        try:
            if len(cfolded):
                self.comments_folded = {int(cid) for cid in cfolded.split(",")}
            else:
                self.comments_folded = {}
        except (TypeError, ValueError):
            raise Http404(
                _(
                    "A comment ID in the list of folded "
                    "comments is not an integer."
                )
            )

    def read_comments_params(self, *args, **kwargs):
        if self.comments_page == None:
            self.set_comments_page(*args, **kwargs)
        if self.comments_folded == None:
            self.set_comments_folded(*args, **kwargs)

    def get_comment_qs_params(self, *args, **kwargs):
        qs_params = []
        self.read_comments_params(*args, **kwargs)

        if self.comments_page != None and self.comments_page != 1:
            qs_params.append(f"{self.comments_page_param}={self.comments_page}")

        if self.comments_folded != None and len(self.comments_folded):
            cfolded = ",".join([str(cid) for cid in self.comments_folded])
            qs_params.append(f"{self.comments_folded_param}={cfolded}")

        return qs_params

    def get_comments_params_dict(self):
        params = {}
        self.read_comments_params()

        params["comments_page_qs_param"] = self.comments_page_param
        params["comments_page"] = self.comments_page

        params["comments_folded_qs_param"] = self.comments_folded_param
        cfolded = ",".join([str(cid) for cid in self.comments_folded])
        params["comments_folded"] = cfolded

        return params

    def get_next_redirect_url(self, fallback, **kwargs):
        self.read_comments_params()
        next = self.request.POST.get("next")

        if not url_has_allowed_host_and_scheme(
            url=next, allowed_hosts={self.request.get_host()}
        ):
            next = resolve_url(fallback)

        if self.comments_page != 1:
            kwargs[self.comments_page_param] = self.comments_page
        if len(self.comments_folded):
            cfolded = ",".join([str(cid) for cid in self.comments_folded])
            kwargs[self.comments_folded_param] = cfolded

        if kwargs:
            if "#" in next:
                tmp = next.rsplit("#", 1)
                next = tmp[0]
                anchor = "#" + tmp[1]
            else:
                anchor = ""

            joiner = ("?" in next) and "&" or "?"
            next += joiner + urlencode(kwargs) + anchor

        return next


# ---------------------------------------------------------------------
class CommentUrlView(CommentsParamsMixin, RedirectView):
    permanent = False

    def set_comments_page(self, comment_id):
        cpage = self.request.GET.get(self.comments_page_param, None)
        if cpage == None:
            self.set_comments_folded()
            comment = InkComment.norel_objects.get(pk=comment_id)
            self.comments_page = utils.get_comment_page_number(
                self.request, comment, self.comments_folded
            )
        else:
            super().set_comments_page()

    def get_redirect_url(self, content_type_id, object_id, comment_id):
        qs_params = self.get_comment_qs_params(comment_id)
        response = shortcut(self.request, content_type_id, object_id)

        if len(qs_params):
            url = f"{response.url}?{'&'.join(qs_params)}"
        else:
            url = response.url

        return url


# ---------------------------------------------------------------------
class JsonResponseMixin:
    def json_response(self, template_list, context, status):
        html = loader.render_to_string(template_list, context, self.request)
        json_context = {
            "html": html,
            "reply_to": self.request.POST.get("reply_to", "0"),
        }
        if "field_focus" in context:
            json_context.update({"field_focus": context["field_focus"]})
        return JsonResponse(json_context, status=status)


# ---------------------------------------------------------------------
class SingleCommentView(CommentsParamsMixin, JsonResponseMixin, DetailView):
    context_object_name = "comment"
    model = get_comment_model()
    check_option = None
    is_ajax = False
    template_list = None
    template_list_js = None

    def get_object(self, comment_id):
        comment = get_object_or_404(
            self.model,
            pk=comment_id,
            site__pk=utils.get_current_site_id(self.request),
        )
        self.options = utils.get_app_model_options(
            content_type=comment.content_type
        )

        if self.check_option != None:
            utils.check_option(self.check_option, options=self.options)

        check_input_allowed_str = self.options.pop("check_input_allowed")
        check_func = import_string(check_input_allowed_str)
        target_obj = comment.content_type.get_object_for_this_type(
            pk=comment.object_pk
        )
        self.is_input_allowed = check_func(target_obj)

        if not self.is_input_allowed:
            raise Http404(_("Input is not allowed."))

        return comment

    def get_template_names(self, is_ajax=False):
        if is_ajax:
            template_list = self.template_list_js
        else:
            template_list = self.template_list

        if template_list is None:
            raise ImproperlyConfigured(
                "SingleCommentView requires either a definition of "
                "'template_list' or an implementation of 'get_template_names()'"
            )

        return [
            pth.format(
                theme_dir=theme_dir,
                app_label=self.object.content_object._meta.app_label,
                model=self.object.content_object._meta.model_name,
            )
            for pth in template_list
        ]

    def get_context_data(self, **kwargs):
        kwargs.update(self.options)
        kwargs.update(self.get_comments_params_dict())
        context = super().get_context_data(
            is_input_allowed=self.is_input_allowed, **kwargs
        )
        return context


# ---------------------------------------------------------------------
class SingleTmpCommentView(DetailView):
    http_method_names = [
        "get",
    ]
    template_list = None

    def get_object(self, key):
        return signed.loads(str(key), extra_key=settings.COMMENTS_INK_SALT)

    def get_template_names(self):
        if self.template_list is None:
            raise ImproperlyConfigured(
                "SingleTmpCommentView requires either a definition of "
                "'template_list' or an implementation of 'get_template_names()'"
            )

        return [
            pth.format(
                theme_dir=theme_dir,
                app_label=self.object.content_type.app_label,
                model=self.object.content_type.model,
            )
            for pth in self.template_list
        ]
