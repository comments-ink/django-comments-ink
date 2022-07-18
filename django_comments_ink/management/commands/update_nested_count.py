import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.utils import ConnectionDoesNotExist

from django_comments_ink.conf import settings
from django_comments_ink.models import InkComment


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Initialize the nested_count field for all the comments in the DB."

    def add_arguments(self, parser):
        parser.add_argument("using", nargs="*", type=str)

    def update_nested_count(self, using):
        total = 0
        ctype_list = []

        # Check if the COMMENTS_INK_MAX_THREAD_LEVEL_BY_APP_MODEL is defined
        # and if so, iterate over each group of app_label.model, and apply
        # the update of the nested_count on per app_label.model group.
        # If that setting only contains the default, then do the update to all
        # the InkComments. Otherwise use the COMMENTS_INK_MAX_THREAD_LEVEL.

        # 1st: Process comments on per app_model basis.
        MTLs = settings.COMMENTS_INK_MAX_THREAD_LEVEL_BY_APP_MODEL
        for app_model, mtl in MTLs.items():
            bits = app_model.split(".")
            app, model = ".".join(bits[:-1]), bits[-1]
            try:
                ctype = ContentType.objects.get(app_label=app, model=model)
                ctype_list.append(ctype)
            except ContentType.DoesNotExist as exc:
                logger.warn("app.model '%s' does not exist", app_model)
            else:
                qs = (
                    InkComment.objects.using(using)
                    .filter(content_type=ctype, level__lte=mtl)
                    .order_by("thread__id", "-order")
                )
                count = self.process_queryset(qs)
                total += count
                self.stdout.write(
                    f"Updated {count} InkComments for {app_model}."
                )

        if not len(MTLs):
            self.stdout.write(f"")

        # 2nd: Process the rest of the comments.
        MTL = settings.COMMENTS_INK_MAX_THREAD_LEVEL
        if len(ctype_list):
            qs = (
                InkComment.objects.using(using)
                .filter(~Q(content_type__in=ctype_list), level__lte=MTL)
                .order_by("thread__id", "-order")
            )
            count = self.process_queryset(qs)
            total += count
            self.stdout.write(f"Updated additional {count} InkComments.")
        else:
            qs = (
                InkComment.objects.using(using)
                .filter(level__lte=MTL)
                .order_by("thread__id", "-order")
            )
            total = self.process_queryset(qs)
            self.stdout.write(f"Updated {total} InkComments.")

        return total

    def process_queryset(self, qs):
        active_thread_id = -1
        parents = {}

        for comment in qs:
            # Clean up parents when there is a control break.
            if comment.thread.id != active_thread_id:
                parents = {}
                active_thread_id = comment.thread.id

            nested_count = parents.get(comment.comment_ptr_id, 0)
            parents.setdefault(comment.parent_id, 0)
            if nested_count > 0:
                parents[comment.parent_id] += 1 + nested_count
            else:
                parents[comment.parent_id] += 1
            comment.nested_count = nested_count
            comment.save()

        return qs.count()

    def handle(self, *args, **options):
        total = 0
        using = options["using"] or ["default"]

        for db_conn in using:
            try:
                total += self.update_nested_count(db_conn)
            except ConnectionDoesNotExist:
                self.stdout.write(
                    "DB connection '%s' does not exist." % db_conn
                )
                continue
        self.stdout.write(
            "%d InkComment object(s) processed in all DBs." % total
        )
