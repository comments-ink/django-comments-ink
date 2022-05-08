import logging
from collections import OrderedDict

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import signing
from django.db import models
from django.db.models import F, Max, Min, Prefetch, Q
from django.db.models.signals import post_delete
from django.db.transaction import atomic
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_comments.managers import CommentManager
from django_comments.models import Comment, CommentFlag
from django_comments_ink import (
    caching,
    get_comment_reactions_enum,
    get_model,
    get_object_reactions_enum,
)
from django_comments_ink.conf import settings
from django_comments_ink.utils import get_current_site_id

logger = logging.getLogger(__name__)


def max_thread_level_for_content_type(content_type):
    app_model = "%s.%s" % (content_type.app_label, content_type.model)
    if app_model in settings.COMMENTS_INK_MAX_THREAD_LEVEL_BY_APP_MODEL:
        return settings.COMMENTS_INK_MAX_THREAD_LEVEL_BY_APP_MODEL[app_model]
    else:
        return settings.COMMENTS_INK_MAX_THREAD_LEVEL


class MaxThreadLevelExceededException(Exception):
    def __init__(self, comment):
        self.comment = comment
        # self.max_by_app = max_thread_level_for_content_type(content_type)

    def __str__(self):
        return "Max thread level reached for comment %d" % self.comment.id


class InkCommentManager(CommentManager):
    def for_app_models(self, *args, **kwargs):
        """Return comments for pairs "app.model" given in args"""
        content_types = []
        for app_model in args:
            app, model = app_model.split(".")
            content_types.append(
                ContentType.objects.get(app_label=app, model=model)
            )
        return self.for_content_types(content_types, **kwargs)

    def for_content_types(self, content_types, site=None):
        filter_fields = {"content_type__in": content_types}
        if site is not None:
            filter_fields["site"] = site
        qs = self.get_queryset().filter(**filter_fields).reverse()
        return qs

    def get_queryset(self):
        qs = super(InkCommentManager, self).get_queryset()
        return qs.select_related("user", "content_type").order_by(
            *settings.COMMENTS_INK_LIST_ORDER
        )


class InkComment(Comment):
    thread_id = models.IntegerField(default=0, db_index=True)
    parent_id = models.IntegerField(default=0)
    level = models.SmallIntegerField(default=0)
    order = models.IntegerField(default=1, db_index=True)
    followup = models.BooleanField(
        blank=True, default=False, help_text=_("Notify follow-up comments")
    )
    nested_count = models.IntegerField(default=0, db_index=True)
    objects = InkCommentManager()
    norel_objects = CommentManager()

    def get_absolute_url(self, anchor_pattern="#comment-%(id)s"):
        return reverse(
            "comments-url-redirect",
            args=(self.content_type_id, self.object_pk, self.pk),
        ) + (anchor_pattern % self.__dict__)

    def save(self, *args, **kwargs):
        caching.clear_cache(self.content_type.id, self.object_pk, self.site.pk)
        is_new = self.pk is None
        super(Comment, self).save(*args, **kwargs)
        if is_new:
            if not self.parent_id:
                self.parent_id = self.id
                self.thread_id = self.id
            else:
                if max_thread_level_for_content_type(self.content_type):
                    with atomic():
                        self._calculate_thread_data()
                else:
                    raise MaxThreadLevelExceededException(self)
            kwargs["force_insert"] = False
            super(Comment, self).save(*args, **kwargs)

    def _calculate_thread_data(self):
        # Implements the following approach:
        #  http://www.sqlteam.com/article/sql-for-threaded-discussion-forums
        parent = InkComment.objects.get(pk=self.parent_id)
        if parent.level == max_thread_level_for_content_type(self.content_type):
            raise MaxThreadLevelExceededException(self)

        self.thread_id = parent.thread_id
        self.level = parent.level + 1
        qc_eq_thread = InkComment.norel_objects.filter(
            thread_id=parent.thread_id
        )
        qc_ge_level = qc_eq_thread.filter(
            level__lte=parent.level, order__gt=parent.order
        )
        if qc_ge_level.count():
            min_order = qc_ge_level.aggregate(Min("order"))["order__min"]
            qc_eq_thread.filter(order__gte=min_order).update(
                order=F("order") + 1
            )
            self.order = min_order
        else:
            max_order = qc_eq_thread.aggregate(Max("order"))["order__max"]
            self.order = max_order + 1

        if self.id != parent.id:
            parent_ids = []
            while True:
                parent_ids.append(parent.pk)
                if parent.id == parent.parent_id:
                    break
                parent = qc_eq_thread.get(pk=parent.parent_id)
            if parent_ids:
                qc_eq_thread.filter(pk__in=parent_ids).update(
                    nested_count=F("nested_count") + 1
                )

    def get_reply_url(self):
        return reverse("comments-ink-reply", kwargs={"cid": self.pk})

    def allow_thread(self):
        if self.level < max_thread_level_for_content_type(self.content_type):
            return True
        else:
            return False

    def get_reactions(self):
        dci_cache = caching.get_cache()
        key = settings.COMMENTS_INK_CACHE_KEYS["comment_reactions"].format(
            comment_id=self.pk
        )
        if dci_cache != None and key != "":
            result = dci_cache.get(key)
            if result != None:
                logger.debug("Fetching %s from the cache", key)
                return result

        total_counter = 0
        max_users_listed = getattr(
            settings, "COMMENTS_INK_MAX_USERS_IN_TOOLTIP", 10
        )
        reactions = OrderedDict([(k, {}) for k in get_comment_reactions_enum()])
        # First add the existing reactions sorted by reaction value.
        for item in self.reactions.order_by("reaction"):
            total_counter += item.counter
            reaction = get_comment_reactions_enum()(item.reaction)
            authors = [
                settings.COMMENTS_INK_API_USER_REPR(author)
                for author in item.authors.all()[:max_users_listed]
            ]
            reactions[reaction.value] = {
                "value": reaction.value,
                "authors": authors,
                "counter": item.counter,
                "label": reaction.label,
                "icon": reaction.icon,
            }
        # Return only the values of OrderedDict after it's being sorted.
        result = {
            "counter": total_counter,
            "list": [v for k, v in reactions.items() if len(v)],
        }
        if dci_cache != None and key != "":
            dci_cache.set(key, result, timeout=None)
            logger.debug("Caching reactions for comment %d" % self.pk)
        return result

    @staticmethod
    def get_queryset(
        content_type=None, object_pk=None, content_object=None, site_id=None
    ):
        """
        Given either a content_object or the pair content_type and object_pk
        it returns the queryset with the comments posted to that object.
        """
        if content_object is None and (
            content_type is None or object_pk is None
        ):
            return None

        if content_object:
            content_type = ContentType.objects.get_for_model(content_object)
            object_pk = content_object.id

        flags = CommentFlag.objects.filter(
            flag__in=[CommentFlag.SUGGEST_REMOVAL]
        ).prefetch_related("user")

        reactions = CommentReaction.objects.all().prefetch_related("authors")

        prefetch_args = [
            Prefetch("flags", queryset=flags),
            Prefetch("reactions", queryset=reactions),
        ]

        fkwds = {
            "content_type": content_type,
            "object_pk": object_pk,
            "site__pk": site_id or get_current_site_id(),
            "is_public": True,
        }

        hide_removed = getattr(settings, "COMMENTS_HIDE_REMOVED", True)
        if hide_removed:
            fkwds["is_removed"] = False

        return (
            get_model().objects.prefetch_related(*prefetch_args).filter(**fkwds)
        )


def publish_or_withhold_nested_comments(comment, shall_be_public=False):
    qs = get_model().norel_objects.filter(
        ~Q(pk=comment.id), parent_id=comment.id
    )
    nested = [cm.id for cm in qs]
    qs.update(is_public=shall_be_public)
    while len(nested):
        cm_id = nested.pop()
        qs = get_model().norel_objects.filter(~Q(pk=cm_id), parent_id=cm_id)
        nested.extend([cm.id for cm in qs])
        qs.update(is_public=shall_be_public)
    # Update nested_count in parents comments in the same thread.
    # The comment.nested_count doesn't change because the comment's is_public
    # attribute is not changing, only its nested comments change, and it will
    # help to re-populate nested_count should it be published again.
    if shall_be_public:
        op = F("nested_count") + comment.nested_count
    else:
        op = F("nested_count") - comment.nested_count
    get_model().norel_objects.filter(
        thread_id=comment.thread_id,
        level__lt=comment.level,
        order__lt=comment.order,
    ).update(nested_count=op)


def publish_or_withhold_on_pre_save(sender, instance, raw, using, **kwargs):
    if not raw and instance and instance.id:
        shall_be_public = (not instance.is_removed) and instance.is_public
        publish_or_withhold_nested_comments(instance, shall_be_public)


def on_comment_deleted(sender, instance, using, **kwargs):
    # Create the list of nested ink-comments that have to deleted too.
    qs = get_model().norel_objects.filter(
        ~Q(pk=instance.id), parent_id=instance.id
    )
    nested = [cm.id for cm in qs]
    for cm_id in nested:
        qs = get_model().norel_objects.filter(~Q(pk=cm_id), parent_id=cm_id)
        nested.extend([cm.id for cm in qs])

    # Update the nested_count attribute up the tree.
    get_model().norel_objects.filter(
        thread_id=instance.thread_id,
        level__lt=instance.level,
        order__lt=instance.order,
    ).update(nested_count=F("nested_count") - instance.nested_count - 1)

    # Delete all reactions, and reaction authors, associated
    # with nested instances.
    creactions_qs = CommentReaction.objects.filter(comment__pk__in=nested)
    creactions_ids = [cr.id for cr in creactions_qs]

    CommentReactionAuthor.objects.filter(
        reaction__pk__in=creactions_ids
    )._raw_delete(using)
    creactions_qs._raw_delete(using)

    # Delete all the comments down the tree from instance.
    get_model().objects.filter(pk__in=nested)._raw_delete(using)


post_delete.connect(on_comment_deleted, sender=InkComment)

# ----------------------------------------------------------------------


class DummyDefaultManager:
    """
    Dummy Manager to mock django's CommentForm.check_for_duplicate method.
    """

    def __getattr__(self, name):
        return lambda *args, **kwargs: []

    def using(self, *args, **kwargs):
        return self


class TmpInkComment(dict):
    """
    Temporary InkComment to be pickled, ziped and appended to a URL.
    """

    _default_manager = DummyDefaultManager()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def save(self, *args, **kwargs):
        pass

    def _get_pk_val(self):
        if self.ink_comment:
            return self.ink_comment._get_pk_val()
        else:
            content_type = "%s.%s" % self.content_type.natural_key()
            return signing.dumps("%s:%s" % (content_type, self.object_pk))

    def __setstate__(self, state):
        ct_key = state.pop("content_type_key")
        ctype = ContentType.objects.get_by_natural_key(*ct_key)
        self.update(
            state,
            content_type=ctype,
            content_object=ctype.get_object_for_this_type(
                pk=state["object_pk"]
            ),
        )

    def __reduce__(self):
        state = {k: v for k, v in self.items() if k != "content_object"}
        ct = state.pop("content_type")
        state["content_type_key"] = ct.natural_key()
        return (TmpInkComment, (), state)


# ----------------------------------------------------------------------
class BlackListedDomain(models.Model):
    """
    A blacklisted domain from which comments should be discarded.
    Automatically populated with a small amount of spamming domains,
    gathered from http://www.joewein.net/spam/blacklist.htm

    You can download for free a recent version of the list, and subscribe
    to get notified on changes. Changes can be fetched with rsync for a
    small fee (check their conditions, or use any other Spam filter).
    """

    domain = models.CharField(max_length=200, db_index=True)

    def __str__(self):
        return self.domain

    class Meta:
        ordering = ("domain",)


# ----------------------------------------------------------------------
class BaseReactionEnum(models.TextChoices):
    @classmethod
    def set_icons(cls, icons):
        cls._icons = icons

    @property
    def icon(self):
        return self._icons[self]


class ReactionEnum(BaseReactionEnum):
    LIKE_IT = "+", "+1"
    DISLIKE_IT = "-", "-1"


ReactionEnum.set_icons(
    {ReactionEnum.LIKE_IT: "#128077", ReactionEnum.DISLIKE_IT: "#128078"}
)


class ReactionField(models.TextField):
    description = "Code representing a user reaction to a comment"

    def deconstruct(self):
        name, path, args, kwargs = super(ReactionField, self).deconstruct()
        kwargs.pop("choices", None)  # Ignore choice changes in migrations.
        return name, path, args, kwargs


# It allows the implementation of two models:
#  * CommentReaction
#  * ObjectReaction

# -----------------------------------------------
# Comment reaction model.


class CommentReaction(models.Model):
    reaction = ReactionField(
        _("reaction"),
        db_index=True,
        choices=get_comment_reactions_enum().choices,
    )
    comment = models.ForeignKey(
        get_model(),
        verbose_name=_("reactions"),
        related_name="reactions",
        on_delete=models.CASCADE,
    )
    counter = models.IntegerField(default=0)
    authors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="CommentReactionAuthor",
        through_fields=("reaction", "author"),
    )

    class Meta:
        verbose_name = _("comment reactions")
        verbose_name_plural = _("comments reactions")

    def delete_from_cache(self):
        dci_cache = caching.get_cache()
        key = settings.COMMENTS_INK_CACHE_KEYS["comment_reactions"].format(
            comment_id=self.comment.pk
        )
        if dci_cache != None and key != "" and dci_cache.get(key):
            logger.debug(
                "Delete cached list of comment reactions in key %s" % key
            )
            dci_cache.delete(key)

    def save(self, *args, **kwargs):
        self.delete_from_cache()
        super(CommentReaction, self).save(*args, **kwargs)


class CommentReactionAuthor(models.Model):
    reaction = models.ForeignKey(CommentReaction, on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )


# -----------------------------------------------
# Object reaction model.


class ObjectReaction(models.Model):
    reaction = ReactionField(
        _("reaction"),
        db_index=True,
        choices=get_object_reactions_enum().choices,
    )
    content_type = models.ForeignKey(
        ContentType,
        verbose_name=_("content type"),
        related_name="content_type_set_for_%(class)s",
        on_delete=models.CASCADE,
    )
    object_pk = models.CharField(_("object ID"), db_index=True, max_length=64)
    content_object = GenericForeignKey(
        ct_field="content_type", fk_field="object_pk"
    )
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    counter = models.IntegerField(default=0)
    authors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ObjectReactionAuthor",
        through_fields=("reaction", "author"),
    )

    class Meta:
        verbose_name = _("object reactions")
        verbose_name_plural = _("objects reactions")

    def delete_from_cache(self):
        dci_cache = caching.get_cache()
        key = settings.COMMENTS_INK_CACHE_KEYS["object_reactions"].format(
            ctype_pk=self.content_type.id,
            object_pk=self.object_pk,
            site_id=self.site.id,
        )
        if dci_cache != None and key != "" and dci_cache.get(key):
            logger.debug(
                "Delete cached list of object reactions in key %s" % key
            )
            dci_cache.delete(key)

    def save(self, *args, **kwargs):
        self.delete_from_cache()
        super(ObjectReaction, self).save(*args, **kwargs)


class ObjectReactionAuthor(models.Model):
    reaction = models.ForeignKey(ObjectReaction, on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
