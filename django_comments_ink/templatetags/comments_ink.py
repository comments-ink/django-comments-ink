import hashlib
import json
import logging
import re
from urllib.parse import urlencode

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import InvalidPage, PageNotAnInteger
from django.db.models import Q
from django.http import Http404
from django.template import (
    Library,
    Node,
    TemplateSyntaxError,
    Variable,
    loader,
)
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django_comments.templatetags.comments import (
    BaseCommentNode,
    RenderCommentFormNode,
)
from django_comments_ink import (
    caching,
    get_comment_reactions_enum,
    get_model,
    get_object_reactions_enum,
    utils,
)
from django_comments_ink.api import frontend
from django_comments_ink.conf import settings
from django_comments_ink.models import (
    ObjectReaction,
    max_thread_level_for_content_type,
)
from django_comments_ink.paginator import CommentsPaginator

logger = logging.getLogger(__name__)

register = Library()


if len(settings.COMMENTS_INK_THEME_DIR) > 0:
    theme_dir = "themes/%s" % settings.COMMENTS_INK_THEME_DIR
    theme_dir_exists = utils.does_theme_dir_exist(f"comments/{theme_dir}")
else:
    theme_dir = ""
    theme_dir_exists = False


# List of possible paths to the list.html template file.
_list_html_tmpl = []
if theme_dir_exists:
    _list_html_tmpl.extend(
        [
            "comments/{theme_dir}/{app_label}/{model}/list.html",
            "comments/{theme_dir}/{app_label}/list.html",
            "comments/{theme_dir}/list.html",
        ]
    )
_list_html_tmpl.extend(
    [
        "comments/{app_label}/{model}/list.html",
        "comments/{app_label}/list.html",
        "comments/list.html",
    ]
)


# List of possible paths to the form.html template file.
_form_html_tmpl = []
if theme_dir_exists:
    _form_html_tmpl.extend(
        [
            "comments/{theme_dir}/{app_label}/{model}/form.html",
            "comments/{theme_dir}/{app_label}/form.html",
            "comments/{theme_dir}/form.html",
        ]
    )
_form_html_tmpl.extend(
    [
        "comments/{app_label}/{model}/form.html",
        "comments/{app_label}/form.html",
        "comments/form.html",
    ]
)


# List of possible paths to the reply_template.html template file.
_reply_template_html_tmpl = []
if theme_dir_exists:
    _reply_template_html_tmpl.extend(
        [
            "comments/{theme_dir}/{app_label}/{model}/reply_template.html",
            "comments/{theme_dir}/{app_label}/reply_template.html",
            "comments/{theme_dir}/reply_template.html",
        ]
    )
_reply_template_html_tmpl.extend(
    [
        "comments/{app_label}/{model}/reply_template.html",
        "comments/{app_label}/reply_template.html",
        "comments/reply_template.html",
    ]
)


_reactions_panel_template_tmpl = []
if theme_dir_exists:
    _reactions_panel_template_tmpl.extend(
        [
            "comments/{theme_dir}/reactions_panel_template.html",
            "comments/reactions_panel_template.html",
        ]
    )
_reactions_panel_template_tmpl.append("comments/reactions_panel_template.html")


_reactions_buttons_tmpl = []
if theme_dir_exists:
    _reactions_buttons_tmpl.extend(
        [
            "comments/{theme_dir}/reactions_buttons.html",
            "comments/reactions_buttons.html",
        ]
    )
_reactions_buttons_tmpl.append("comments/reactions_buttons.html")


# List of possible paths to the object_reactions.html template file.
_object_reactions_tmpl = []
if theme_dir_exists:
    _object_reactions_tmpl.extend(
        [
            "comments/{theme_dir}/{app_label}/{model}/object_reactions.html"
            "comments/{theme_dir}/{app_label}/object_reactions_form.html",
            "comments/{theme_dir}/object_reactions_form.html",
        ]
    )
_object_reactions_tmpl.extend(
    [
        "comments/{app_label}/{model}/object_reactions.html",
        "comments/{app_label}/object_reactions.html",
        "comments/object_reactions.html",
    ]
)


# List of possible paths to the object_reactions_form.html template file.
_object_reactions_form_tmpl = []
if theme_dir_exists:
    _object_reactions_form_tmpl.extend(
        [
            (
                "comments/{theme_dir}/{app_label}/{model}/"
                "object_reactions_form.html"
            ),
            "comments/{theme_dir}/{app_label}/object_reactions_form.html",
            "comments/{theme_dir}/object_reactions_form.html",
        ]
    )
_object_reactions_form_tmpl.extend(
    [
        "comments/{app_label}/{model}/object_reactions_form.html",
        "comments/{app_label}/object_reactions_form.html",
        "comments/object_reactions_form.html",
    ]
)


def filter_folded_comments(qs, context):
    request = context.get("request", None)
    cfold_qs_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
    cfold = (request and request.GET.get(cfold_qs_param, None)) or None
    if cfold:
        cfold_list = {int(cid) for cid in cfold.split(",")}
        return qs.filter(~Q(level__gt=0, thread_id__in=cfold_list))
    return qs


def folded_comments(context):
    """
    Returns dict with folded comments data to the given context.
    """
    request = context.get("request", None)
    cfold_qs_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
    cfold = (request and request.GET.get(cfold_qs_param, None)) or None
    fold = (cfold and {int(cid) for cid in cfold.split(",")}) or {}

    return {
        "comments_fold_qs_param": cfold_qs_param,
        cfold_qs_param: ",".join([str(cid) for cid in fold]),
    }


def paginate_queryset(queryset, context, ckey_prefix):
    """
    Returns dict with pagination data for the given queryset and context.
    """
    request = context.get("request", None)
    num_orphans = settings.COMMENTS_INK_MAX_LAST_PAGE_ORPHANS
    page_size = settings.COMMENTS_INK_ITEMS_PER_PAGE

    cpage_qs_param = settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
    page = (request and request.GET.get(cpage_qs_param, None)) or 1

    cfold_qs_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
    cfold = (request and request.GET.get(cfold_qs_param, None)) or None
    fold = (cfold and {int(cid) for cid in cfold.split(",")}) or {}

    if page_size == 0:
        return {
            "paginator": None,
            "page_obj": None,
            "is_paginated": False,
            "comments_page_qs_param": cpage_qs_param,
            "comment_list": queryset,
            cpage_qs_param: 1,
        }

    paginator = CommentsPaginator(
        queryset,
        page_size,
        orphans=num_orphans,
        comments_folded=fold,
        cache_key_prefix=ckey_prefix,
    )

    try:
        page_number = int(page)
    except ValueError:
        if page == "last":
            page_number = paginator.num_pages
        else:
            raise Http404(
                _("Page is not “last”, nor can it " "be converted to an int.")
            )

    try:
        page = paginator.page(page_number)
        return {
            "paginator": paginator,
            "page_obj": page,
            "is_paginated": page.has_other_pages(),
            "comments_page_qs_param": cpage_qs_param,
            "comment_list": page.object_list,
            cpage_qs_param: page.number,
        }
    except InvalidPage as exc:
        raise Http404(
            _("Invalid page (%(page_number)s): %(message)s")
            % {"page_number": page_number, "message": str(exc)}
        )


class BaseInkCommentNode(BaseCommentNode):
    def get_queryset(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        site_id = utils.get_current_site_id(context.get("request", None))

        kwargs = {
            "ctype_pk": ctype.pk,
            "object_pk": object_pk,
            "site_id": site_id,
        }
        comments_qs_ptn = settings.COMMENTS_INK_CACHE_KEYS["comments_qs"]
        comments_count_ptn = settings.COMMENTS_INK_CACHE_KEYS["comments_count"]
        comments_paged_ptn = settings.COMMENTS_INK_CACHE_KEYS["comments_paged"]
        self.ckey_comments_qs = comments_qs_ptn.format(**kwargs)
        self.ckey_comments_count = comments_count_ptn.format(**kwargs)
        self.ckey_comments_paged = comments_paged_ptn.format(**kwargs)

        # Check whether there is already a qs in the dci cache.
        qs = None
        dci_cache = caching.get_cache()
        if dci_cache != None and self.ckey_comments_qs != "":
            cached = dci_cache.get(self.ckey_comments_qs)
            if cached:
                logger.debug("Get %s from the cache", self.ckey_comments_qs)
                qs = cached

        if not qs:
            qs = super().get_queryset(context)
            if dci_cache != None and self.ckey_comments_qs != "":
                logger.debug("Adding %s to the cache", self.ckey_comments_qs)
                dci_cache.set(self.ckey_comments_qs, qs, timeout=None)

        return qs


class InkCommentListNode(BaseInkCommentNode):
    def get_context_value_from_queryset(self, context, qs):
        return qs


class RenderInkCommentListNode(InkCommentListNode):
    """Render the comment list directly."""

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse render_comment_list and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != "for":
            raise TemplateSyntaxError(
                "Second argument in %r tag must be 'for'" % tokens[0]
            )

        # {% render_comment_list for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_comment_list for app.models pk %}
        elif len(tokens) == 4:
            return cls(
                ctype=BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
            )

    def render(self, context):
        try:
            ctype, object_pk = self.get_target_ctype_pk(context)
        except AttributeError:
            # in get_target_ctype_pk the call to FilterExpression.resolve
            # does not raise VariableDoesNotExist, however in a latter step
            # an AttributeError is raised when the object_expr does not exist
            # in the context. Therefore, this except raises when used as:
            # {% render_inkcomment_list for var_not_in_context %}
            return ""

        template_list = [
            pth.format(
                theme_dir=theme_dir,
                app_label=ctype.app_label,
                model=ctype.model,
            )
            for pth in _list_html_tmpl
        ]

        qs = self.get_queryset(context)
        qs = self.get_context_value_from_queryset(context, qs)
        context_dict = context.flatten()
        qs = filter_folded_comments(qs, context)
        context_dict.update(folded_comments(context))
        context_dict.update(
            paginate_queryset(qs, context, self.ckey_comments_paged)
        )

        # Pass max_thread_level in the context.
        app_model = "%s.%s" % (ctype.app_label, ctype.model)
        MTL = settings.COMMENTS_INK_MAX_THREAD_LEVEL_BY_APP_MODEL
        mtl = MTL.get(app_model, settings.COMMENTS_INK_MAX_THREAD_LEVEL)
        max_users_in_tooltip = settings.COMMENTS_INK_MAX_USERS_IN_TOOLTIP
        context_dict.update(
            {
                "dcx_theme_dir": theme_dir,
                "max_thread_level": mtl,
                "reply_stack": [],  # List to control reply widget rendering.
                "max_users_in_tooltip": max_users_in_tooltip,
            }
        )

        # get_app_model_options returns a dict like: {
        #     'who_can_post': 'all' | 'users',
        #     'check_input_allowed': 'string path to function',
        #     'comment_flagging_enabled': <boolean>,
        #     'comment_reactions_enabled': <boolean>,
        #     'object_reactions_enabled': <boolean>
        # }
        options = utils.get_app_model_options(content_type=app_model)
        check_input_allowed_str = options.pop("check_input_allowed")
        check_func = import_string(check_input_allowed_str)
        target_obj = ctype.get_object_for_this_type(pk=object_pk)

        # Call the function that checks whether comments input
        # is still allowed on the given target_object. And add
        # the resulting boolean to the template context.
        #
        options["is_input_allowed"] = check_func(target_obj)
        context_dict.update(options)

        liststr = loader.render_to_string(template_list, context_dict)
        return liststr


@register.tag
def render_inkcomment_list(parser, token):
    """
    Render the comment list (as returned by ``{% get_inkcomment_list %}``)
    through the ``comments/list.html`` templates.

    Syntax::

        {% render_inkcomment_list for [object] %}
        {% render_inkcomment_list for [app].[model] [obj_id] %}

    Example usage::

        {% render_inkcomment_list for post %}

    """
    return RenderInkCommentListNode.handle_token(parser, token)


# ---------------------------------------------------------------------
class InkCommentCountNode(BaseInkCommentNode):
    """Insert a count of comments into the context."""

    def get_context_value_from_queryset(self, context, qs):
        return qs.count()

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        site_id = utils.get_current_site_id(context.get("request", None))

        result = None
        dci_cache = caching.get_cache()
        key = settings.COMMENTS_INK_CACHE_KEYS["comments_count"].format(
            ctype_pk=ctype.pk, object_pk=object_pk, site_id=site_id
        )
        if dci_cache != None and key != "":
            cached = dci_cache.get(key)
            if cached:
                logger.debug("Fetching %s from the cache", key)
                result = cached

        if not result:
            qs = self.get_queryset(context)
            result = self.get_context_value_from_queryset(context, qs)
            if dci_cache != None and key != "":
                logger.debug("Adding %s to the cache", key)
                dci_cache.set(key, result, timeout=None)

        context[self.as_varname] = result
        return ""


@register.tag
def get_inkcomment_count(parser, token):
    """
    Gets the comment count for the given params and populates the template
    context with a variable containing that value, whose name is defined by the 'as' clause. It differs from {% get_comment_count %} in which it
    caches the result.

    Syntax::

        {% get_inkcomment_count for [object] as [varname]  %}
        {% get_inkcomment_count for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_inkcomment_count for event as comment_count %}
        {% get_inkcomment_count for calendar.event event.id as comment_count %}
        {% get_inkcomment_count for calendar.event 17 as comment_count %}

    """
    return InkCommentCountNode.handle_token(parser, token)


# ---------------------------------------------------------------------
class RenderInkCommentFormNode(RenderCommentFormNode):
    """
    Almost identical to django_comments' RenderCommentFormNode.

    This class rewrites the `render` method of its parent class, to
    fetch the template from the theme directory.
    """

    def render(self, context):
        try:
            ctype, _ = self.get_target_ctype_pk(context)
            template_list = [
                pth.format(
                    theme_dir=theme_dir,
                    app_label=ctype.app_label,
                    model=ctype.model,
                )
                for pth in _form_html_tmpl
            ]
            context_dict = context.flatten()
            context_dict["form"] = self.get_form(context)
            formstr = loader.render_to_string(template_list, context_dict)
            return formstr
        except:
            return ""


@register.tag
def render_inkcomment_form(parser, token):
    """
    Render "comments/<theme_dir>/form.html" or "comments/form.html".

    Syntax::

        {% get_inkcomment_form for [object] as [varname] %}
        {% get_inkcomment_form for [app].[model] [object_id] as [varname] %}
    """
    return RenderInkCommentFormNode.handle_token(parser, token)


class RenderCommentReplyTemplateNode(RenderCommentFormNode):
    def render(self, context):
        cpage_qs_param = settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
        try:
            ctype, _ = self.get_target_ctype_pk(context)
            template_list = [
                pth.format(
                    theme_dir=theme_dir,
                    app_label=ctype.app_label,
                    model=ctype.model,
                )
                for pth in _reply_template_html_tmpl
            ]
            context_dict = context.flatten()
            context_dict.update(
                {
                    "form": self.get_form(context),
                    "comments_page_qs_param": cpage_qs_param,
                    "dcx_theme_dir": theme_dir,
                }
            )
            formstr = loader.render_to_string(template_list, context_dict)
            return formstr
        except:
            return ""


@register.tag
def render_comment_reply_template(parser, token):
    """
    Render the comment reply form to be used by the JavaScript plugin.

    Syntax::

        {% render_comment_reply_template for [object] %}
        {% render_comment_reply_template for [app].[model] [object_id] %}
    """
    return RenderCommentReplyTemplateNode.handle_token(parser, token)


# ---------------------------------------------------------------------
class RenderQSParams(Node):
    def __init__(self, page_expr, comment_action, comment_object):
        self.page_expr = None
        self.comment_action = comment_action
        self.comment_object = None
        if page_expr != None:
            self.page_expr = Variable(page_expr)
        if comment_object != None:
            self.comment_object = Variable(comment_object)

    def render(self, context):
        cobj = None
        qs_params = []
        cpage_qs_param = settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
        cfold_qs_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
        fold_param = context.get(cfold_qs_param, None) or ""

        if self.page_expr:
            page = self.page_expr.resolve(context)
            if page != 1:
                qs_params.append(f"{cpage_qs_param}={page}")

        if self.comment_object:
            cobj = self.comment_object.resolve(context)

        if self.comment_object == None and self.page_expr == None:
            page = context.get(cpage_qs_param, None) or None
            if page != 1:
                qs_params.append(f"{cpage_qs_param}={page}")

        if cobj:
            if len(fold_param) > 0:
                fold = {int(cid) for cid in fold_param.split(",")}
            else:
                fold = set()

            if self.comment_action == "fold":
                fold.add(cobj.id)
            elif self.comment_action == "unfold":
                fold.remove(cobj.id)

            fold_csv = ",".join(sorted([str(cid) for cid in fold]))

            if self.page_expr == None:
                request = context.get("request", None)
                page = utils.get_comment_page_number(
                    request,
                    cobj.content_type.id,
                    cobj.object_pk,
                    cobj.id,
                    comments_folded=fold,
                )
                qs_params.append(f"{cpage_qs_param}={page}")

            if len(fold_csv):
                qs_params.append(f"{cfold_qs_param}={fold_csv}")

        else:  # cobj is None.
            if len(fold_param) > 0:
                qs_params.append(f"{cfold_qs_param}={fold_param}")

        return mark_safe(f"{'&'.join(qs_params)}")


@register.tag
def render_qs_params(parser, token):
    """
    Render_qs_params to manage comments page and comments muted list.

    Syntax::

        {% render_qs_params [page <var>] [fold|unfold <InkComment>] %}
    """
    bits = token.contents.split()
    tag_name, args = bits[0], bits[1:]

    if len(args) != 0 and len(args) != 2 and len(args) != 4:
        raise TemplateSyntaxError(
            "%r tag requires either 0 or 2 or 4 arguments" % tag_name
        )

    page_expr = None
    comment_action = None
    comment_object = None

    if len(args) == 2:
        if args[0] == "page":
            page_expr = args[1]
        elif args[0] in ["fold", "unfold"]:
            comment_action = args[0]
            comment_object = args[1]
    elif len(args) == 4:
        if args[0] == "page" and args[2] in ["fold", "unfold"]:
            page_expr = args[1]
            comment_action = args[2]
            comment_object = args[3]
        elif args[0] in ["fold", "unfold"] and args[2] == "page":
            page_expr = args[3]
            comment_action = args[0]
            comment_object = args[1]
        else:
            raise TemplateSyntaxError(
                "%r tag requires 'page <page_var>' and/or "
                "'fold|unfold <comment>' pair arguments" % tag_name
            )

    return RenderQSParams(page_expr, comment_action, comment_object)


@register.filter
def has_comment(cfold, comment):
    if cfold and len(cfold) > 0:
        fold = {int(cid) for cid in cfold.split(",")}
        return comment.id in fold
    return False


@register.filter
def get_anchor(comment, anchor_pattern=None):
    if anchor_pattern:
        cm_abs_url = comment.get_absolute_url(anchor_pattern)
    else:
        cm_abs_url = comment.get_absolute_url()

    hash_pos = cm_abs_url.find("#")
    return cm_abs_url[hash_pos + 1 :]


# ---------------------------------------------------------------------
@register.simple_tag()
def get_inkcomment_permalink(
    comment, page_number=None, comments_folded=None, anchor_pattern=None
):
    """
    Get the permalink for a comment, optionally specifying the format of the
    named anchor to be appended to the end of the URL.

    Usage::
        {% get_inkcomment_permalink comment <page_num> <comments_folded> <anchor_pattern> %}

    Example::
        {% get_inkcomment_permalink comment 2 "1,97,145" "#c%(id)s" %}
    """
    try:
        if anchor_pattern:
            cm_abs_url = comment.get_absolute_url(anchor_pattern)
        else:
            cm_abs_url = comment.get_absolute_url()

        hash_pos = cm_abs_url.find("#")
        cm_anchor = cm_abs_url[hash_pos:]
        cm_abs_url = cm_abs_url[:hash_pos]
    except Exception:
        return comment.get_absolute_url()

    if not page_number:
        page_number = 1
    else:
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            raise PageNotAnInteger(_("That page number is not an integer"))

    if not comments_folded:
        comments_folded = ""
    else:
        try:
            comments_folded = {int(cid) for cid in comments_folded.split(",")}
        except (TypeError, ValueError):
            raise TemplateSyntaxError(
                _("A comment ID in comments_folded is not an integer.")
            )

    qs_params = []

    if page_number > 1:
        cpage_qs_param = settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
        qs_params.append(f"{cpage_qs_param}={page_number}")

    if len(comments_folded):
        cfold_qs_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
        csv_of_cids = ",".join([str(cid) for cid in comments_folded])
        qs_params.append(f"{cfold_qs_param}={csv_of_cids}")

    if len(qs_params):
        return mark_safe(f"{cm_abs_url}?{'&'.join(qs_params)}{cm_anchor}")
    else:
        return f"{cm_abs_url}{cm_anchor}"


# ----------------------------------------------------------------------
class GetCommentsAPIPropsNode(Node):
    def __init__(self, obj):
        self.obj = Variable(obj)

    def render(self, context):
        obj = self.obj.resolve(context)
        user = context.get("user", None)
        request = context.get("request", None)
        props = frontend.comments_api_props(obj, user, request=request)
        return json.dumps(props)


@register.tag
def get_comments_api_props(parser, token):
    """
    Returns a JSON with properties required to use the REST API.

    See api.frontend.comments_props for full details on the props.

    Example::
        {% get_comments_api_props for comment %}
    """
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError(
            "%r tag requires arguments" % token.contents.split()[0]
        )
    match = re.search(r"for (\w+)", args)
    if not match:
        raise TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    obj = match.groups()[0]
    return GetCommentsAPIPropsNode(obj)


# ----------------------------------------------------------------------
@register.simple_tag
def comment_reaction_form_target(comment):
    """
    Get the target URL for the comment reaction form.

    Example::

        <form action="{% comment_reaction_form_target comment %}" method="post">
    """
    return reverse("comments-ink-react", args=(comment.id,))


class RenderCommentReactionsButtons(Node):
    def __init__(self, user_reactions):
        self.user_reactions = Variable(user_reactions)

    def render(self, context):
        context = {
            "reactions": get_comment_reactions_enum(),
            "user_reactions": self.user_reactions.resolve(context),
            "break_every": settings.COMMENTS_INK_REACTIONS_ROW_LENGTH,
        }
        template_list = [
            pth.format(theme_dir=theme_dir) for pth in _reactions_buttons_tmpl
        ]
        htmlstr = loader.render_to_string(template_list, context)
        return htmlstr


@register.tag
def render_comment_reactions_buttons(parser, token):
    """
    Renders template with reactions buttons, depending on the selected theme.

    Example usage::

        {% render_comment_reactions_buttons user_reactions %}

    Argument `user_reactions` is a list with `ReactionEnum` items, it
    contains a user's reactions to a comment. The template displays a button
    per each reaction returned from get_comment_reactions_enum().
    Each reaction that is already in the `user_reactions` list is marked as
    already clicked. This templatetag is used within the
    `react_to_comment.html` template.
    """
    try:
        _, args = token.contents.split(None, 1)
    except ValueError:
        raise TemplateSyntaxError(
            "%r tag requires argument" % token.contents.split()[0]
        )
    user_reactions = args
    return RenderCommentReactionsButtons(user_reactions)


@register.filter
def authors_list(cmt_reaction):
    """
    Returns a list with the result of applying the function
    COMMENTS_INK_API_USER_REPR to each authour of the given CommentReaction.
    """
    return [
        settings.COMMENTS_INK_API_USER_REPR(author)
        for author in cmt_reaction.authors.all()
    ]


@register.filter
def get_comment_reaction_enum(cmt_reaction):
    """
    Helper to get the ReactionEnum corresponding to given CommentReaction.
    """
    return get_comment_reactions_enum()(cmt_reaction.reaction)


# ----------------------------------------------------------------------
@register.simple_tag(takes_context=True)
def comment_css_thread_range(context, comment, prefix="l"):
    """
    Helper tag to return a string of CSS selectors that render vertical
    lines to represent comment threads. When comment's level matches the
    max_thread_level there is no vertical line as comments in the
    max_thread_level can not receivereplies.

    Returns a concatenated string of f'{prefix}{i}' for i in range(level + 1).
    When the given comment has level=2, and the maximum thread level is 2:

        `{% comment_css_thread_range comment %}`

    produces the string: "l0-mid l1-mid l2".
    """
    max_thread_level = context.get("max_thread_level", None)
    if not max_thread_level:
        ctype = ContentType.objects.get_for_model(comment.content_object)
        max_thread_level = max_thread_level_for_content_type(ctype)

    result = ""
    for i in range(comment.level + 1):
        if i == comment.level:
            if comment.level == max_thread_level:
                result += f"{prefix}{i} "
            else:
                result += f"{prefix}{i}-ini "
        else:
            result += f"{prefix}{i}-mid "
    return result.rstrip()


@register.filter(is_safe=True)
def reply_css_thread_range(level, prefix="l"):
    """
    Helper filter to return a string of CSS selectors that render vertical
    lines to represent comment threads. When comment level matches the
    max_thread_level there is no vertical line, as comments in the
    max_thread_level can not receive replies.

    Returns a concatenated string of f'{prefix}{i}' for i in range(level + 1).
    If the given comment object has level=1, using the filter as:

        `{{ comment.level|reply_css_thread_range }}`

    produces the string: "l0 l1".
    """
    result = ""
    for i in range(level + 1):
        result += f"{prefix}{i} "
    return mark_safe(result.rstrip())


@register.filter(is_safe=True)
def indent_divs(level, prefix="level-"):
    """
    Helper filter to return a concatenated string of divs for indentation.

    When called as {{ 2|indent_divs }} produces the string:

        '<div class="level-1"></div>
         <div class="level-2"></div>'
    """
    result = ""
    for i in range(1, level + 1):
        result += f'<div class="{prefix}{i}"></div>'
    return mark_safe(result)


@register.filter(is_safe=True)
def hline_div(level, prefix="line-"):
    """
    Helper filter to eeturns a DIV that renders a horizontal line connecting
    the vertical comment thread line with the comment reply box.

    When called as {{ comment.level|hline_div }} produces the string:

        '<div class="line-{comment.level}"></div>'
    """
    return mark_safe(f'<div class="{prefix}{level}"></div>')


@register.filter
def get_top_comment(reply_stack):
    """
    Helper filter used to list comments in the <comments/list.html> template.
    """
    return reply_stack[-1]


@register.filter
def pop_comments_gte(reply_stack, level_lte=0):
    """
    Helper filter used to list comments in the <comments/list.html> template.
    """
    comments_lte = []
    try:
        for index in range(len(reply_stack) - 1, -1, -1):
            if reply_stack[index].level < level_lte:
                break
            comments_lte.append(reply_stack.pop(index))
    finally:
        return comments_lte


@register.simple_tag(takes_context=True)
def push_comment(context, comment):
    """
    Helper filter used to list comments in the <comments/list.html> template.
    """
    context["reply_stack"].append(comment)
    return ""


@register.filter
def get_comment(comment_id: str):
    return get_model().objects.get(pk=int(comment_id))


@register.simple_tag()
def dci_custom_selector():
    return f"{settings.COMMENTS_INK_CSS_CUSTOM_SELECTOR}"


@register.simple_tag()
def get_dci_theme_dir():
    return theme_dir


# ----------------------------------------------------------------------
@register.inclusion_tag("comments/only_users_can_post.html")
def render_only_users_can_post_template(object):
    return {"html_id_suffix": utils.get_html_id_suffix(object)}


class RenderCommentReactionsPanelTemplate(Node):
    def render(self, context):
        enums_details = [
            (enum.value, enum.label, enum.icon)
            for enum in get_comment_reactions_enum()
        ]
        context = {
            "enums_details": enums_details,
            "break_every": settings.COMMENTS_INK_REACTIONS_ROW_LENGTH,
        }
        template_list = [
            pth.format(theme_dir=theme_dir)
            for pth in _reactions_panel_template_tmpl
        ]
        htmlstr = loader.render_to_string(template_list, context)
        return htmlstr


@register.tag
def render_comment_reactions_panel_template(parser, token):
    return RenderCommentReactionsPanelTemplate()


# ----------------------------------------------------------------------
# Base class to handle object reactions.


class BaseObjectReactionsNode(Node):
    """
    Base helper class for handling tags:
     * render_object_reactions
     * render_object_reactions_form
    """

    @classmethod
    def handle_token(cls, parser, token):
        tokens = token.split_contents()
        if tokens[1] != "for":
            raise TemplateSyntaxError(
                "Second argument in %r tag must be 'for'" % tokens[0]
            )

        # {% render_object_reactions for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_object_reactions for app.model pk %}
        elif len(tokens) == 4:
            return cls(
                ctype=cls.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
            )

    @staticmethod
    def lookup_content_type(token, tagname):
        try:
            app, model = token.split(".")
            return ContentType.objects.get_by_natural_key(app, model)
        except ValueError:
            raise TemplateSyntaxError(
                "Third argument in %r must be in the format 'app.model'"
                % tagname
            )
        except ContentType.DoesNotExist:
            raise TemplateSyntaxError(
                "%r tag has non-existant content-type: '%s.%s'"
                % (tagname, app, model)
            )

    def __init__(self, ctype=None, object_pk_expr=None, object_expr=None):
        self.ctype = ctype
        self.object_pk_expr = object_pk_expr
        self.object_expr = object_expr

    def resolve_ctype_and_object_pk(self, context):
        """
        Assign values to self attributes ctype, object_pk and site_id.
        """
        self.object_pk = None
        self.site_id = None

        request = context.get("request", None)
        self.site_id = utils.get_current_site_id(request)

        if self.object_expr:
            obj = self.object_expr.resolve(context)
            if obj:
                self.ctype = ContentType.objects.get_for_model(obj)
                self.object_pk = obj.pk
            else:
                raise TemplateSyntaxError(
                    "Variable '%s' does not exist" % self.object_expr
                )
        else:
            self.object_pk = self.object_pk_expr.resolve(
                context, ignore_failures=True
            )

        app_model = "%s.%s" % (self.ctype.app_label, self.ctype.model)
        options = utils.get_app_model_options(content_type=app_model)
        if not options["object_reactions_enabled"]:
            raise Exception(
                "Object reactions for '%s' is not enabled in the setting "
                "COMMENTS_INK_APP_MODEL_OPTIONS in the settings module"
                % app_model
            )

        self.object = self.ctype.get_object_for_this_type(pk=self.object_pk)
        check_input_allowed_str = options.pop("check_input_allowed")
        check_func = import_string(check_input_allowed_str)
        self.is_input_allowed = check_func(self.object)

    @property
    def template_list(self):
        return [
            pth.format(
                theme_dir=theme_dir,
                app_label=self.ctype.app_label,
                model=self.ctype.model,
            )
            for pth in self.tag_templates
        ]

    def get_object_reactions(self):
        """Returns list of dicts with object reactions and their counters."""
        max_users_listed = getattr(
            settings, "COMMENTS_INK_MAX_USERS_IN_TOOLTIP", 10
        )
        reactionsd = dict(
            [
                (
                    item.reaction,
                    {
                        "counter": item.counter,
                        "authors": [
                            settings.COMMENTS_INK_API_USER_REPR(author)
                            for author in item.authors.all()[:max_users_listed]
                        ],
                    },
                )
                for item in ObjectReaction.objects.filter(
                    content_type=self.ctype,
                    object_pk=self.object_pk,
                    site__id=self.site_id,
                )
            ]
        )

        object_reactions = []
        defs = {"counter": 0, "authors": []}
        for item in get_object_reactions_enum():
            object_reactions.append(
                {
                    "value": item.value,
                    "label": item.label,
                    "icon": item.icon,
                    "counter": reactionsd.get(item.value, defs)["counter"],
                    "authors": reactionsd.get(item.value, defs)["authors"],
                }
            )

        return object_reactions

    def render(self, context):
        request = context.get("request", None)
        self.resolve_ctype_and_object_pk(context)

        cpage_qs_param = settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
        page = (request and request.GET.get(cpage_qs_param, None)) or 1

        cfold_qs_param = settings.COMMENTS_INK_FOLD_QUERY_STRING_PARAM
        cfold = (request and request.GET.get(cfold_qs_param, None)) or None
        fold = (cfold and {int(cid) for cid in cfold.split(",")}) or {}

        try:
            login_url = reverse("login")
        except NoReverseMatch as exc:
            login_url = settings.LOGIN_URL

        max_users_in_tooltip = settings.COMMENTS_INK_MAX_USERS_IN_TOOLTIP

        context = {
            "content_type": self.ctype,
            "object": self.object,
            "object_reactions": self.get_object_reactions(),
            "is_input_allowed": self.is_input_allowed,
            "max_users_in_tooltip": max_users_in_tooltip,
            "comments_page_qs_param": cpage_qs_param,
            cpage_qs_param: page,
            "comments_fold_qs_param": cfold_qs_param,
            cfold_qs_param: ",".join([str(cid) for cid in fold]),
            "login_url": login_url,
        }
        htmlstr = loader.render_to_string(self.template_list, context, request)
        return htmlstr


class RenderObjectReactions(BaseObjectReactionsNode):
    """Template tag to render reactions posted to a given object."""

    tag_templates = _object_reactions_tmpl


class RenderObjectReactionsForm(BaseObjectReactionsNode):
    """Template tag to render the object reactions form."""

    tag_templates = _object_reactions_form_tmpl


@register.tag
def render_object_reactions(parser, token):
    """
    Render the object reactions list through the ``object_reactions.html``
    template. The template is looked for in the following directories:
     * comments/<app_label>/<model>/
     * comments/<app_label>/
     * comments/
    If the setting `COMMENTS_INK_THEME_DIR` is provided in the settings module
    the previous list contains is preceded by the following list:
     * comments/<theme_dir>/<app_label>/<model>/
     * comments/<theme_dir>/<app_label>/
     * comments/<theme_dir>/

    Syntax::

        {% render_object_reactions for [object] %}
        {% render_object_reactions for [app].[model] [obj_id] %}

    Example usage::

        {% render_object_reactions for post %}

    """
    return RenderObjectReactions.handle_token(parser, token)


@register.tag
def render_object_reactions_form(parser, token):
    """
    Render object reactions using the ``object_reactions_form.html`` template.
    The template is looked for in the following directories:
     * comments/<app_label>/<model>/
     * comments/<app_label>/
     * comments/
    If the setting `COMMENTS_INK_THEME_DIR` is provided in the settings module
    the previous list contains is preceded by the following list:
     * comments/<theme_dir>/<app_label>/<model>/
     * comments/<theme_dir>/<app_label>/
     * comments/<theme_dir>/

    Syntax::

        {% render_object_reactions_form for [object] %}
        {% render_object_reactions_form for [app].[model] [obj_id] %}

    Example usage::

        {% render_object_reactions_form for post %}

    """
    return RenderObjectReactionsForm.handle_token(parser, token)


@register.simple_tag
def object_reactions_form_target(object):
    """
    Get the target URL for the object reaction form.

    Example::

        <form action="{% object_reactions_form_target object %}" method="post">
    """
    ctype = ContentType.objects.get_for_model(object)
    return reverse("comments-ink-react-to-object", args=(ctype.id, object.id))


# ----------------------------------------------------------------------
# Template tag for themes 'avatar_in_thread' and 'avatar_in_header'


def get_gravatar_url(email, size=48, avatar="identicon"):
    """
    This is the parameter of the production avatar.
    The first parameter is the way of generating the
    avatar and the second one is the size.
    The way os generating has mp/identicon/monsterid/wavatar/retro/hide.
    """
    return "//www.gravatar.com/avatar/%s?%s&d=%s" % (
        hashlib.md5(email.lower().encode("utf-8")).hexdigest(),
        urlencode({"s": str(size)}),
        avatar,
    )


# ----------------------------------------------------------------------
# The following code requires django-avatar.

if apps.is_installed("avatar"):  # pragma: no cover

    from avatar.templatetags.avatar_tags import avatar
    from avatar.utils import cache_result

    @cache_result
    @register.simple_tag
    def get_user_avatar_or_gravatar(email, config="48,identicon"):
        size, gravatar_type = config.split(",")
        try:
            size_number = int(size)
        except ValueError:
            raise Http404(_("The given size is not a number: %s" % repr(size)))

        try:
            user = get_user_model().objects.get(email=email)
            return avatar(user, size_number)
        except get_user_model().DoesNotExist:
            url = get_gravatar_url(email, size_number, gravatar_type)
            return mark_safe(
                '<img src="%s" height="%d" width="%d">'
                % (url, size_number, size_number)
            )

else:

    @register.simple_tag
    def get_user_avatar_or_gravatar(*args, **kwargs):
        raise TemplateSyntaxError(
            "The 'get_user_avatar_or_gravatar' template tag requires "
            "to have installed the package 'django-avatar'."
        )
