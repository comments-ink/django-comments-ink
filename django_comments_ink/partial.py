import logging

from django.db.models import Q
from django.template import loader
from django.utils.encoding import smart_str
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from django_comments_ink import caching, get_model, utils
from django_comments_ink.conf import settings
from django_comments_ink.paginator import CommentsPaginator
from django_comments_ink.views.templates import f_templates


logger = logging.getLogger(__name__)

page_size = settings.COMMENTS_INK_COMMENTS_PER_PAGE
num_orphans = settings.COMMENTS_INK_MAX_LAST_PAGE_ORPHANS
cpage_qs_param = settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
cfold_qs_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
max_users_in_tooltip = settings.COMMENTS_INK_MAX_USERS_IN_TOOLTIP
cache_keys = settings.COMMENTS_INK_CACHE_KEYS


class PartialTemplate:
    def __init__(
        self, content_type, object_pk, site_id, cpage, cfolded, is_authenticated
    ):
        self.content_type = content_type
        self.object_pk = object_pk
        self.site_id = site_id
        self.cpage = cpage
        self.cfolded = cfolded

        try:
            self.comments_page = int(cpage) if cpage != "last" else "last"
        except ValueError:
            raise Exception(
                _("Page is not “last”, nor can it be converted to an int.")
            )

        try:
            if len(cfolded):
                self.comments_folded = {int(cid) for cid in cfolded.split(",")}
            else:
                self.comments_folded = {}
        except (TypeError, ValueError):
            raise Exception(
                _(
                    "A comment ID in the list of folded "
                    "comments is not an integer."
                )
            )

        self.paginator = None
        self.page_obj = None
        self.is_paginated = False
        self.comment_list = []
        self.cache_key = ""

        kwargs = {
            "ctype_pk": self.content_type.pk,
            "object_pk": self.object_pk,
            "site_id": self.site_id,
        }
        comment_qs_ptn = cache_keys["comment_qs"]
        self.ckey_comment_qs = comment_qs_ptn.format(**kwargs)
        comments_paged_ptn = cache_keys["comments_paged"]
        self.ckey_comments_paged = comments_paged_ptn.format(**kwargs)
        self.max_thread_level = utils.get_max_thread_level(self.content_type)
        if is_authenticated:
            self.cmlist_ptn = cache_keys["comment_list_auth"]
        else:
            self.cmlist_ptn = cache_keys["comment_list_anon"]

        self.options = utils.get_app_model_options(
            content_type=self.content_type
        )
        check_input_allowed_str = self.options.pop("check_input_allowed")
        check_func = import_string(check_input_allowed_str)
        target_obj = content_type.get_object_for_this_type(pk=object_pk)
        self.options["is_input_allowed"] = check_func(target_obj)

    def get_queryset(self):
        # Check whether there is already a qs in the dci cache.
        qs = None
        dci_cache = caching.get_cache()
        if dci_cache != None and self.ckey_comment_qs != "":
            cached = dci_cache.get(self.ckey_comment_qs)
            if cached:
                logger.debug("Get %s from the cache", self.ckey_comment_qs)
                qs = cached

        if not qs:
            qs = get_model().objects.filter(
                content_type=self.content_type,
                object_pk=smart_str(self.object_pk),
                site__pk=self.site_id,
                level__lte=self.max_thread_level,
            )

            # The is_public and is_removed fields are implementation details
            # of the built-in comment model's spam filtering system, so they
            # might not be present on a custom comment model subclass. If they
            # exist, we should filter on them.
            field_names = [f.name for f in get_model()._meta.fields]
            if "is_public" in field_names:
                qs = qs.filter(is_public=True)
            if (
                getattr(settings, "COMMENTS_HIDE_REMOVED", True)
                and "is_removed" in field_names
            ):
                qs = qs.filter(is_removed=False)
            if "user" in field_names:
                qs = qs.select_related("user")

            if dci_cache != None and self.ckey_comment_qs != "":
                logger.debug("Adding %s to the cache", self.ckey_comment_qs)
                dci_cache.set(self.ckey_comment_qs, qs, timeout=None)

        return qs

    def filter_folded_comments(self, qs):
        if not len(self.comments_folded):
            return qs
        return qs.filter(~Q(level__gt=0, thread_id__in=self.comments_folded))

    def paginate_queryset(self, queryset):
        if page_size == 0:
            self.comment_list = queryset
            return

        self.paginator = CommentsPaginator(
            queryset,
            page_size,
            orphans=num_orphans,
            comments_folded=self.comments_folded,
            cache_key_prefix=self.ckey_comments_paged,
        )
        if self.comments_page == "last":
            page_number = self.paginator.num_pages
        else:
            page_number = self.comments_page
        self.page_obj = self.paginator.page(page_number)
        self.is_paginated = self.page_obj.has_other_pages()
        self.comment_list = self.page_obj.object_list

    def get_context(self, context=None):
        cfold_param_str = ",".join([str(cid) for cid in self.comments_folded])

        if context:
            context_dict = context.flatten()
        else:
            context_dict = {}
        context_dict.update(
            {
                "comments_page_qs_param": cpage_qs_param,
                cpage_qs_param: self.comments_page,
                "comments_folded_qs_param": cfold_qs_param,
                cfold_qs_param: cfold_param_str,
                "max_thread_level": self.max_thread_level,
                "reply_stack": [],  # List to control reply widget rendering.
                "max_users_in_tooltip": max_users_in_tooltip,
                "paginator": self.paginator,
                "page_obj": self.page_obj,
                "is_paginated": self.is_paginated,
                "comment_list": self.comment_list,
            }
        )
        context_dict.update(self.options)
        return context_dict

    def render(self, context):
        ckey_cmlist = ""
        req = context.get("request", None)
        if req:
            ckey_cmlist = self.cmlist_ptn.format(path=req.get_full_path())

        dci_cache = caching.get_cache()
        if dci_cache != None and ckey_cmlist != "":
            cached = dci_cache.get(ckey_cmlist)
            if cached:
                logger.debug("Get %s from the cache", ckey_cmlist)
                return cached

        template_list = f_templates(
            "list",
            app_label=self.content_type.app_label,
            model=self.content_type.model,
        )

        qs = self.get_queryset()
        qs = self.filter_folded_comments(qs)
        self.paginate_queryset(qs)

        context = self.get_context(context)
        result = loader.render_to_string(template_list, context)
        dci_cache.set(ckey_cmlist, result, timeout=None)
        return result
