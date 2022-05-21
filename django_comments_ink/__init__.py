from django.urls import reverse
from django.utils.module_loading import import_string

default_app_config = "django_comments_ink.apps.CommentsInkConfig"


def get_model():
    from django_comments_ink.conf import settings

    return import_string(settings.COMMENTS_INK_MODEL)


def get_form():
    from django_comments_ink.conf import settings

    return import_string(settings.COMMENTS_INK_FORM_CLASS)


def get_comment_reactions_enum():
    from django_comments_ink.conf import settings

    return import_string(settings.COMMENTS_INK_COMMENT_REACTIONS_ENUM)


def get_object_reactions_enum():
    from django_comments_ink.conf import settings

    return import_string(settings.COMMENTS_INK_OBJECT_REACTIONS_ENUM)


def get_form_target():
    return reverse("comments-ink-post")


VERSION = (0, 0, 2, "a", 0)  # following PEP 440


def get_version():
    version = "%s.%s.%s" % (VERSION[0], VERSION[1], VERSION[2])
    if VERSION[3] != "f":
        version = "%s%s%s" % (version, VERSION[3], VERSION[4])
    return version
