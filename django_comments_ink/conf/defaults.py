from __future__ import unicode_literals

from django.conf import settings

COMMENT_MAX_LENGTH = 3000

# Extra key to salt the InkCommentForm.
COMMENTS_INK_SALT = b""

# Whether comment posts should be confirmed by email.
COMMENTS_INK_CONFIRM_EMAIL = True

# From email address.
COMMENTS_INK_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL

# Contact email address.
COMMENTS_INK_CONTACT_EMAIL = settings.DEFAULT_FROM_EMAIL

# Maximum Thread Level.
COMMENTS_INK_MAX_THREAD_LEVEL = 0

# Maximum Thread Level per app.model basis.
COMMENTS_INK_MAX_THREAD_LEVEL_BY_APP_MODEL = {}

# Default order to list comments in.
COMMENTS_INK_LIST_ORDER = ("thread_id", "order")

# Form class to use.
COMMENTS_INK_FORM_CLASS = "django_comments_ink.forms.InkCommentForm"

# Model to use.
COMMENTS_INK_MODEL = "django_comments_ink.models.InkComment"

# Enum class for comment reactions.
COMMENTS_INK_COMMENT_REACTIONS_ENUM = "django_comments_ink.models.ReactionEnum"

# Enum class for object reactions.
COMMENTS_INK_OBJECT_REACTIONS_ENUM = "django_comments_ink.models.ReactionEnum"

# Send HTML emails.
COMMENTS_INK_SEND_HTML_EMAIL = True

# Whether to send emails in separate threads or use the regular method.
# Set it to False to use a third-party app like django-celery-email or
# your own celery app.
COMMENTS_INK_THREADED_EMAILS = True

# Define what commenting features a pair app_label.model can have.
COMMENTS_INK_APP_MODEL_OPTIONS = {
    "default": {
        "who_can_post": "all",  # Valid values: "users", "all",
        # Function to determine whether new comments,
        # reactions, etc. should be allowed for a given object.
        "check_input_allowed": "django_comments_ink.utils.check_input_allowed",
        # Whether to display a link to flag a comment as inappropriate.
        "comment_flagging_enabled": False,
        # Whether to allow users to submit reactions on comments.
        "comment_reactions_enabled": False,
        # Whether to allow users to submit reactions on any object
        # registered as a content type.
        "object_reactions_enabled": False,
    }
}

# When True, an approval or removal operation on a comment will
# trigger a publishing or withholding operation on its nested comments.
COMMENTS_INK_PUBLISH_OR_WITHHOLD_NESTED = True


# Define a function to return the user representation. Used by
# the web API to represent user strings in response objects.
def username(u):
    return u.username


COMMENTS_INK_API_USER_REPR = username

# Makes the "Notify me about followup comments" checkbox in the
# comment form checked (True) or unchecked (False) by default.
COMMENTS_INK_DEFAULT_FOLLOWUP = False

# How many reaction buttons can be displayed
# in a row before it breaks into another row.
COMMENTS_INK_REACTIONS_ROW_LENGTH = 4

# How many users are listed when hovering a reaction.
COMMENTS_INK_MAX_USERS_IN_TOOLTIP = 10

# Display up to the given number of comments in the last page to avoid
# creating another page containing only these amount of comments.
COMMENTS_INK_MAX_LAST_PAGE_ORPHANS = 10

# Number of comments per page. When <=0 pagination is disabled.
COMMENTS_INK_ITEMS_PER_PAGE = 25

# Name of the query string parameter containing the page number.
COMMENTS_INK_PAGE_QUERY_STRING_PARAM = "cpage"

# Name of the query string parameter containing the comments to fold.
COMMENTS_INK_FOLD_QUERY_STRING_PARAM = "cfold"

# All HTML elements rendered by django-comments-ink use the 'dci' CSS selector,
# defined in 'django_comments_ink/static/django_comments_ink/css/comments.css'.
# You can alter the CSS rules applied to your comments adding your own custom
# selector to the following setting. If you wanted to modify the .body of the
# comments with, say, a different padding, line-height and font color you could
# create do so by creating the following selector in your project's CSS:
#
#   .dci.dci-custom .comment-box .body {
#       padding: 8px;
#       line-height: 1.5;
#       color: #555;
#   }
#
# And adding the following setting to your settings module:
#
#    COMMENTS_INK_CSS_CUSTOM_SELECTOR = "dci dci-custom"
#
COMMENTS_INK_CSS_CUSTOM_SELECTOR = "dci"

# Name of the directory containing the theme templates.
# By default there are 3 theme directories:
#   'avatar_in_thread', 'avatar_in_header', 'twbs_5'.
#
# Use a theme by assigning any of those values to the COMMENTS_INK_THEME_DIR
# setting. You can create your own theme templates by adding a new theme
# directory to your Django project template's directory,
# under `comments/themes/<your-theme>`.
#
COMMENTS_INK_THEME_DIR = ""

# Name of the entry in settings.CACHE to use for caching django-comments-ink.
COMMENTS_INK_CACHE_NAME = "dci"

COMMENTS_INK_CACHE_KEYS = {
    # The key 'comments_qs' holds the QuerySet by the given params.
    "comments_qs": "/comments_qs/{ctype_pk}/{object_pk}/{site_id}",
    # The key 'comments_count' stores the number of
    # comments returned by the previous QuerySet.
    "comments_count": "/comments_count/{ctype_pk}/{object_pk}/{site_id}",
    # The key 'comments_paged' stores a dictionary of k: v, where
    # keys are combinations of page number and folded comments, and
    # values are cache keys where to find the computed values that
    # correspond to the output of paginate_querysey.
    "comments_paged": "/comments_paged/{ctype_pk}/{object_pk}/{site_id}",
    # The key 'comment_reactions' stores the json output produced by
    # InkComment.get_reactions(), for the comment receiving the method.
    "comment_reactions": "/comment_reactions/cm/{comment_id}",
    # The key 'object_reactions' stores the json output produced by
    # get_object_reactions(ctype_pk, object_pk, site_id).
    "object_reactions": "/object_reactions/{ctype_pk}/{object_pk}/{site_id}",
}
