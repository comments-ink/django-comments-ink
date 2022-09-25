import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from django_comments_ink import signals
from django_comments_ink.models import CommentVote
from django_comments_ink.views.base import SingleCommentView
from django_comments_ink.views.templates import themed_templates


logger = logging.getLogger(__name__)

decorators = [csrf_protect, login_required]


# ---------------------------------------------------------
INVERSE_VOTE = {
    CommentVote.POSITIVE: CommentVote.NEGATIVE,
    CommentVote.NEGATIVE: CommentVote.POSITIVE,
}

VOTE_VALUE = {CommentVote.POSITIVE: +1, CommentVote.NEGATIVE: -1}


@method_decorator(decorators, name="dispatch")
class VoteCommentView(SingleCommentView):
    http_method_names = ["get", "post"]
    check_option = "comment_votes_enabled"
    template_list = themed_templates("vote")
    template_list_js = themed_templates("voted_js")
    context_object_name = "comment"

    def get_object(self, comment_id):
        comment = super().get_object(comment_id)
        if comment.level > 0:
            raise Http404("Input is not allowed")
        return comment

    def perform_vote(self):
        delta = 0  # To sum to thread's score.
        vote = self.request.POST["vote"]
        vote_obj, created = CommentVote.objects.get_or_create(
            vote=vote, comment=self.object, author=self.request.user
        )

        if created:
            delta = CommentVote.VALUE[vote]
            counterpart_qs = CommentVote.objects.filter(
                vote=INVERSE_VOTE[vote],
                comment=self.object,
                author=self.request.user,
            )
            if counterpart_qs.count():
                delta += VOTE_VALUE[vote]
                counterpart_qs.delete()
        else:
            delta = -VOTE_VALUE[vote]
            vote_obj.delete()

        self.object.thread.score = self.object.thread.score + delta
        self.object.thread.save()

        signals.comment_got_a_vote.send(
            sender=self.object.__class__,
            comment=self.object,
            vote=vote,
            created=created,
            request=self.request,
        )
        return created

    def get(self, request, comment_id, next=None):
        self.object = self.get_object(comment_id)
        user_votes_qs = CommentVote.objects.filter(
            comment=self.object, author=request.user
        )
        user_vote = None if user_votes_qs.count() == 0 else user_votes_qs[0]
        context = self.get_context_data(user_vote=user_vote, next=next)
        return self.render_to_response(context)

    def post(self, request, comment_id, next=None):
        self.object = self.get_object(comment_id)

        try:
            with transaction.atomic():
                created = self.perform_vote()
        except Exception as exc:
            created = False
            logger.error(exc)

        if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
            template_list = self.get_template_names(is_ajax=True)
            context = self.get_context_data()
            status = 201 if created else 200
            return self.json_response(template_list, context, status)

        next_redirect_url = self.get_next_redirect_url(
            next or "comments-ink-vote-done", c=self.object.pk
        )
        return HttpResponseRedirect(next_redirect_url)


# ---------------------------------------------------------
@method_decorator(decorators, name="dispatch")
class VoteCommentDoneView(SingleCommentView):
    http_method_names = [
        "get",
    ]
    check_option = "comment_votes_enabled"
    template_list = themed_templates("voted")
    context_object_name = "comment"

    def get_object(self, comment_id):
        comment = super().get_object(comment_id)
        if comment.level > 0:
            raise Http404("Input is not allowed")
        return comment

    def get(self, request):
        comment_id = request.GET.get("c", None)
        self.object = self.get_object(comment_id)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
