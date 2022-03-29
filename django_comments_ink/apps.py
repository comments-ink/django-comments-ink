from django.apps import AppConfig
from django.db.models.signals import pre_save


class CommentsInkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_comments_ink"
    verbose_name = "Comments Ink"

    def ready(self):
        from django_comments_ink import get_model
        from django_comments_ink.conf import settings
        from django_comments_ink.models import publish_or_withhold_on_pre_save

        if getattr(settings, "COMMENTS_HIDE_REMOVED", True) or getattr(
            settings, "COMMENTS_INK_PUBLISH_OR_WITHHOLD_NESTED", True
        ):
            model_app_label = get_model()._meta.label
            pre_save.connect(
                publish_or_withhold_on_pre_save, sender=model_app_label
            )
