from django import http
from django.apps import apps
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.contrib.sites.shortcuts import get_current_site
from django.core import signing
from django.core.exceptions import (
    ImproperlyConfigured,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db.utils import NotSupportedError
from django.shortcuts import render, resolve_url
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.defaults import bad_request
from django.views.generic.edit import FormView

from django_comments.signals import comment_was_posted, comment_will_be_posted
from django_comments.views.comments import CommentPostBadRequest

from django_comments_ink import get_form, get_model
from django_comments_ink import signals, signed, utils
from django_comments_ink.conf import settings
from django_comments_ink.models import (
    MaxThreadLevelExceededException,
    TmpInkComment,
)
from django_comments_ink.views.base import (
    CommentsParamsMixin,
    JsonResponseMixin,
    SingleCommentView,
)
from django_comments_ink.views.templates import theme_dir, themed_templates


InkComment = get_model()


class BadRequest(Exception):
    """Exception raised for a bad post request."""

    def __init__(self, why):
        self.why = why


# ---------------------------------------------------------------------
def send_email_confirmation_request(
    comment,
    key,
    site,
    text_template="comments/email_confirmation_request.txt",
    html_template="comments/email_confirmation_request.html",
):
    """Send email requesting comment confirmation"""
    subject = _("comment confirmation request")
    confirmation_url = reverse(
        "comments-ink-confirm", args=[key.decode("utf-8")]
    )
    message_context = {
        "comment": comment,
        "confirmation_url": confirmation_url,
        "contact": settings.COMMENTS_INK_CONTACT_EMAIL,
        "site": site,
    }
    # prepare text message
    text_message_template = get_template(text_template)
    text_message = text_message_template.render(message_context)
    if settings.COMMENTS_INK_SEND_HTML_EMAIL:
        # prepare html message
        html_message_template = get_template(html_template)
        html_message = html_message_template.render(message_context)
    else:
        html_message = None

    utils.send_mail(
        subject,
        text_message,
        settings.COMMENTS_INK_FROM_EMAIL,
        [
            comment.user_email,
        ],
        html=html_message,
    )


# ---------------------------------------------------------------------
def get_comment_if_exists(comment: TmpInkComment):
    """
    Returns either an InkComment matching the TmpInkComment, or None.

    The attributes that have to match between the TmpInkComment and the
    InkComment are 'user_name', 'user_email' and 'submit_date'.

    """
    return InkComment.objects.filter(
        user_name=comment.user_name,
        user_email=comment.user_email,
        followup=comment.followup,
        submit_date=comment.submit_date,
    ).first()


def create_comment(tmp_comment):
    """
    Creates an InkComment from a TmpInkComment.
    """
    tmp_comment.pop("comments_page", None)
    comment = InkComment(**tmp_comment)
    comment.save()
    return comment


# ---------------------------------------------------------------------
def notify_comment_followers(comment):
    followers = {}
    kwargs = {
        "content_type": comment.content_type,
        "object_pk": comment.object_pk,
        "is_public": True,
        "followup": True,
    }
    previous_comments = InkComment.objects.filter(**kwargs).exclude(
        user_email=comment.user_email
    )

    def feed_followers(gen):
        for instance in gen:
            followers[instance.user_email] = (
                instance.user_name,
                signed.dumps(
                    instance,
                    compress=True,
                    extra_key=settings.COMMENTS_INK_SALT,
                ),
            )

    try:
        gen = previous_comments.distinct("user_email").order_by("user_email")
        feed_followers(gen)
    except NotSupportedError:
        feed_followers(previous_comments)

    for instance in previous_comments:
        followers[instance.user_email] = (
            instance.user_name,
            signed.dumps(
                instance, compress=True, extra_key=settings.COMMENTS_INK_SALT
            ),
        )

    subject = _("new comment posted")
    text_message_template = get_template("comments/email_followup_comment.txt")
    if settings.COMMENTS_INK_SEND_HTML_EMAIL:
        html_message_template = get_template(
            "comments/email_followup_comment.html"
        )

    for email, (name, key) in followers.items():
        mute_url = reverse("comments-ink-mute", args=[key.decode("utf-8")])
        message_context = {
            "user_name": name,
            "comment": comment,
            "content_object": comment.content_object,
            "mute_url": mute_url,
            "site": comment.site,
        }
        text_message = text_message_template.render(message_context)
        if settings.COMMENTS_INK_SEND_HTML_EMAIL:
            html_message = html_message_template.render(message_context)
        else:
            html_message = None
        utils.send_mail(
            subject,
            text_message,
            settings.COMMENTS_INK_FROM_EMAIL,
            [
                email,
            ],
            html=html_message,
        )


def confirm(
    request,
    key,
    template_discarded=themed_templates("discarded"),
    template_moderated=themed_templates("moderated"),
):
    try:
        tmp_comment = signed.loads(
            str(key), extra_key=settings.COMMENTS_INK_SALT
        )
    except (ValueError, signed.BadSignature) as exc:
        return bad_request(request, exc)

    # The comment does exist if the URL was already confirmed,
    # in such a case, as per suggested in ticket #80, we return
    # the comment's URL, as if the comment is just confirmed.
    comment = get_comment_if_exists(tmp_comment)
    comments_page = tmp_comment.pop("comments_page", None)

    if comment is not None:
        if getattr(settings, "COMMENTS_INK_COMMENTS_PER_PAGE", 0) == 0:
            return utils.redirect_to(comment, comments_page=1)
        else:
            comments_page = utils.get_comment_page_number(request, comment)
            return utils.redirect_to(comment, comments_page=comments_page)

    # Send signal that the comment confirmation has been received.
    responses = signals.confirmation_received.send(
        sender=TmpInkComment, comment=tmp_comment, request=request
    )
    # Check whether a signal receiver decides to discard the comment.
    for receiver, response in responses:
        if response is False:
            return render(request, template_discarded, {"comment": tmp_comment})

    comment = create_comment(tmp_comment)
    if comment.is_public is False:
        template_list = [
            pth.format(
                theme_dir=theme_dir,
                app_label=comment.content_type.app_label,
                model=comment.content_type.model,
            )
            for pth in template_moderated
        ]
        return render(request, template_list, {"comment": comment})
    else:
        notify_comment_followers(comment)
        if getattr(settings, "COMMENTS_INK_COMMENTS_PER_PAGE", 0) == 0:
            return utils.redirect_to(comment, comments_page=1)
        else:
            comments_page = utils.get_comment_page_number(request, comment)
            return utils.redirect_to(comment, comments_page=comments_page)


def sent(
    request,
    using=None,
    template_posted=themed_templates("posted"),
    template_moderated=themed_templates("moderated"),
):
    comment_pk = request.GET.get("c", None)
    if not comment_pk:
        return CommentPostBadRequest("Comment doesn't exist")
    try:
        comment_pk = int(comment_pk)
        comment = InkComment.objects.get(pk=comment_pk)
    except (TypeError, ValueError, InkComment.DoesNotExist):
        try:
            value = signing.loads(comment_pk)
            ctype, object_pk = value.split(":")
            model = apps.get_model(*ctype.split(".", 1))
            target = model._default_manager.using(using).get(pk=object_pk)
        except Exception:
            return CommentPostBadRequest("Comment doesn't exist")
        return render(request, template_posted, {"target": target})
    else:
        if comment.is_public:
            return utils.redirect_to(comment, request=request)
        else:
            template_list = [
                pth.format(
                    theme_dir=theme_dir,
                    app_label=comment.content_type.app_label,
                    model=comment.content_type.model,
                )
                for pth in template_moderated
            ]
            return render(request, template_list, {"comment": comment})


# ---------------------------------------------------------------------
def on_comment_will_be_posted(sender, comment, request, **kwargs):
    """
    Check whether there are conditions to reject the post.

    Returns False if there are conditions to reject the comment.
    """
    if settings.COMMENTS_APP != "django_comments_ink":  # pragma: no cover
        # Do not kill the post if handled by other commenting app.
        return True

    if comment.user:
        user_is_authenticated = comment.user.is_authenticated
    else:
        user_is_authenticated = False

    ct = comment.get("content_type")
    options = utils.get_app_model_options(content_type=ct)
    if not user_is_authenticated and options["who_can_post"] == "users":
        # Reject comment.
        return False
    else:
        return True


comment_will_be_posted.connect(on_comment_will_be_posted, sender=TmpInkComment)


# ---------------------------------------------------------------------
def on_comment_was_posted(sender, comment, request, **kwargs):
    """
    Post the comment if a user is authenticated or send a confirmation email.

    On signal django_comments.signals.comment_was_posted check if the
    user is authenticated or if settings.COMMENTS_INK_CONFIRM_EMAIL is False.
    In both cases will post the comment. Otherwise will send a confirmation
    email to the person who posted the comment.
    """
    if settings.COMMENTS_APP != "django_comments_ink":  # pragma: no cover
        return False
    if comment.user:
        user_is_authenticated = comment.user.is_authenticated
    else:
        user_is_authenticated = False

    if not settings.COMMENTS_INK_CONFIRM_EMAIL or user_is_authenticated:
        if get_comment_if_exists(comment) is None:
            new_comment = create_comment(comment)
            comment.ink_comment = new_comment
            signals.confirmation_received.send(
                sender=TmpInkComment, comment=comment, request=request
            )
            if comment.is_public:
                notify_comment_followers(new_comment)
    else:
        key = signed.dumps(
            comment, compress=True, extra_key=settings.COMMENTS_INK_SALT
        )
        site = get_current_site(request)
        send_email_confirmation_request(comment, key, site)


comment_was_posted.connect(on_comment_was_posted, sender=TmpInkComment)


# ---------------------------------------------------------------------
@method_decorator(csrf_protect, name="dispatch")
class PostCommentView(CommentsParamsMixin, JsonResponseMixin, FormView):
    context_object_name = "comment"
    http_method_names = ["post"]
    bad_form_template_list = themed_templates("bad_form")
    template_list = themed_templates("preview")
    is_ajax = False

    # Templates when returning from an Ajax request.
    template_form_js = themed_templates("form_js")
    template_reply_form_js = themed_templates("reply_form_js")
    template_posted_js = themed_templates("posted_js")
    template_published_js = themed_templates("published_js")
    template_moderated_js = themed_templates("moderated_js")

    def get_target_object(self, data):
        ctype = data.get("content_type")
        object_pk = data.get("object_pk")
        if ctype is None or object_pk is None:
            raise BadRequest("Missing content_type or object_pk field.")

        self.using = self.kwargs.get("using")
        try:
            model = apps.get_model(*ctype.split(".", 1))
            return model._default_manager.using(self.using).get(pk=object_pk)
        except (LookupError, TypeError):
            raise BadRequest("Invalid content_type value: %r" % escape(ctype))
        except AttributeError:
            raise BadRequest(
                "The given content-type %r does not resolve to a valid model."
                % escape(ctype)
            )
        except ObjectDoesNotExist:
            raise BadRequest(
                "No object matching content-type %r and object PK %r exists."
                % (escape(ctype), escape(object_pk))
            )
        except (ValueError, ValidationError) as e:
            raise BadRequest(
                "Attempting to get content-type %r and object PK %r raised %s"
                % (escape(ctype), escape(object_pk), e.__class__.__name__)
            )

    def get_form_kwargs(self):
        data = self.request.POST.copy()
        if self.request.user.is_authenticated:
            if not data.get("name", ""):
                data["name"] = (
                    self.request.user.get_full_name()
                    or self.request.user.get_username()
                )
            if not data.get("email", ""):
                data["email"] = self.request.user.email
        return data

    def get_form_class(self):
        return get_form()

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.target_object, data=self.data)

    def create_comment(self, form):
        self.read_comments_params()
        comment = form.get_comment_object(
            site_id=get_current_site(self.request).id
        )
        comment.ip_address = self.request.META.get("REMOTE_ADDR", None) or None
        comment.comments_page = self.comments_page
        if self.request.user.is_authenticated:
            comment.user = self.request.user

        # Signal that the comment is about to be saved.
        responses = comment_will_be_posted.send(
            sender=comment.__class__, comment=comment, request=self.request
        )

        for receiver, response in responses:
            if response is False:
                msg = (
                    "comment_will_be_posted receiver %r killed the comment"
                    % receiver.__name__
                )
                raise BadRequest(msg)

        # Save the comment and signal that it was saved
        comment.save()
        comment_was_posted.send(
            sender=comment.__class__, comment=comment, request=self.request
        )
        return comment

    def get_bad_form_template_names(self):
        if self.bad_form_template_list is None:
            raise ImproperlyConfigured(
                "PostCommentView requires either a definition of "
                "'bad_form_template_list' or an implementation of "
                "'get_bad_form_template_names()'"
            )

        return [
            pth.format(theme_dir=theme_dir)
            for pth in self.bad_form_template_list
        ]

    def get_template_names(self, default=None):
        if default:
            template_list = default
        elif self.is_ajax:
            if self.data.get("reply_to", "0") != "0":
                template_list = self.template_reply_form_js
            else:
                template_list = self.template_form_js
        else:
            template_list = self.template_list

        if template_list is None:
            raise ImproperlyConfigured(
                "PostCommentView requires either a definition of "
                "'template_list' or an implementation of "
                "'get_template_names()'"
            )

        return [
            pth.format(
                theme_dir=theme_dir,
                app_label=self.target_object._meta.app_label,
                model=self.target_object._meta.model_name,
            )
            for pth in template_list
        ]

    def get_success_url(self):
        return self.get_next_redirect_url(
            "comments-comment-done", c=self.object._get_pk_val()
        )

    def get_context_data(self, **kwargs):
        kwargs.update(self.get_comments_params_dict())
        if "form" in kwargs:
            form = kwargs.get("form")
            kwargs.update(
                {
                    "is_reply": form.data.get("reply_to", "0") != "0",
                    "next": self.data.get("next", None),
                }
            )
            if self.is_ajax:
                if form.errors:
                    field_focus = [key for key in form.errors.keys()][0]
                else:
                    field_focus = None
                kwargs.update(
                    {
                        "display_preview": not form.errors,
                        "field_focus": field_focus,
                    }
                )
        return super().get_context_data(**kwargs)

    def comment_posted(self):
        try:
            value = signing.loads(self.object._get_pk_val())
            ctype, object_pk = value.split(":")
            model = apps.get_model(*ctype.split(".", 1))
            target = model._default_manager.using(self.using).get(pk=object_pk)
        except Exception:
            context = {"bad_error": "Comment does not exist."}
            return self.json_response(
                self.bad_form_template_list, context, status=400
            )

        app_label, model_name = ctype.split(".", 1)
        template_list = [
            pth.format(
                theme_dir=theme_dir, app_label=app_label, model=model_name
            )
            for pth in self.template_posted_js
        ]

        return self.json_response(template_list, {"target": target}, status=202)

    def comment_published(self):
        template_list = self.get_template_names(self.template_published_js)
        comment_page = utils.get_comment_page_number(self.request, self.object)
        comment_url = utils.get_comment_url(self.object, None, comment_page)
        return self.json_response(
            template_list,
            {"comment": self.object, "comment_url": comment_url},
            status=201,
        )

    def comment_moderated(self):
        template_list = self.get_template_names(self.template_moderated_js)
        return self.json_response(
            template_list, {"comment": self.object}, status=201
        )

    def post_js_response(self):
        try:
            self.object = InkComment.objects.get(pk=self.object._get_pk_val())
        except (TypeError, ValueError, InkComment.DoesNotExist):
            return self.comment_posted()
        else:
            if self.object.is_public:
                return self.comment_published()
            else:
                return self.comment_moderated()

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        if self.is_ajax:
            return self.json_response(
                self.get_template_names(), context, status=200
            )
        else:
            return self.render_to_response(context)

    def post(self, request, **kwargs):
        self.object = None
        self.target_object = None
        self.data = self.get_form_kwargs()

        if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
            self.is_ajax = True

        try:
            self.target_object = self.get_target_object(self.data)
        except BadRequest as exc:
            if self.is_ajax:
                context = {"bad_error": exc.why}
                bad_form_tmpl = self.get_bad_form_template_names()
                return self.json_response(bad_form_tmpl, context, status=400)
            else:
                return CommentPostBadRequest(exc.why)
        else:
            if self.is_ajax:
                bad_form_tmpl = self.get_bad_form_template_names()

        form = self.get_form()

        if form.security_errors():
            if self.is_ajax:
                error_msg = "The comment form failed security verification."
                context = {"bad_error": error_msg}
                return self.json_response(bad_form_tmpl, context, status=400)
            else:
                return CommentPostBadRequest(
                    "The comment form failed security verification: %s"
                    % escape(str(form.security_errors()))
                )

        if not form.is_valid() or "preview" in self.data:
            return self.form_invalid(form)
        else:
            try:
                self.object = self.create_comment(form)
            except BadRequest as exc:
                if self.is_ajax:
                    if not settings.DEBUG:  # pragma: no cover
                        msg = "Your comment has been rejected."
                    else:
                        msg = exc.why
                    return self.json_response(
                        self.get_bad_form_template_names(),
                        {"bad_error": msg},
                        status=400,
                    )
                return CommentPostBadRequest(exc.why)
            else:
                if self.is_ajax:
                    return self.post_js_response()
                else:
                    return self.form_valid(form)


# ---------------------------------------------------------------------
class ReplyCommentView(SingleCommentView):
    http_method_names = [
        "get",
    ]
    template_list = themed_templates("reply")

    def get(self, request, comment_id):
        self.object = self.get_object(comment_id)

        if not self.object.allow_thread():
            return http.HttpResponseForbidden(
                MaxThreadLevelExceededException(self.object)
            )

        if (
            not self.request.user.is_authenticated
            and self.options["who_can_post"] == "users"
        ):
            path = request.build_absolute_uri()
            login_url = resolve_url(settings.LOGIN_URL)
            return redirect_to_login(path, login_url, REDIRECT_FIELD_NAME)

        form = get_form()(self.object.content_object, comment=self.object)
        next = request.GET.get("next", reverse("comments-ink-sent"))
        context = self.get_context_data(form=form, next=next)
        return self.render_to_response(context)
