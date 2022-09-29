from django_comments_ink.conf import settings
from django_comments_ink.utils import does_theme_dir_exist


theme_dir = None
theme_dir_exists = None


def check_theme():
    global theme_dir, theme_dir_exists
    if theme_dir is not None and theme_dir_exists is not None:
        return

    if len(settings.COMMENTS_INK_THEME) > 0:
        theme_dir = f"themes/{settings.COMMENTS_INK_THEME}"
        theme_dir_exists = does_theme_dir_exist(f"comments/{theme_dir}")
    else:
        theme_dir = ""
        theme_dir_exists = False


t = {
    "list": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/list.html",
            "comments/{theme_dir}/{app_label}/list.html",
            "comments/{theme_dir}/list.html",
            "comments/{app_label}/{model}/list.html",
            "comments/{app_label}/list.html",
            "comments/list.html",
        ],
        "default": [
            "comments/{app_label}/{model}/list.html",
            "comments/{app_label}/list.html",
            "comments/list.html",
        ],
    },
    "form": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/form.html",
            "comments/{theme_dir}/{app_label}/form.html",
            "comments/{theme_dir}/form.html",
            "comments/{app_label}/{model}/form.html",
            "comments/{app_label}/form.html",
            "comments/form.html",
        ],
        "default": [
            "comments/{app_label}/{model}/form.html",
            "comments/{app_label}/form.html",
            "comments/form.html",
        ],
    },
    "preview": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/preview.html",
            "comments/{theme_dir}/{app_label}/preview.html",
            "comments/{theme_dir}/preview.html",
            "comments/{app_label}/{model}/preview.html",
            "comments/{app_label}/preview.html",
            "comments/preview.html",
        ],
        "default": [
            "comments/{app_label}/{model}/preview.html",
            "comments/{app_label}/preview.html",
            "comments/preview.html",
        ],
    },
    "discarded": {
        "themed": [
            f"comments/{theme_dir}/discarded.html",
            "comments/discarded.html",
        ],
        "default": "comments/discarded.html",
    },
    "moderated": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/moderated.html",
            "comments/{theme_dir}/{app_label}/moderated.html",
            "comments/{theme_dir}/moderated.html",
            "comments/{app_label}/{model}/moderated.html",
            "comments/{app_label}/moderated.html",
            "comments/moderated.html",
        ],
        "default": [
            "comments/{app_label}/{model}/moderated.html",
            "comments/{app_label}/moderated.html",
            "comments/moderated.html",
        ],
    },
    "posted": {
        "themed": [f"comments/{theme_dir}/posted.html", "comments/posted.html"],
        "default": "comments/posted.html",
    },
    "posted_js": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/posted_js.html",
            "comments/{theme_dir}/{app_label}/posted_js.html",
            "comments/{theme_dir}/posted_js.html",
            "comments/{app_label}/{model}/posted_js.html",
            "comments/{app_label}/posted_js.html",
            "comments/posted_js.html",
        ],
        "default": [
            "comments/{app_label}/{model}/posted_js.html",
            "comments/{app_label}/posted_js.html",
            "comments/posted_js.html",
        ],
    },
    "bad_form": {
        "themed": [
            f"comments/{theme_dir}/bad_form.html",
            "comments/bad_form.html",
        ],
        "default": [
            "comments/bad_form.html",
        ],
    },
    "form_js": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/form_js.html",
            "comments/{theme_dir}/{app_label}/form_js.html",
            "comments/{theme_dir}/form_js.html",
            "comments/{app_label}/{model}/form_js.html",
            "comments/{app_label}/form_js.html",
            "comments/form_js.html",
        ],
        "default": [
            "comments/{app_label}/{model}/form_js.html",
            "comments/{app_label}/form_js.html",
            "comments/form_js.html",
        ],
    },
    "reply_form_js": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/reply_form_js.html",
            "comments/{theme_dir}/{app_label}/reply_form_js.html",
            "comments/{theme_dir}/reply_form_js.html",
            "comments/{app_label}/{model}/reply_form_js.html",
            "comments/{app_label}/reply_form_js.html",
            "comments/reply_form_js.html",
        ],
        "default": [
            "comments/{app_label}/{model}/reply_form_js.html",
            "comments/{app_label}/reply_form_js.html",
            "comments/reply_form_js.html",
        ],
    },
    "published_js": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/published_js.html",
            "comments/{theme_dir}/{app_label}/published_js.html",
            "comments/{theme_dir}/published_js.html",
            "comments/{app_label}/{model}/published_js.html",
            "comments/{app_label}/published_js.html",
            "comments/published_js.html",
        ],
        "default": [
            "comments/{app_label}/{model}/published_js.html",
            "comments/{app_label}/published_js.html",
            "comments/published_js.html",
        ],
    },
    "moderated_js": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/moderated_js.html",
            "comments/{theme_dir}/{app_label}/moderated_js.html",
            "comments/{theme_dir}/moderated_js.html",
            "comments/{app_label}/{model}/moderated_js.html",
            "comments/{app_label}/moderated_js.html",
            "comments/moderated_js.html",
        ],
        "default": [
            "comments/{app_label}/{model}/moderated_js.html",
            "comments/{app_label}/moderated_js.html",
            "comments/moderated_js.html",
        ],
    },
    "reply": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/reply.html",
            "comments/{theme_dir}/{app_label}/reply.html",
            "comments/{theme_dir}/reply.html",
            "comments/{app_label}/{model}/reply.html",
            "comments/{app_label}/reply.html",
            "comments/reply.html",
        ],
        "default": [
            "comments/{app_label}/{model}/reply.html",
            "comments/{app_label}/reply.html",
            "comments/reply.html",
        ],
    },
    "reply_template": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/reply_template.html",
            "comments/{theme_dir}/{app_label}/reply_template.html",
            "comments/{theme_dir}/reply_template.html",
            "comments/{app_label}/{model}/reply_template.html",
            "comments/{app_label}/reply_template.html",
            "comments/reply_template.html",
        ],
        "default": [
            "comments/{app_label}/{model}/reply_template.html",
            "comments/{app_label}/reply_template.html",
            "comments/reply_template.html",
        ],
    },
    "muted": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/muted.html",
            "comments/{theme_dir}/{app_label}/muted.html",
            "comments/{theme_dir}/muted.html",
            "comments/{app_label}/{model}/muted.html",
            "comments/{app_label}/muted.html",
            "comments/muted.html",
        ],
        "default": [
            "comments/{app_label}/{model}/muted.html",
            "comments/{app_label}/muted.html",
            "comments/muted.html",
        ],
    },
    "react": {
        "themed": [
            f"comments/{theme_dir}/react.html",
            "comments/react.html",
        ],
        "default": ["comments/react.html"],
    },
    "reacted_js": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/comment_reactions.html",
            "comments/{theme_dir}/{app_label}/comment_reactions.html",
            "comments/{theme_dir}/comment_reactions.html",
            "comments/{app_label}/{model}/comment_reactions.html",
            "comments/{app_label}/comment_reactions.html",
            "comments/comment_reactions.html",
        ],
        "default": [
            "comments/{app_label}/{model}/comment_reactions.html",
            "comments/{app_label}/comment_reactions.html",
            "comments/comment_reactions.html",
        ],
    },
    "reacted": {
        "themed": [
            f"comments/{theme_dir}/reacted.html",
            "comments/reacted.html",
        ],
        "default": ["comments/reacted.html"],
    },
    "users_reacted_to_comment": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/"
            "users_reacted_to_comment.html",
            "comments/{theme_dir}/{app_label}/users_reacted_to_comment.html",
            "comments/{theme_dir}/users_reacted_to_comment.html",
            "comments/{app_label}/{model}/users_reacted_to_comment.html",
            "comments/{app_label}/users_reacted_to_comment.html",
            "comments/users_reacted_to_comment.html",
        ],
        "default": [
            "comments/{app_label}/{model}/users_reacted_to_comment.html",
            "comments/{app_label}/users_reacted_to_comment.html",
            "comments/users_reacted_to_comment.html",
        ],
    },
    "users_reacted_to_object": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/"
            "users_reacted_to_object.html",
            "comments/{theme_dir}/{app_label}/users_reacted_to_object.html",
            "comments/{theme_dir}/users_reacted_to_object.html",
            "comments/{app_label}/{model}/users_reacted_to_object.html",
            "comments/{app_label}/users_reacted_to_object.html",
            "comments/users_reacted_to_object.html",
        ],
        "default": [
            "comments/{app_label}/{model}/users_reacted_to_object.html",
            "comments/{app_label}/users_reacted_to_object.html",
            "comments/users_reacted_to_object.html",
        ],
    },
    "reactions_panel": {
        "themed": [
            "comments/{theme_dir}/reactions_panel_template.html",
            "comments/reactions_panel_template.html",
        ],
        "default": ["comments/reactions_panel_template.html"],
    },
    "reactions_buttons": {
        "themed": [
            "comments/{theme_dir}/reactions_buttons.html",
            "comments/reactions_buttons.html",
        ],
        "default": ["comments/reactions_buttons.html"],
    },
    "object_reactions": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/object_reactions.html"
            "comments/{theme_dir}/{app_label}/object_reactions_form.html",
            "comments/{theme_dir}/object_reactions_form.html",
            "comments/{app_label}/{model}/object_reactions.html",
            "comments/{app_label}/object_reactions.html",
            "comments/object_reactions.html",
        ],
        "default": [
            "comments/{app_label}/{model}/object_reactions.html",
            "comments/{app_label}/object_reactions.html",
            "comments/object_reactions.html",
        ],
    },
    "object_reactions_form": {
        "themed": [
            (
                "comments/{theme_dir}/{app_label}/{model}/"
                "object_reactions_form.html"
            ),
            "comments/{theme_dir}/{app_label}/object_reactions_form.html",
            "comments/{theme_dir}/object_reactions_form.html",
            "comments/{app_label}/{model}/object_reactions_form.html",
            "comments/{app_label}/object_reactions_form.html",
            "comments/object_reactions_form.html",
        ],
        "default": [
            "comments/{app_label}/{model}/object_reactions_form.html",
            "comments/{app_label}/object_reactions_form.html",
            "comments/object_reactions_form.html",
        ],
    },
    "vote": {
        "themed": [
            f"comments/{theme_dir}/vote.html",
            "comments/vote.html",
        ],
        "default": ["comments/vote.html"],
    },
    "voted": {
        "themed": [
            f"comments/{theme_dir}/voted.html",
            "comments/voted.html",
        ],
        "default": ["comments/voted.html"],
    },
    "voted_js": {
        "themed": [
            "comments/{theme_dir}/{app_label}/{model}/comment_votes.html",
            "comments/{theme_dir}/{app_label}/comment_votes.html",
            "comments/{theme_dir}/comment_votes.html",
            "comments/{app_label}/{model}/comment_votes.html",
            "comments/{app_label}/comment_votes.html",
            "comments/comment_votes.html",
        ],
        "default": [
            "comments/{app_label}/{model}/comment_votes.html",
            "comments/{app_label}/comment_votes.html",
            "comments/comment_votes.html",
        ],
    },
}


def themed_templates(alias):
    if theme_dir_exists:
        return t[alias]["themed"]
    else:
        return t[alias]["default"]


def f_templates(alias, **kwargs):
    templates = themed_templates(alias)
    return [
        template.format(theme_dir=theme_dir, **kwargs) for template in templates
    ]


check_theme()
