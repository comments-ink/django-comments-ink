from django.urls import include, path, re_path
from django_comments.views.comments import comment_done
from django_comments.views.moderation import (
    approve,
    approve_done,
    delete,
    delete_done,
    flag_done,
)
from django_comments_ink.conf import settings
from django_comments_ink.views.base import CommentUrlView
from django_comments_ink.views.commenting import (
    confirm,
    sent,
    PostCommentView,
    ReplyCommentView,
)
from django_comments_ink.views.flagging import FlagCommentView
from django_comments_ink.views.muting import MuteCommentView
from django_comments_ink.views.reacting import (
    ReactToCommentDoneView,
    ReactToCommentView,
    ReactToObjectView,
    ReactedToCommentUserListView,
    ReactedToObjectUserListView,
)
from django_comments_ink.views.voting import (
    VoteCommentDoneView,
    VoteCommentView,
)
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = [
    # re_path(r"^post/$", views.post, name="comments-ink-post"),
    re_path(r"^post/$", PostCommentView.as_view(), name="comments-ink-post"),
    re_path(r"^posted/$", comment_done, name="comments-comment-done"),
    re_path(r"^sent/$", sent, name="comments-ink-sent"),
    re_path(r"^confirm/(?P<key>[^/]+)/$", confirm, name="comments-ink-confirm"),
    re_path(
        r"^mute/(?P<key>[^/]+)/$",
        MuteCommentView.as_view(),
        name="comments-ink-mute",
    ),
    re_path(
        r"^reply/(\d+)/$",
        ReplyCommentView.as_view(),
        # views.reply,
        name="comments-ink-reply",
    ),
    # Remap comments-flag to check allow-flagging is enabled.
    re_path(r"^flag/(\d+)/$", FlagCommentView.as_view(), name="comments-flag"),
    re_path(r"^flagged/$", flag_done, name="comments-flag-done"),
    re_path(r"^delete/(\d+)/$", delete, name="comments-delete"),
    re_path(r"^deleted/$", delete_done, name="comments-delete-done"),
    re_path(r"^approve/(\d+)/$", approve, name="comments-approve"),
    re_path(r"^approved/$", approve_done, name="comments-approve-done"),
    re_path(
        r"^vote/(\d+)/$", VoteCommentView.as_view(), name="comments-ink-vote"
    ),
    re_path(
        r"^voted/$",
        VoteCommentDoneView.as_view(),
        name="comments-ink-vote-done",
    ),
    re_path(
        r"^react/(\d+)/$",
        ReactToCommentView.as_view(),
        name="comments-ink-react",
    ),
    re_path(
        r"^reacted/$",
        ReactToCommentDoneView.as_view(),
        name="comments-ink-react-done",
    ),
    re_path(
        r"^list-reacted/(\d+)/([\w\+\-]+)/$",
        ReactedToCommentUserListView.as_view(),
        name="comments-ink-list-reacted",
    ),
    re_path(
        r"^react/(\d+)/(\d+)/$",
        ReactToObjectView.as_view(),
        name="comments-ink-react-to-object",
    ),
    re_path(
        r"^list-reacted/(\d+)/(\d+)/([\w\+\-]+)/$",
        ReactedToObjectUserListView.as_view(),
        name="comments-ink-list-reacted-to-object",
    ),
    re_path(
        r"^cr/(\d+)/(\d+)/(\d+)/$",
        CommentUrlView.as_view(),
        name="comments-url-redirect",
    ),
    # API handlers.
    path(
        "api/",
        include("django_comments_ink.api.urls"),
        {"override_drf_defaults": settings.COMMENTS_INK_OVERRIDE_DRF_DEFAULTS},
    ),
]


urlpatterns = format_suffix_patterns(urlpatterns)
