from django.utils.translation import ugettext as _
from django_comments_ink.models import BaseReactionEnum


# ----------------------------------------------------
class CommentReactionEnum(BaseReactionEnum):
    LIKE_IT = "+", _("Like")
    DISLIKE_IT = "-", _("Dislike")
    SMILE = "S", _("Smile")
    CONFUSED = "C", _("Confused")
    GREAT = "G", _("Great")
    HEART = "H", _("Heart")
    ROCKET = "R", _("Rocket")
    EYES = "E", _("Eyes")


CommentReactionEnum.set_icons(
    {
        CommentReactionEnum.LIKE_IT: "#128077",
        CommentReactionEnum.DISLIKE_IT: "#128078",
        CommentReactionEnum.SMILE: "#128512",
        CommentReactionEnum.CONFUSED: "#128533",
        CommentReactionEnum.GREAT: "#127881",
        CommentReactionEnum.ROCKET: "#128640",
        CommentReactionEnum.HEART: "#10084",
        CommentReactionEnum.EYES: "#128064",
    }
)


# ----------------------------------------------------
class ObjectReactionEnum(BaseReactionEnum):
    LIKE_IT = "+", _("Like")
    DISLIKE_IT = "-", _("Dislike")


ObjectReactionEnum.set_icons(
    {
        ObjectReactionEnum.LIKE_IT: "#128077",
        ObjectReactionEnum.DISLIKE_IT: "#128078",
    }
)
