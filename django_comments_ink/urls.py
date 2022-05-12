from django.urls import include, path, re_path
from django_comments.views.comments import comment_done
from django_comments.views.moderation import (
    approve,
    approve_done,
    delete,
    delete_done,
    flag_done,
)
from django_comments_ink import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    re_path(r"^post/$", views.post, name="comments-ink-post"),
    re_path(r"^posted/$", comment_done, name="comments-comment-done"),
    re_path(r"^sent/$", views.sent, name="comments-ink-sent"),
    re_path(
        r"^confirm/(?P<key>[^/]+)/$", views.confirm, name="comments-ink-confirm"
    ),
    re_path(r"^mute/(?P<key>[^/]+)/$", views.mute, name="comments-ink-mute"),
    re_path(r"^reply/(?P<cid>[\d]+)/$", views.reply, name="comments-ink-reply"),
    # Remap comments-flag to check allow-flagging is enabled.
    re_path(r"^flag/(\d+)/$", views.flag, name="comments-flag"),
    re_path(r"^flagged/$", flag_done, name="comments-flag-done"),
    re_path(r"^delete/(\d+)/$", delete, name="comments-delete"),
    re_path(r"^deleted/$", delete_done, name="comments-delete-done"),
    re_path(r"^approve/(\d+)/$", approve, name="comments-approve"),
    re_path(r"^approved/$", approve_done, name="comments-approve-done"),
    re_path(r"^react/(\d+)/$", views.react, name="comments-ink-react"),
    re_path(r"^reacted/$", views.react_done, name="comments-ink-react-done"),
    re_path(
        r"^list-reacted/(\d+)/([\w\+\-]+)/$",
        views.list_reacted,
        name="comments-ink-list-reacted",
    ),
    re_path(
        r"^react/(\d+)/(\d+)/$",
        views.react_to_object,
        name="comments-ink-react-to-object",
    ),
    re_path(
        r"^list-reacted/(\d+)/(\d+)/([\w\+\-]+)/$",
        views.list_reacted_to_object,
        name="comments-ink-list-reacted-to-object",
    ),
    # Remap comments-url-redirect to add query string params.
    re_path(
        r"^cr/(\d+)/(\d+)/(\d+)/$",
        views.get_inkcomment_url,
        name="comments-url-redirect",
    ),
    # API handlers.
    path(
        "api/",
        include("django_comments_ink.api.urls"),
        {"override_drf_defaults": True},
    ),
]


urlpatterns = format_suffix_patterns(urlpatterns)
