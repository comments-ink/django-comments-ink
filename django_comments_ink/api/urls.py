from django.urls import path, re_path

from .views import (
    CommentCount,
    CommentCreate,
    CommentList,
    CommentReactionAuthorList,
    CreateReportFlag,
    ObjectReactionAuthorList,
    PostCommentReaction,
    PostObjectReaction,
)

urlpatterns = [
    path("comment/", CommentCreate.as_view(), name="comments-ink-api-create"),
    path(
        "react/",
        PostCommentReaction.as_view(),
        name="comments-ink-api-react",
    ),
    path(
        "react-to-object/",
        PostObjectReaction.as_view(),
        name="comments-ink-api-react-to-object",
    ),
    path("flag/", CreateReportFlag.as_view(), name="comments-ink-api-flag"),
    re_path(
        r"^(?P<comment_pk>[\d]+)/(?P<reaction_value>[\w\+\-]+)/$",
        CommentReactionAuthorList.as_view(),
        name="comments-ink-comment-reaction-authors",
    ),
    # -----------------------------------------------------------------
    # The following 3 re_path entries read the content type as
    # <applabel>-<model>, and the object ID to which comments
    # have been sent.
    # List the comments sent to the <ctype>/<object_pk>.
    re_path(
        r"^(?P<content_type>\w+[-]{1}\w+)/(?P<object_pk>[-\w]+)/$",
        CommentList.as_view(),
        name="comments-ink-api-list",
    ),
    # Number of comments sent to the <ctype>/<object_pk>.
    re_path(
        r"^(?P<content_type>\w+[-]{1}\w+)/(?P<object_pk>[-\w]+)/count/$",
        CommentCount.as_view(),
        name="comments-ink-api-count",
    ),
    # List users that reacted with <reaction_value> to the post
    # identified with <ctype>/<object_pk>.
    re_path(
        r"^(?P<content_type>\w+[-]{1}\w+)/"
        r"(?P<object_pk>[-\w]+)/"
        r"(?P<reaction_value>[\w\+\-]+)/$",
        ObjectReactionAuthorList.as_view(),
        name="comments-ink-api-object-reaction-authors",
    ),
]
