from django.urls import reverse
from django_comments_ink.api.views import (
    CommentCreate,
    CreateReportFlag,
    PostCommentReaction,
)
from rest_framework.test import APIRequestFactory, force_authenticate

request_factory = APIRequestFactory()


def post_comment(data, auth_user=None):
    request = request_factory.post(reverse("comments-ink-api-create"), data)
    if auth_user:
        force_authenticate(request, user=auth_user)
    view = CommentCreate.as_view()
    return view(request)


def send_reaction(method, data, auth_user=None):
    assert method is not None
    assert method in ["get", "post", "update", "put", "delete"]
    method = getattr(request_factory, method)
    request = method(reverse("comments-ink-api-react"), data)
    if auth_user:
        force_authenticate(request, user=auth_user)
    view = PostCommentReaction.as_view()
    return view(request)


def post_flag(data, auth_user=None):
    request = request_factory.post(reverse("comments-ink-api-flag"), data)
    if auth_user:
        force_authenticate(request, user=auth_user)
    view = CreateReportFlag.as_view()
    return view(request)
