from django.apps import apps
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.defaults import bad_request

from django_comments_ink import signals, signed
from django_comments_ink.models import InkComment
from django_comments_ink.views.base import SingleTmpCommentView
from django_comments_ink.views.commenting import get_comment_if_exists
from django_comments_ink.views.templates import themed_templates


class MuteCommentView(SingleTmpCommentView):
    template_list = themed_templates("muted")

    def get_object(self, key):
        tmp_comment = super().get_object(key)

        # Can't mute a comment that doesn't have the followup attribute
        # set to True, or a comment that doesn't exist.
        if (
            not tmp_comment.followup
            or get_comment_if_exists(tmp_comment) is None
        ):
            raise Http404(_("Comment already muted or comment does not exist."))

        return tmp_comment

    def perform_mute(self):
        InkComment.norel_objects.filter(
            content_type=self.object.content_type,
            object_pk=self.object.object_pk,
            user_email=self.object.user_email,
            is_public=True,
            followup=True,
        ).update(followup=False)

        # Send signal that the comment thread has been muted
        signals.comment_thread_muted.send(
            sender=InkComment, comment=self.object, request=self.request
        )

    def get(self, request, key):
        try:
            self.object = self.get_object(key)
        except (ValueError, signed.BadSignature) as exc:
            return bad_request(request, exc)
        model = apps.get_model(
            self.object.content_type.app_label, self.object.content_type.model
        )
        target = model._default_manager.get(pk=self.object.object_pk)
        self.perform_mute()
        context = self.get_context_data(content_object=target)
        return self.render_to_response(context)
