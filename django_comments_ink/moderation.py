from django import VERSION
from django.contrib.sites.shortcuts import get_current_site
from django.template import Context, loader
from django_comments import get_model
from django_comments.models import CommentFlag
from django_comments.moderation import CommentModerator, Moderator
from django_comments.signals import comment_was_flagged, comment_will_be_posted
from django_comments_ink.conf import settings
from django_comments_ink.models import BlackListedDomain, TmpInkComment
from django_comments_ink.signals import confirmation_received
from django_comments_ink.utils import send_mail


class InkCommentModerator(CommentModerator):
    """
    Encapsulates comment-moderation options for a given-model.

    This class extends ``django_comments.moderation.CommentModerator``. It's not
    designed to be used directly, since it doesn't enable any of the available
    moderation options. Instead, subclass it and override attributes to enable
    different options::

    ``removal_suggestion_notification``
        If ``True``, any new removal suggestion flag on an object
        of this model will generate an email to site staff. Default
        value is ``False``.

    Check parent class to see inherited options.

    Most common moderation needs can be covered by changing option attributes,
    but further customization can be obtained by subclassing and overriding
    the following method::

    ``notify_removal_suggestion``
         If removal suggestion notifications should be sent to site staff
         or moderators, this method is responsible for sending the email.

    Check the parent class to read about methods ``allow``, ``email``, and
    ``moderate``.

    """

    removal_suggestion_notification = None

    def notify_removal_suggestion(self, comment, content_object, request):
        if not self.removal_suggestion_notification:
            return
        recipient_list = [
            manager_tuple[1] for manager_tuple in settings.MANAGERS
        ]
        t = loader.get_template("comments/removal_notification_email.txt")
        c = {
            "comment": comment,
            "content_object": content_object,
            "current_site": get_current_site(request),
            "request": request,
        }
        subject = '[%s] Comment removal suggestion on "%s"' % (
            c["current_site"].name,
            content_object,
        )
        message = t.render(Context(c) if VERSION < (1, 8) else c)
        send_mail(
            subject,
            message,
            settings.COMMENTS_INK_FROM_EMAIL,
            recipient_list,
            fail_silently=True,
        )


class SpamModerator(InkCommentModerator):
    """
    Discard messages comming from blacklisted domains.

    The current list of blacklisted domains had been fetched from
    http://www.joewein.net/spam/blacklist.htm

    You can download for free a recent version of the list, and subscribe
    to get notified on changes. Changes can be fetched with rsync for a
    small fee (check their conditions, or use any other Spam filter).

    django-comments-ink approach against spam consist of requiring comment
    confirmation by email. However spam comments could be discarded even
    before sending the confirmation email by searching sender's domain in
    the list of blacklisted domains.

    ``SpamModerator`` uses the additional ``django_comments_ink`` model:
     * ``BlackListedDomain``

    Remember to update the content regularly through an external Spam
    filtering service.
    """

    def allow(self, comment, content_object, request):
        # There is no way the comment.user_email does not get validated.
        # Whether coming from anonymous user or registered user.
        # So it has to contain an '@' attribute.
        domain = comment.user_email.split("@", 1)[1]
        if BlackListedDomain.objects.filter(domain=domain).count():
            return False
        return super(SpamModerator, self).allow(
            comment, content_object, request
        )


class InkModerator(Moderator):
    def connect(self):
        comment_will_be_posted.connect(
            self.pre_save_moderation, sender=TmpInkComment
        )
        confirmation_received.connect(
            self.post_save_moderation, sender=TmpInkComment
        )
        comment_was_flagged.connect(self.comment_flagged, sender=get_model())

    def comment_flagged(
        self, sender, comment, flag, created, request, **kwargs
    ):
        model = comment.content_type.model_class()
        if model not in self._registry:
            return
        if flag.flag != CommentFlag.SUGGEST_REMOVAL:
            return
        self._registry[model].notify_removal_suggestion(
            comment, comment.content_object, request
        )


moderator = InkModerator()
