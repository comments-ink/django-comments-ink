from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import ConnectionDoesNotExist, IntegrityError
from django_comments.models import Comment
from django_comments_ink.models import InkComment

__all__ = ["Command"]


class Command(BaseCommand):
    help = "Load the inkcomment table with valid data from django_comments."

    def add_arguments(self, parser):
        parser.add_argument("using", nargs="*", type=str)

    def populate_db(self, cursor):
        for comment in Comment.objects.all():
            sql = (
                "INSERT INTO %(table)s "
                "       ('comment_ptr_id', 'thread_id', 'parent_id',"
                "        'level', 'order', 'followup', 'nested_count') "
                "VALUES (%(id)d, %(id)d, %(id)d, 0, 1, FALSE, 0)"
            )
            cursor.execute(
                sql % {"table": InkComment._meta.db_table, "id": comment.id}
            )

    def handle(self, *args, **options):
        total = 0
        using = options["using"] or ["default"]
        for db_conn in using:
            try:
                self.populate_db(connections[db_conn].cursor())
                total += InkComment.objects.using(db_conn).count()
            except ConnectionDoesNotExist:
                self.stdout.write(
                    "DB connection '%s' does not exist." % db_conn
                )
            except IntegrityError:
                if db_conn != "default":
                    self.stdout.write(
                        "Table '%s' (in '%s' DB connection) "
                        "must be empty." % (InkComment._meta.db_table, db_conn)
                    )
                else:
                    self.stdout.write(
                        "Table '%s' must be empty." % InkComment._meta.db_table
                    )
            finally:
                continue
        self.stdout.write("Added %d InkComment object(s)." % total)
