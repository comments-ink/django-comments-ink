from django.urls import reverse
from django_comments_ink import get_form_target


def test_get_form_target():
    assert get_form_target() == reverse("comments-ink-post")
