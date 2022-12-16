import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from django_comments import signals
from django_comments.models import CommentFlag

from django_comments_ink import caching
from django_comments_ink.views.base import SingleCommentView


logger = logging.getLogger(__name__)


decorators = [csrf_protect, login_required]


@method_decorator(decorators, name="dispatch")
class FlagCommentView(SingleCommentView):
    check_option = "comment_flagging_enabled"
    template_list = ["comments/flag.html"]
    template_list_js = ["comments/comment_flags.html"]
    context_object_name = "comment"

    def perform_flag(self):
        created = False
        caching.clear_item("comment_flags", comment_id=self.object.pk)

        flag_qs = CommentFlag.objects.filter(
            comment=self.object,
            user=self.request.user,
            flag=CommentFlag.SUGGEST_REMOVAL,
        )

        if flag_qs.count() == 1:
            flag_qs.delete()
        else:
            flag, created = CommentFlag.objects.get_or_create(
                comment=self.object,
                user=self.request.user,
                flag=CommentFlag.SUGGEST_REMOVAL,
            )

        signals.comment_was_flagged.send(
            sender=self.object.__class__,
            comment=self.object,
            flag=flag,
            created=created,
            request=self.request,
        )

    def get(self, request, comment_id, next=None):
        self.object = self.get_object(comment_id)
        context = self.get_context_data(object=self.object, next=next)
        user_flag_qs = CommentFlag.objects.filter(
            flag=CommentFlag.SUGGEST_REMOVAL,
            comment=self.object,
            user=request.user,
        )
        user_flagged = False if user_flag_qs.count() == 0 else True
        context["user_flagged"] = user_flagged
        return self.render_to_response(context)

    def post(self, request, comment_id, next=None):
        self.object = self.get_object(comment_id)
        try:
            self.perform_flag()
        except Exception as exc:
            logger.error(exc)

        if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
            template_list = self.get_template_names(is_ajax=True)
            context = self.get_context_data()
            status = 200
            return self.json_response(template_list, context, status)

        next_redirect_url = self.get_next_redirect_url(
            next or "comments-flag-done", c=self.object.pk
        )
        return HttpResponseRedirect(next_redirect_url)
