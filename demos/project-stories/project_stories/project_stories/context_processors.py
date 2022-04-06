from django_comments_ink.conf import settings as _settings


def settings(request):
    return {"settings": _settings}
