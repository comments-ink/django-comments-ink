from __future__ import unicode_literals

import json
import random
import re
import string
from datetime import datetime
from typing import List
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import pytest

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404, JsonResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

import django_comments
from django_comments.views.comments import CommentPostBadRequest
from rest_framework import status
from rest_framework.exceptions import ErrorDetail, PermissionDenied

from django_comments_ink import signals, signed
from django_comments_ink.conf import settings
from django_comments_ink.models import (
    CommentReaction,
    CommentThread,
    InkComment,
    ObjectReaction,
)
from django_comments_ink.views import base, commenting, reacting, templates
from django_comments_ink.views.base import CommentUrlView
from django_comments_ink.views.commenting import (
    confirm,
    PostCommentView,
    ReplyCommentView,
)
from django_comments_ink.views.muting import MuteCommentView
from django_comments_ink.views.reacting import (
    ReactedToCommentUserListView,
    ReactedToObjectUserListView,
    ReactToCommentDoneView,
    ReactToCommentView,
    ReactToObjectView,
)
from django_comments_ink.views.templates import themed_templates
from django_comments_ink.views.voting import (
    VoteCommentDoneView,
    VoteCommentView,
)

from django_comments_ink.tests.models import Article, Diary


request_factory = RequestFactory()

keys_in_SingleCommentView_context = [
    "comment",
    "who_can_post",
    "comment_votes_enabled",
    "comment_flagging_enabled",
    "comment_reactions_enabled",
    "object_reactions_enabled",
    "is_input_allowed",
    "comments_page_qs_param",
    "comments_page",
    "comments_folded_qs_param",
    "comments_folded",
]


def nope(target):
    return False


def post_article_comment(data, article, auth_user=None):
    request = request_factory.post(
        reverse(
            "article-detail",
            kwargs={
                "year": article.publish.year,
                "month": article.publish.month,
                "day": article.publish.day,
                "slug": article.slug,
            },
        ),
        data=data,
        follow=True,
    )
    if auth_user:
        request.user = auth_user
    else:
        request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    return PostCommentView.as_view()(request)


def post_diary_comment(data, diary_entry, auth_user=None):
    request = request_factory.post(
        reverse(
            "diary-detail",
            kwargs={
                "year": diary_entry.publish.year,
                "month": diary_entry.publish.month,
                "day": diary_entry.publish.day,
            },
        ),
        data=data,
        follow=True,
    )
    if auth_user:
        request.user = auth_user
    else:
        request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    return PostCommentView.as_view()(request)


def confirm_comment_url(key, follow=True):
    request = request_factory.get(
        reverse("comments-ink-confirm", kwargs={"key": key}), follow=follow
    )
    request.user = AnonymousUser()
    return confirm(request, key)


app_model_options_mock = {"tests.article": {"who_can_post": "users"}}


class OnCommentWasPostedTestCase(TestCase):
    def setUp(self):
        self.patcher = patch(
            "django_comments_ink.views.commenting.utils.send_mail"
        )
        self.mock_mailer = self.patcher.start()
        self.article = Article.objects.create(
            title="October", slug="october", body="What I did on October..."
        )
        self.form = django_comments.get_form()(self.article)
        self.user = AnonymousUser()

    def tearDown(self):
        self.patcher.stop()

    def post_valid_data(self, auth_user=None, response_code=302):
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal eine kleine...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, self.article, auth_user)
        self.assertEqual(response.status_code, response_code)
        if response.status_code == 302:
            self.assertTrue(response.url.startswith("/comments/sent/?c="))

    def post_invalid_data(
        self, auth_user=None, response_code=302, remove_fields: List[str] = []
    ):
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal eine kleine...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        if len(remove_fields):
            for field_name in remove_fields:
                data.pop(field_name)
        response = post_article_comment(data, self.article, auth_user)
        self.assertEqual(response.status_code, response_code)
        if response.status_code == 302:
            self.assertTrue(response.url.startswith("/comments/sent/?c="))

    def test_post_as_authenticated_user(self):
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        self.assertTrue(self.mock_mailer.call_count == 0)
        self.post_valid_data(auth_user=self.user)
        # no confirmation email sent as user is authenticated
        self.assertTrue(self.mock_mailer.call_count == 0)

    def test_post_as_authenticated_user_without_name_nor_email(self):
        data = {
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal eine kleine...",
        }
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        self.assertTrue(self.mock_mailer.call_count == 0)
        self.post_invalid_data(
            auth_user=self.user, remove_fields=["name", "email"]
        )
        # no confirmation email sent as user is authenticated via self.user.
        self.assertTrue(self.mock_mailer.call_count == 0)

    # def test_post_comment_form_without_content_type(self):
    #     self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
    #     self.assertTrue(self.mock_mailer.call_count == 0)
    #     self.post_invalid_data(
    #         auth_user=self.user,
    #         response_code=400,
    #         remove_fields=['content_type']
    #     )

    def test_confirmation_email_is_sent(self):
        self.assertTrue(self.mock_mailer.call_count == 0)
        self.post_valid_data()
        self.assertTrue(self.mock_mailer.call_count == 1)

    @patch.multiple(
        "django_comments_ink.conf.settings",
        COMMENTS_INK_APP_MODEL_OPTIONS=app_model_options_mock,
    )
    def test_post_as_visitor_when_only_users_can_post(self):
        self.assertTrue(self.mock_mailer.call_count == 0)
        self.post_valid_data(response_code=400)
        self.assertTrue(self.mock_mailer.call_count == 0)


class ConfirmCommentTestCase(TestCase):
    def setUp(self):
        patcher = patch("django_comments_ink.views.commenting.utils.send_mail")
        self.mock_mailer = patcher.start()
        # Create random string so that it's harder for zlib to compress
        content = "".join(random.choice(string.printable) for _ in range(6096))
        self.article = Article.objects.create(
            title="September",
            slug="september",
            body="In September..." + content,
        )
        self.form = django_comments.get_form()(self.article)
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal iene kleine...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        post_article_comment(data, self.article)
        self.assertTrue(self.mock_mailer.call_count == 1)
        self.key = str(
            re.search(
                r"http://.+/confirm/(?P<key>[\S]+)/",
                self.mock_mailer.call_args[0][1],
            ).group("key")
        )
        self.addCleanup(patcher.stop)

    def test_confirm_url_is_short_enough(self):
        # Tests that the length of the confirm url's length isn't
        # dependent on the article length.
        l = len(reverse("comments-ink-confirm", kwargs={"key": self.key}))
        self.assertLessEqual(l, 4096, "Urls can only be a max of 4096")

    def test_400_on_bad_signature(self):
        response = confirm_comment_url(self.key[:-1])
        self.assertEqual(response.status_code, 400)

    def test_consecutive_confirmation_url_visits_doesnt_fail(self):
        # test that consecutives visits to the same confirmation URL produce
        # an Http 404 code, as the comment has already been verified in the
        # first visit
        response = confirm_comment_url(self.key)
        self.assertEqual(response.status_code, 302)
        confirm_comment_url(self.key)
        self.assertEqual(response.status_code, 302)

    def test_signal_receiver_may_discard_the_comment(self):
        # test that receivers of signal confirmation_received may return False
        # and thus rendering a template_discarded output
        def on_signal(sender, comment, request, **kwargs):
            return False

        self.assertEqual(self.mock_mailer.call_count, 1)  # sent during setUp
        signals.confirmation_received.connect(on_signal)
        response = confirm_comment_url(self.key)
        # mailing avoided by on_signal:
        self.assertEqual(self.mock_mailer.call_count, 1)
        self.assertTrue(response.content.find(b"Comment discarded") > -1)

    def test_comment_is_created_and_view_redirect(self):
        # testing that visiting a correct confirmation URL creates a InkComment
        # and redirects to the article detail page
        Site.objects.get_current().domain = "testserver"  # django bug #7743
        response = confirm_comment_url(self.key, follow=False)
        data = signed.loads(self.key, extra_key=settings.COMMENTS_INK_SALT)
        try:
            comment = InkComment.objects.get(
                content_type=data["content_type"],
                user_name=data["user_name"],
                user_email=data["user_email"],
                submit_date=data["submit_date"],
            )
        except:
            comment = None
        self.assertTrue(comment is not None)
        self.assertEqual(response.url, comment.get_absolute_url())

    def test_notify_comment_followers(self):
        # send a couple of comments to the article with followup=True and check
        # that when the second comment is confirmed a followup notification
        # email is sent to the user who sent the first comment
        self.assertEqual(self.mock_mailer.call_count, 1)
        confirm_comment_url(self.key)
        # no comment followers yet:
        self.assertEqual(self.mock_mailer.call_count, 1)
        # send 2nd comment
        self.form = django_comments.get_form()(self.article)
        data = {
            "name": "Alice",
            "email": "alice@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal eine kleine...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, article=self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.key = re.search(
            r"http://.+/confirm/(?P<key>[\S]+)/",
            self.mock_mailer.call_args[0][1],
        ).group("key")
        confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 3)
        self.assertTrue(
            # We can find the 'comment' in the text_message.
            self.mock_mailer.call_args[0][1].index(data["comment"])
            > -1
        )
        articles_title = f"Post: {self.article.title}"
        self.assertTrue(
            # We can find article's title (comment.content_object.title).
            self.mock_mailer.call_args[0][1].index(articles_title)
            > -1
        )
        self.assertTrue(self.mock_mailer.call_args[0][3] == ["bob@example.com"])
        self.assertTrue(
            self.mock_mailer.call_args[0][1].find(
                "There is a new comment following up yours."
            )
            > -1
        )

    @patch.multiple(
        "django_comments_ink.conf.settings", COMMENTS_INK_SEND_HTML_EMAIL=False
    )
    def test_notify_comment_followers_with_SEND_HTML_EMAIL_eq_False(self):
        # send a couple of comments to the article with followup=True and check
        # that when the second comment is confirmed a followup notification
        # email is sent to the user who sent the first comment
        self.assertEqual(self.mock_mailer.call_count, 1)
        confirm_comment_url(self.key)
        # no comment followers yet:
        self.assertEqual(self.mock_mailer.call_count, 1)
        # send 2nd comment
        self.form = django_comments.get_form()(self.article)
        data = {
            "name": "Alice",
            "email": "alice@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal eine kleine...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, article=self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.key = re.search(
            r"http://.+/confirm/(?P<key>[\S]+)/",
            self.mock_mailer.call_args[0][1],
        ).group("key")
        confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 3)
        self.assertTrue(self.mock_mailer.call_args[0][3] == ["bob@example.com"])
        self.assertTrue(
            self.mock_mailer.call_args[0][1].find(
                "There is a new comment following up yours."
            )
            > -1
        )
        self.assertEqual(self.mock_mailer.call_args[1], {"html": None})

    def test_notify_followers_dupes(self):
        # first of all confirm Bob's comment otherwise it doesn't reach DB
        confirm_comment_url(self.key)
        # then put in play pull-request-15's assert...
        # https://github.com/danirus/django-comments-xtd/pull/15
        diary = Diary.objects.create(body="Lorem ipsum", allow_comments=True)
        self.assertEqual(diary.pk, self.article.pk)

        self.form = django_comments.get_form()(diary)
        data = {
            "name": "Charlie",
            "email": "charlie@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal eine kleine...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_diary_comment(data, diary_entry=diary)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        self.key = str(
            re.search(
                r"http://.+/confirm/(?P<key>[\S]+)/",
                self.mock_mailer.call_args[0][1],
            ).group("key")
        )
        # 1) confirmation for Bob (sent in `setUp()`)
        # 2) confirmation for Charlie
        self.assertEqual(self.mock_mailer.call_count, 2)
        response = confirm_comment_url(self.key)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/cr/"))
        self.assertEqual(self.mock_mailer.call_count, 2)

        self.form = django_comments.get_form()(self.article)
        data = {
            "name": "Alice",
            "email": "alice@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmal iene kleine...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, article=self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        self.assertEqual(self.mock_mailer.call_count, 3)
        self.key = re.search(
            r"http://.+/confirm/(?P<key>[\S]+)/",
            self.mock_mailer.call_args[0][1],
        ).group("key")
        confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 4)
        self.assertTrue(self.mock_mailer.call_args[0][3] == ["bob@example.com"])
        self.assertTrue(
            self.mock_mailer.call_args[0][1].find(
                "There is a new comment following up yours."
            )
            > -1
        )

    def test_no_notification_for_same_user_email(self):
        # test that a follow-up user_email don't get a notification when
        # sending another email to the thread
        self.assertEqual(self.mock_mailer.call_count, 1)
        confirm_comment_url(self.key)  # confirm Bob's comment
        # no comment followers yet:
        self.assertEqual(self.mock_mailer.call_count, 1)
        # send Bob's 2nd comment
        self.form = django_comments.get_form()(self.article)
        data = {
            "name": "Alice",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Bob's comment he shouldn't get notified about",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.key = re.search(
            r"http://.+/confirm/(?P<key>[\S]+)/",
            self.mock_mailer.call_args[0][1],
        ).group("key")
        confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 2)


class ReplyNoCommentTestCase(TestCase):
    def test_reply_non_existing_comment_raises_404(self):
        response = self.client.get(reverse("comments-ink-reply", args=(1,)))
        self.assertContains(response, "404", status_code=404)


class ReplyCommentTestCase(TestCase):
    def setUp(self):
        article = Article.objects.create(
            title="September",
            slug="september",
            body="What I did on September...",
        )
        article_ct = ContentType.objects.get(app_label="tests", model="article")
        site = Site.objects.get(pk=1)

        # post Comment 1 to article, level 0
        InkComment.objects.create(
            content_type=article_ct,
            object_pk=article.id,
            content_object=article,
            site=site,
            comment="comment 1 to article",
            submit_date=datetime.now(),
        )

        # post Comment 2 to article, level 1
        InkComment.objects.create(
            content_type=article_ct,
            object_pk=article.id,
            content_object=article,
            site=site,
            comment="comment 1 to comment 1",
            submit_date=datetime.now(),
            parent_id=1,
        )

        # post Comment 3 to article, level 2 (max according to test settings)
        InkComment.objects.create(
            content_type=article_ct,
            object_pk=article.id,
            content_object=article,
            site=site,
            comment="comment 1 to comment 1",
            submit_date=datetime.now(),
            parent_id=2,
        )

    def test_reply_view(self):
        response = self.client.get(reverse("comments-ink-reply", args=(3,)))
        self.assertEqual(response.status_code, 200)

    @patch.multiple(
        "django_comments_ink.conf.settings", COMMENTS_INK_MAX_THREAD_LEVEL=2
    )
    def test_not_allow_threaded_reply_raises_403(self):
        response = self.client.get(reverse("comments-ink-reply", args=(3,)))
        self.assertEqual(response.status_code, 403)

    @patch.multiple(
        "django_comments_ink.conf.settings",
        COMMENTS_INK_APP_MODEL_OPTIONS=app_model_options_mock,
    )
    def test_reply_as_visitor_when_only_users_can_post(self):
        response = self.client.get(reverse("comments-ink-reply", args=(1,)))
        self.assertEqual(response.status_code, 302)  # Redirect to login.
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))


class MuteFollowUpTestCase(TestCase):
    def setUp(self):
        # Creates an article and send two comments to the article with
        # follow-up notifications. First comment doesn't have to send any
        #  notification.
        # Second comment has to send one notification (to Bob).
        patcher = patch("django_comments_ink.views.commenting.utils.send_mail")
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="September", slug="september", body="John's September"
        )
        self.form = django_comments.get_form()(self.article)

        # Bob sends 1st comment to the article with follow-up
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Nice September you had...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        self.assertTrue(self.mock_mailer.call_count == 1)
        bobkey = str(
            re.search(
                r"http://.+/confirm/(?P<key>[\S]+)/",
                self.mock_mailer.call_args[0][1],
            ).group("key")
        )
        confirm_comment_url(bobkey)  # confirm Bob's comment

        # Alice sends 2nd comment to the article with follow-up
        data = {
            "name": "Alice",
            "email": "alice@example.com",
            "followup": True,
            "reply_to": 1,
            "level": 1,
            "order": 1,
            "comment": "Yeah, great photos",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        self.assertTrue(self.mock_mailer.call_count == 2)
        alicekey = str(
            re.search(
                r"http://.+/confirm/(?P<key>[\S]+)/",
                self.mock_mailer.call_args[0][1],
            ).group("key")
        )
        confirm_comment_url(alicekey)  # confirm Alice's comment

        # Bob receives a follow-up notification
        self.assertTrue(self.mock_mailer.call_count == 3)
        self.bobs_mutekey = str(
            re.search(
                r"http://.+/mute/(?P<key>[\S]+)/",
                self.mock_mailer.call_args[0][1],
            ).group("key")
        )
        self.addCleanup(patcher.stop)

    def get_mute_followup_url(self, key):
        request = request_factory.get(
            reverse("comments-ink-mute", kwargs={"key": key}), follow=True
        )
        request.user = AnonymousUser()
        response = MuteCommentView.as_view()(request, key)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.find(b"Comment thread muted") > -1)
        return response

    def test_mute_followup_notifications(self):
        # Bob's receive a notification and click on the mute link to
        # avoid additional comment messages on the same article.
        self.get_mute_followup_url(self.bobs_mutekey)
        # Alice sends 3rd comment to the article with follow-up
        data = {
            "name": "Alice",
            "email": "alice@example.com",
            "followup": True,
            "reply_to": 2,
            "level": 1,
            "order": 1,
            "comment": "And look at this and that...",
            "next": reverse("comments-ink-sent"),
        }
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        # Alice confirms her comment...
        self.assertTrue(self.mock_mailer.call_count == 4)
        alicekey = str(
            re.search(
                r"http://.+/confirm/(?P<key>[\S]+)/",
                self.mock_mailer.call_args[0][1],
            ).group("key")
        )
        confirm_comment_url(alicekey)  # confirm Alice's comment.
        # Alice confirmed her comment, but this time Bob won't receive any
        # notification, neither do Alice being the sender.
        self.assertTrue(self.mock_mailer.call_count == 4)

    def test_mute_followup_notifications_with_wrong_key(self):
        # Bob's receive a notification and click on the mute link to
        # avoid additional comment messages on the same article.
        # But we use a wrong key (just remove a few bits from the tail).
        key = self.bobs_mutekey[:-2]
        request = request_factory.get(
            reverse("comments-ink-mute", kwargs={"key": key}), follow=True
        )
        request.user = AnonymousUser()
        response = MuteCommentView.as_view()(request, key)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.content.find(b"Bad Request") > -1)

    def test_muting_twice_raise_http_404(self):
        # Mute one time.
        self.get_mute_followup_url(self.bobs_mutekey)
        # Mute a second time.
        request = request_factory.get(
            reverse("comments-ink-mute", kwargs={"key": self.bobs_mutekey}),
            follow=True,
        )
        request.user = AnonymousUser()
        with self.assertRaises(Http404):
            MuteCommentView.as_view()(request, self.bobs_mutekey)


class HTMLDisabledMailTestCase(TestCase):
    def setUp(self):
        # Create an article and send a comment. Test method will chech headers
        # to see wheter messages has multiparts or not.
        patcher = patch("django_comments_ink.views.commenting.utils.send_mail")
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="September", slug="september", body="John's September"
        )
        self.form = django_comments.get_form()(self.article)

        # Bob sends 1st comment to the article with follow-up
        self.data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Nice September you had...",
            "next": reverse("comments-ink-sent"),
        }
        self.data.update(self.form.initial)

    @patch.multiple(
        "django_comments_ink.conf.settings", COMMENTS_INK_SEND_HTML_EMAIL=False
    )
    def test_mail_does_not_contain_html_part(self):
        with patch.multiple(
            "django_comments_ink.conf.settings",
            COMMENTS_INK_SEND_HTML_EMAIL=False,
        ):
            response = post_article_comment(self.data, self.article)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/comments/sent/?c="))
            self.assertTrue(self.mock_mailer.call_count == 1)
            self.assertTrue(self.mock_mailer.call_args[1]["html"] is None)

    def test_mail_does_contain_html_part(self):
        response = post_article_comment(self.data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comments/sent/?c="))
        self.assertTrue(self.mock_mailer.call_count == 1)
        self.assertTrue(self.mock_mailer.call_args[1]["html"] is not None)


# ---------------------------------------------------------------------
# Test module level `_*_tmpl` variables. Verify that they include
# the them (settings.COMMENTS_INK_THEME) in the path when that
# setting is provided.


def test_template_path_includes_theme(monkeypatch):
    monkeypatch.setattr(
        templates.settings, "COMMENTS_INK_THEME", "avatar_in_header"
    )
    monkeypatch.setattr(templates, "theme_dir", None)
    templates.check_theme()
    assert templates.theme_dir == "themes/avatar_in_header"
    assert templates.theme_dir_exists == True


def test_template_path_does_not_include_theme(monkeypatch):
    monkeypatch.setattr(templates.settings, "COMMENTS_INK_THEME", "")
    monkeypatch.setattr(templates, "theme_dir", None)
    templates.check_theme()
    assert templates.theme_dir == ""
    assert templates.theme_dir_exists == False


# ---------------------------------------------------------------------
# Test 'post' via accessing the exposed functionality, to
# later replace the implementation with class-based views.


def test_post_view_requires_method_to_be_POST(rf):
    # GET should not work.
    request = rf.get(reverse("comments-ink-post"))
    request._dont_enforce_csrf_checks = True
    response = PostCommentView.as_view()(request)
    assert response.status_code == 405

    # PUT should not work.
    request = rf.put(reverse("comments-ink-post"))
    request._dont_enforce_csrf_checks = True
    response = PostCommentView.as_view()(request)
    assert response.status_code == 405

    # PATCH should not work.
    request = rf.patch(reverse("comments-ink-post"))
    request._dont_enforce_csrf_checks = True
    response = PostCommentView.as_view()(request)
    assert response.status_code == 405


def test_XMLHttpRequest_post_view_handles_to_post_js(rf, monkeypatch):
    monkeypatch.setattr(
        PostCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: JsonResponse(
            {"post_js_called": True}, status=200
        ),
    )
    request = rf.post(
        reverse(
            "comments-ink-post",
        ),
        data={},
    )
    request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
    response = PostCommentView.as_view()(request)
    assert response.status_code == 200
    assert json.loads(response.content) == {"post_js_called": True}


# ---------------------------------------------------------------------
class MockedPostBadRequest(CommentPostBadRequest):
    def __init__(self, why):
        self.why = why
        super().__init__(why)


def prepare_comment_form_data(an_article):
    form = django_comments.get_form()(an_article)
    data = {
        "name": "Joe",
        "email": "joe@example.com",
        "followup": True,
        "reply_to": 0,
        "level": 1,
        "order": 1,
        "comment": "Es war einmal eine kleine...",
        "next": reverse("comments-ink-sent"),
    }
    data.update(form.initial)
    return data


def prepare_request_to_post_form(
    monkeypatch, rf, an_article, user=None, remove_fields=[], add_fields=[]
):
    monkeypatch.setattr(
        "django_comments_ink.views.commenting.CommentPostBadRequest",
        MockedPostBadRequest,
    )
    data = prepare_comment_form_data(an_article)

    # Remove fields listed in remove_fields.
    for field_name in remove_fields:
        data.pop(field_name)

    # Add fields listed in add_fields as {"name": <name>, "value": <value>}
    for field in add_fields:
        data[field["name"]] = field["value"]

    article_url = reverse(
        "article-detail",
        kwargs={
            "year": an_article.publish.year,
            "month": an_article.publish.month,
            "day": an_article.publish.day,
            "slug": an_article.slug,
        },
    )
    request = rf.post(article_url, data=data, follow=True)
    if user:
        request.user = user
    else:
        request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    return request


@pytest.mark.django_db
def test_post_comment_form_without_content_type(
    monkeypatch, rf, an_article, an_user
):
    request = prepare_request_to_post_form(
        monkeypatch,
        rf,
        an_article,
        user=an_user,
        remove_fields=["content_type"],
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    assert response.why == "Missing content_type or object_pk field."


@pytest.mark.django_db
def test_post_comment_form_without_object_pk(
    monkeypatch, rf, an_article, an_user
):
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user, remove_fields=["object_pk"]
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    assert response.why == "Missing content_type or object_pk field."


def mock_get_model(etr):
    def _mocked_function(*args, **kwargs):
        raise etr("Something went wrong")

    return _mocked_function


@pytest.mark.django_db
@pytest.mark.parametrize(
    "monkeypatch, rf, an_article, an_user, exc, message",
    [
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            LookupError,
            "Invalid content_type value",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            TypeError,
            "Invalid content_type value",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            AttributeError,
            "The given content-type",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            ObjectDoesNotExist,
            "No object matching content-type",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            ValueError,
            "Attempting to get content-type",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            ValidationError,
            "Attempting to get content-type",
        ),
    ],
    indirect=["monkeypatch", "rf", "an_article", "an_user"],
)
def test_post_comment_form_raises_an_error(
    monkeypatch, rf, an_article, an_user, exc, message
):
    monkeypatch.setattr(
        "django_comments_ink.views.commenting.apps.get_model",
        mock_get_model(exc),
    )
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    assert response.why.startswith(message)


# ---------------------------------------------------------------------


def get_form_mocked(has_errors=False):
    class MockedForm:
        def __init__(self, target, data=None):
            self.has_errors = has_errors
            self.target = target
            self.data = data

        def security_errors(self):
            return self.has_errors

    return MockedForm


@pytest.mark.django_db
def test_post_comment_form_with_security_errors(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        "django_comments_ink.views.commenting.get_form",
        lambda: get_form_mocked(has_errors=True),
    )
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    assert response.why.startswith("The comment form failed security ")


# ---------------------------------------------------------------------
# Check the preview templates in the following conditions:
#  1st: when the theme_dir is left blank.
#  2nd: when the theme_dir is been given in the settings.
#  3rd: when the form had errors (remove the 'comment' field and add it empty.)


@pytest.mark.django_db
def test_post_comment_form_in_preview_without_theme_dir(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        PostCommentView,
        "render_to_response",
        lambda self, ctx: self.get_template_names(),
    )
    request = prepare_request_to_post_form(
        monkeypatch,
        rf,
        an_article,
        user=an_user,
        add_fields=[
            {"name": "preview", "value": 1},
        ],
    )
    template_list = PostCommentView.as_view()(request)
    assert template_list == [
        "comments/tests/article/preview.html",
        "comments/tests/preview.html",
        "comments/preview.html",
    ]


@pytest.mark.django_db
def test_post_comment_form_in_preview_with_theme_dir(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        "django_comments_ink.views.commenting.theme_dir",
        "themes/feedback_in_header",
    )
    monkeypatch.setattr(
        "django_comments_ink.views.templates.theme_dir_exists", True
    )
    monkeypatch.setattr(
        PostCommentView, "template_list", themed_templates("preview")
    )

    monkeypatch.setattr(
        PostCommentView,
        "render_to_response",
        lambda self, ctx: self.get_template_names(),
    )
    request = prepare_request_to_post_form(
        monkeypatch,
        rf,
        an_article,
        user=an_user,
        add_fields=[
            {"name": "preview", "value": 1},
        ],
    )
    template_list = PostCommentView.as_view()(request)
    assert template_list == [
        "comments/themes/feedback_in_header/tests/article/preview.html",
        "comments/themes/feedback_in_header/tests/preview.html",
        "comments/themes/feedback_in_header/preview.html",
        "comments/tests/article/preview.html",
        "comments/tests/preview.html",
        "comments/preview.html",
    ]


@pytest.mark.django_db
def test_post_comment_form_with_an_empty_comment_field(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        PostCommentView,
        "render_to_response",
        lambda self, ctx: self.get_template_names(),
    )
    request = prepare_request_to_post_form(
        monkeypatch,
        rf,
        an_article,
        user=an_user,
        remove_fields=["comment"],
        add_fields=[
            {"name": "comment", "value": ""},
        ],
    )
    template_list = PostCommentView.as_view()(request)
    assert template_list == [
        "comments/tests/article/preview.html",
        "comments/tests/preview.html",
        "comments/preview.html",
    ]


# ----------------------------------------------------------------------
# Test that during the post of the comment form the
# signal 'comment_will_be_posted' has been called.
#  1. Check that when the signal returns False, a HTTP 400 is returned.
#  2. Check that when the signal returns True, the comment is posted.


@pytest.mark.django_db
def test_post_comment_form__comment_will_be_posted__returns_400(
    monkeypatch, rf, an_article, an_user
):
    def mock_send(*args, **kwargs):
        class Receiver:
            def __init__(self):
                self.__name__ = "mocked receiver"

        return [
            (Receiver(), False),
        ]

    monkeypatch.setattr(commenting.comment_will_be_posted, "send", mock_send)
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    assert response.why.startswith("comment_will_be_posted receiver")


@pytest.mark.django_db
def test_post_comment_form__comment_will_be_posted__returns_302(
    monkeypatch, rf, an_article, an_user
):
    def mock_send(*args, **kwargs):
        return [
            (None, True),
        ]

    monkeypatch.setattr(commenting.comment_will_be_posted, "send", mock_send)
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url == "/comments/sent/?c=1"


# ----------------------------------------------------------------------
# Test that 'comment_was_posted' signal has been sent.
# Follow the same approach as here above, but check
# that method 'send' is called.


@pytest.mark.django_db
def test_post_comment_form__comment_was_posted__signal_sent(
    monkeypatch, rf, an_article, an_user
):
    mock_send = Mock()
    monkeypatch.setattr(commenting.comment_was_posted, "send", mock_send)
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    PostCommentView.as_view()(request)
    assert mock_send.called


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_post_comment_form_has_cpage_qs_param(
    monkeypatch, rf, an_article, an_user
):
    request = prepare_request_to_post_form(
        monkeypatch,
        rf,
        an_article,
        user=an_user,
        add_fields=[{"name": "cpage", "value": 2}],
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url == "/comments/sent/?c=1&cpage=2"


# ---------------------------------------------------------------------
def prepare_js_request_to_post_form(
    rf, an_article, user=None, remove_fields=[], add_fields=[]
):
    data = prepare_comment_form_data(an_article)

    # Remove fields listed in remove_fields.
    for field_name in remove_fields:
        data.pop(field_name)

    # Add fields listed in add_fields as {"name": <name>, "value": <value>}
    for field in add_fields:
        data[field["name"]] = field["value"]

    article_url = reverse(
        "article-detail",
        kwargs={
            "year": an_article.publish.year,
            "month": an_article.publish.month,
            "day": an_article.publish.day,
            "slug": an_article.slug,
        },
    )
    request = rf.post(article_url, data=data, follow=True)
    if user != None:
        request.user = user
    else:
        request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
    return request


@pytest.mark.django_db
def test_post_js_comment_form_missing_name_and_email(rf, an_article, an_user):
    request = prepare_js_request_to_post_form(
        rf, an_article, user=an_user, remove_fields=["name", "email"]
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 201
    result = json.loads(response.content)
    assert result["html"].find("Your comment has been already published.") > -1
    comment = InkComment.objects.get(pk=1)
    assert comment.user == an_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "rf, an_article, an_user, remove_field",
    [
        ("rf", "an_article", "an_user", "content_type"),
        ("rf", "an_article", "an_user", "object_pk"),
    ],
    indirect=["rf", "an_article", "an_user"],
)
def test_post_js_comment_form_missing_content_type_or_object_pk(
    rf, an_article, an_user, remove_field
):
    request = prepare_js_request_to_post_form(
        rf, an_article, user=an_user, remove_fields=[remove_field]
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    result = json.loads(response.content)
    assert result["html"].find("Missing content_type or object_pk field.") > -1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "monkeypatch, rf, an_article, an_user, exc, message",
    [
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            LookupError,
            "Invalid content_type value",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            TypeError,
            "Invalid content_type value",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            AttributeError,
            "The given content-type",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            ObjectDoesNotExist,
            "No object matching content-type",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            ValueError,
            "Attempting to get content-type",
        ),
        (
            "monkeypatch",
            "rf",
            "an_article",
            "an_user",
            ValidationError,
            "Attempting to get content-type",
        ),
    ],
    indirect=["monkeypatch", "rf", "an_article", "an_user"],
)
def test_post_js_comment_form_returns_400(
    monkeypatch, rf, an_article, an_user, exc, message
):
    monkeypatch.setattr(commenting.apps, "get_model", mock_get_model(exc))
    request = prepare_js_request_to_post_form(rf, an_article, user=an_user)
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    result = json.loads(response.content)
    assert result["html"].find(message) > -1


@pytest.mark.django_db
def test_post_js_comment_form_with_security_errors(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        commenting, "get_form", lambda: get_form_mocked(has_errors=True)
    )
    request = prepare_js_request_to_post_form(rf, an_article, user=an_user)
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    result = json.loads(response.content)
    assert result["html"].find("The comment form failed security") > -1


# ---------------------------------------------------------------------
# Do a JS Post and check the preview templates in the following
# conditions:
#  1st: when the reply_to field is 0, and the theme_dir is left blank.
#  2nd: when the reply_to field is 1, and the theme_dir is left blank.
#  3nd: when the reply_to is 0 and theme_dir is given in the settings.
#  4th: when the reply_to is 1 and theme_dir is given in the settings.
#  5th: when the form had errors (remove the 'comment' field and add it empty.)


@pytest.mark.django_db
def test_post_js_comment_form_in_preview__no_reply_to__without_theme_dir(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        PostCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: tmpl_list,
    )
    request = prepare_js_request_to_post_form(
        rf,
        an_article,
        user=an_user,
        remove_fields=["reply_to"],
        add_fields=[
            {"name": "preview", "value": 1},
            {"name": "reply_to", "value": 0},  # Will use 'form_js.html'.
        ],
    )
    template_list = PostCommentView.as_view()(request)
    assert template_list == [
        "comments/tests/article/form_js.html",
        "comments/tests/form_js.html",
        "comments/form_js.html",
    ]


@pytest.mark.django_db
def test_post_js_comment_form_in_preview__with_reply_to__without_theme_dir(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        PostCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: tmpl_list,
    )
    request = prepare_js_request_to_post_form(
        rf,
        an_article,
        user=an_user,
        remove_fields=["reply_to"],
        add_fields=[
            {"name": "preview", "value": 1},
            {"name": "reply_to", "value": 1},  # Will use 'reply_form_js.html'.
        ],
    )
    template_list = PostCommentView.as_view()(request)
    assert template_list == [
        "comments/tests/article/reply_form_js.html",
        "comments/tests/reply_form_js.html",
        "comments/reply_form_js.html",
    ]


@pytest.mark.django_db
def test_post_js_comment_form_in_preview__no_reply_to__with_theme_dir(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        "django_comments_ink.views.commenting.theme_dir",
        "themes/feedback_in_header",
    )
    monkeypatch.setattr(
        "django_comments_ink.views.templates.theme_dir_exists", True
    )
    monkeypatch.setattr(
        PostCommentView, "template_form_js", themed_templates("form_js")
    )

    monkeypatch.setattr(
        PostCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: tmpl_list,
    )

    request = prepare_js_request_to_post_form(
        rf,
        an_article,
        user=an_user,
        remove_fields=["reply_to"],
        add_fields=[
            {"name": "preview", "value": 1},
            {"name": "reply_to", "value": 0},  # Will use 'form_js.html'.
        ],
    )
    template_list = PostCommentView.as_view()(request)
    assert template_list == [
        "comments/themes/feedback_in_header/tests/article/form_js.html",
        "comments/themes/feedback_in_header/tests/form_js.html",
        "comments/themes/feedback_in_header/form_js.html",
        "comments/tests/article/form_js.html",
        "comments/tests/form_js.html",
        "comments/form_js.html",
    ]


@pytest.mark.django_db
def test_post_js_comment_form_in_preview__with_reply_to__with_theme_dir(
    monkeypatch, rf, an_article, an_user
):
    monkeypatch.setattr(
        "django_comments_ink.views.commenting.theme_dir",
        "themes/feedback_in_header",
    )
    monkeypatch.setattr(
        "django_comments_ink.views.templates.theme_dir_exists", True
    )
    monkeypatch.setattr(
        PostCommentView,
        "template_reply_form_js",
        themed_templates("reply_form_js"),
    )

    monkeypatch.setattr(
        PostCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: tmpl_list,
    )
    request = prepare_js_request_to_post_form(
        rf,
        an_article,
        user=an_user,
        remove_fields=["reply_to"],
        add_fields=[
            {"name": "preview", "value": 1},
            {"name": "reply_to", "value": 1},  # Will use 'reply_form_js.html'.
        ],
    )
    template_list = PostCommentView.as_view()(request)
    assert template_list == [
        "comments/themes/feedback_in_header/tests/article/reply_form_js.html",
        "comments/themes/feedback_in_header/tests/reply_form_js.html",
        "comments/themes/feedback_in_header/reply_form_js.html",
        "comments/tests/article/reply_form_js.html",
        "comments/tests/reply_form_js.html",
        "comments/reply_form_js.html",
    ]


@pytest.mark.django_db
def test_post_js_comment_form_with_an_empty_comment_field(
    rf, an_article, an_user
):
    request = prepare_js_request_to_post_form(
        rf,
        an_article,
        user=an_user,
        remove_fields=["comment"],
        add_fields=[
            {"name": "comment", "value": ""},
        ],
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 200
    result = json.loads(response.content)
    assert result["field_focus"] == "comment"


# ---------------------------------------------------------------------
# Test that during the post_js of the comment form the signal
# 'comment_will_be_posted' has been called.
#  1. Check that when the signal returns False, a HTTP 400 is returned.
#  2. Check that wh nthe signal returns True, the comment is posted.


@pytest.mark.django_db
def test_post_js_comment_form__comment_will_be_posted__returns_400(
    monkeypatch, rf, an_article, an_user
):
    def mock_send(*args, **kwargs):
        class Receiver:
            def __init__(self):
                self.__name__ = "mocked receiver"

        return [
            (Receiver(), False),
        ]

    monkeypatch.setattr(commenting.comment_will_be_posted, "send", mock_send)
    request = prepare_js_request_to_post_form(rf, an_article, user=an_user)
    response = PostCommentView.as_view()(request)
    assert response.status_code == 400
    result = json.loads(response.content)
    assert result["html"].find("comment_will_be_posted receiver") > -1


@pytest.mark.django_db
def test_post_js_comment_form__comment_will_be_posted__returns_201(
    monkeypatch, rf, an_article, an_user
):
    def mock_send(*args, **kwargs):
        return [
            (None, True),
        ]

    monkeypatch.setattr(commenting.comment_will_be_posted, "send", mock_send)
    request = prepare_js_request_to_post_form(rf, an_article, user=an_user)
    response = PostCommentView.as_view()(request)
    assert response.status_code == 201
    result = json.loads(response.content)
    assert result["html"].find("Your comment has been already published.") > -1
    comment = InkComment.objects.get(pk=1)
    assert comment.user == an_user


@pytest.mark.django_db
def test_sent_js_returns_posted_js_tmpl(monkeypatch, rf, an_article):
    send_mail_mock = Mock()
    monkeypatch.setattr(commenting.utils, "send_mail", send_mail_mock)
    monkeypatch.setattr(
        PostCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: (tmpl_list, status),
    )
    request = prepare_js_request_to_post_form(rf, an_article)
    template_list, status = PostCommentView.as_view()(request)
    assert send_mail_mock.called
    assert status == 202
    assert template_list == [
        "comments/tests/article/posted_js.html",
        "comments/tests/posted_js.html",
        "comments/posted_js.html",
    ]


@pytest.mark.django_db
def test_sent_js_failing_to_decode_key_returns_400(monkeypatch, rf, an_article):
    def _raise_exception(*args, **kwargs):
        raise Exception("Something went wrong!")

    send_mail_mock = Mock()
    monkeypatch.setattr(commenting.signing, "loads", _raise_exception)
    monkeypatch.setattr(commenting.utils, "send_mail", send_mail_mock)
    request = prepare_js_request_to_post_form(rf, an_article)
    response = PostCommentView.as_view()(request)
    assert send_mail_mock.called
    result = json.loads(response.content)
    assert response.status_code == 400
    assert result["html"].find("Comment does not exist") > -1


@pytest.mark.django_db
def test_sent_js__returns_moderated_js_tmpl(
    monkeypatch, rf, an_article, an_user
):
    def mock_send(*args, **kwargs):
        comment = kwargs["comment"]
        comment.is_public = False
        comment.save()
        return [
            (None, True),
        ]

    monkeypatch.setattr(commenting.comment_will_be_posted, "send", mock_send)

    monkeypatch.setattr(
        PostCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: (tmpl_list, status),
    )

    request = prepare_js_request_to_post_form(rf, an_article, user=an_user)
    template_list, status = PostCommentView.as_view()(request)
    assert status == 201
    assert template_list == [
        "comments/tests/article/moderated_js.html",
        "comments/tests/moderated_js.html",
        "comments/moderated_js.html",
    ]
    comment = InkComment.objects.get(pk=1)
    assert comment.user == an_user
    assert comment.is_public == False


# ---------------------------------------------------------------------
# Test the redirect to 'sent'.


@pytest.mark.django_db
def test_sent_receives_non_existing_comment_pk(monkeypatch, rf):
    monkeypatch.setattr(
        commenting, "CommentPostBadRequest", MockedPostBadRequest
    )
    request = rf.get("/comments/sent/")
    response = commenting.sent(request)
    assert response.status_code == 400
    assert response.why == "Comment doesn't exist"


@pytest.mark.django_db
def test_redirect_to_sent__auth_comment__returns_comments_url(
    monkeypatch, rf, an_article, an_user
):
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url == "/comments/sent/?c=1"

    request = rf.get(response.url)
    request.user = an_user
    response = commenting.sent(request)
    assert response.status_code == 302
    comment = InkComment.objects.get(pk=1)
    assert response.url == comment.get_absolute_url()


@pytest.mark.django_db
def test_redirect_to_sent__not_auth_comment__returns_posted_tmpl(
    monkeypatch, rf, an_article
):
    monkeypatch.setattr(
        commenting.utils,
        "send_mail",
        lambda *args, **kwargs: Mock(*args, *kwargs),
    )
    request = prepare_request_to_post_form(monkeypatch, rf, an_article)
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url.startswith("/comments/sent/?c=")
    request = rf.get(response.url)
    response = commenting.sent(request)
    assert response.status_code == 200
    assert (
        response.content.decode("utf-8").find("Comment confirmation requested")
        > -1
    )


@pytest.mark.django_db
def test_redirect_to_sent__not_auth_comment__uses_posted_tmpl(
    monkeypatch, rf, an_article
):
    monkeypatch.setattr(
        PostCommentView,
        "render_to_response",
        lambda self, ctx: self.get_template_names(),
    )
    monkeypatch.setattr(commenting, "render", lambda x, tmpl_list, y: tmpl_list)
    request = prepare_request_to_post_form(monkeypatch, rf, an_article)
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url.startswith("/comments/sent/?c=")
    request = rf.get(response.url)
    template = commenting.sent(request)
    assert template == "comments/posted.html"


@pytest.mark.django_db
def test_redirect_to_sent__bad_key__returns_400(monkeypatch, rf, an_article):
    request = prepare_request_to_post_form(monkeypatch, rf, an_article)
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url.startswith("/comments/sent/?c=")
    request = rf.get(response.url[:-1])  # Force malformed key.
    response = commenting.sent(request)
    assert response.status_code == 400
    assert response.why == "Comment doesn't exist"


@pytest.mark.django_db
def test_redirect_to_sent__not_public_comment__comment_in_moderation(
    monkeypatch, rf, an_article, an_user
):
    def create_comment(tmp_comment):
        tmp_comment.pop("comments_page", None)
        comment = InkComment(**tmp_comment)
        comment.is_public = False  # To force rendering moderated_tmpl.
        comment.save()
        return comment

    monkeypatch.setattr(commenting, "create_comment", create_comment)
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url.startswith("/comments/sent/?c=")
    request = rf.get(response.url)
    response = commenting.sent(request)
    assert response.status_code == 200
    assert (
        response.content.decode("utf-8").find("Your comment is in moderation.")
        > -1
    )


@pytest.mark.django_db
def test_redirect_to_sent__not_public_comment__uses_moderated_tmpl(
    monkeypatch, rf, an_article, an_user
):
    def create_comment(tmp_comment):
        tmp_comment.pop("comments_page", None)
        comment = InkComment(**tmp_comment)
        comment.is_public = False  # To force rendering moderated_tmpl.
        comment.save()
        return comment

    monkeypatch.setattr(
        PostCommentView,
        "render_to_response",
        lambda self, ctx: self.get_template_names(),
    )
    monkeypatch.setattr(
        commenting.utils,
        "send_mail",
        lambda *args, **kwargs: Mock(*args, *kwargs),
    )
    monkeypatch.setattr(commenting, "create_comment", create_comment)
    monkeypatch.setattr(commenting, "render", lambda x, tmpl_list, y: tmpl_list)
    request = prepare_request_to_post_form(
        monkeypatch, rf, an_article, user=an_user
    )
    response = PostCommentView.as_view()(request)
    assert response.status_code == 302
    assert response.url.startswith("/comments/sent/?c=")
    request = rf.get(response.url)
    template_list = commenting.sent(request)
    assert template_list == [
        "comments/tests/article/moderated.html",
        "comments/tests/moderated.html",
        "comments/moderated.html",
    ]


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_GET_reply_without_input_allowed_raises(
    monkeypatch, rf, an_user, an_articles_comment
):
    def get_options(*args, **kwargs):
        return {
            "check_input_allowed": "django_comments_ink.tests.test_views.nope",
            "comment_flagging_enabled": False,
            "comment_votes_enabled": False,
            "comment_reactions_enabled": False,
            "object_reactions_enabled": False,
        }

    monkeypatch.setattr(commenting.utils, "get_app_model_options", get_options)

    request = rf.get(
        reverse("comments-ink-reply", args=(an_articles_comment.pk,))
    )
    request.user = an_user
    try:
        ReplyCommentView.as_view()(request, an_articles_comment.pk)
    except Exception as exc:
        assert type(exc) == Http404


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_GET_react_without_reactions_enabled_raises(
    monkeypatch, rf, an_user, an_articles_comment
):
    def raise_PermissionDenied(*args, **kwargs):
        raise PermissionDenied(detail="Mee", code=status.HTTP_403_FORBIDDEN)

    monkeypatch.setattr(base.utils, "check_option", raise_PermissionDenied)
    request = rf.get(
        reverse("comments-ink-react", args=(an_articles_comment.pk,))
    )
    request.user = an_user
    # request._dont_enforce_csrf_checks = True
    try:
        ReactToCommentView.as_view()(request, an_articles_comment.pk)
    except Exception as exc:
        assert exc.detail == ErrorDetail(string="Mee", code=403)


@pytest.mark.django_db
def test_GET_react_renders_react_tmpl(
    monkeypatch, rf, an_user, an_articles_comment
):
    def fake_check_option(*args, **kwargs):
        return True

    monkeypatch.setattr(base.utils, "check_option", fake_check_option)
    monkeypatch.setattr(
        ReactToCommentView,
        "render_to_response",
        lambda self, ctx: (self.get_template_names(), ctx),
    )
    request = rf.get(
        reverse("comments-ink-react", args=(an_articles_comment.pk,))
    )
    request.user = an_user
    template, context = ReactToCommentView.as_view()(
        request, an_articles_comment.pk
    )
    assert template == ["comments/react.html"]
    for key in keys_in_SingleCommentView_context:
        assert key in context
    for key in [
        "user_reactions",
        "next",
    ]:
        assert key in context


@pytest.mark.django_db
def test_POST_react(monkeypatch, rf, an_user, an_articles_comment):
    def fake_check_option(*args, **kwargs):
        return True

    monkeypatch.setattr(base.utils, "check_option", fake_check_option)
    monkeypatch.setattr(
        ReactToCommentDoneView,
        "render_to_response",
        lambda self, ctx: (self.get_template_names(), ctx),
    )
    request = rf.post(
        reverse("comments-ink-react", args=(an_articles_comment.pk,)),
        data={"reaction": "+"},
        follow=True,
    )
    request.user = an_user
    request._dont_enforce_csrf_checks = True
    response = ReactToCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    template, context = ReactToCommentDoneView.as_view()(request)
    assert template == ["comments/reacted.html"]
    assert context["comment"] == an_articles_comment
    for key in keys_in_SingleCommentView_context:
        assert key in context


@pytest.mark.django_db
def test_POST_react_two_users_add_same_reaction_2nd_user_withdraws_it(
    monkeypatch, rf, an_user, an_user_2, an_articles_comment
):
    # This function tests perform_react: two users add the same
    # reaction to the same comment, and then the second user withdraws the
    # reaction.

    def fake_check_option(*args, **kwargs):
        return True

    def get_cr_counter():
        return CommentReaction.objects.get(
            reaction="+", comment=an_articles_comment
        ).counter

    def prepare_request(user):
        request = rf.post(
            reverse("comments-ink-react", args=(an_articles_comment.pk,)),
            data={"reaction": "+"},
            follow=True,
        )
        request.user = user
        request._dont_enforce_csrf_checks = True
        return request

    monkeypatch.setattr(reacting.utils, "check_option", fake_check_option)

    # 1: an_user sends the "+" reaction to this comment.
    request = prepare_request(an_user)
    response = ReactToCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    response = ReactToCommentDoneView.as_view()(request)
    assert response.status_code == 200
    assert get_cr_counter() == 1

    # 2: an_user_2 sends the "+" reaction to this comment.
    request = prepare_request(an_user_2)
    response = ReactToCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    response = ReactToCommentDoneView.as_view()(request)
    assert response.status_code == 200
    assert get_cr_counter() == 2

    # 3: an_user_2 sends again the "+" reaction to this comment,
    # the effect is the withdrawal of the reaction.
    request = prepare_request(an_user_2)
    response = ReactToCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    response = ReactToCommentDoneView.as_view()(request)
    assert response.status_code == 200
    assert get_cr_counter() == 1

    # 4: an_user sends again the "+" reaction to this comment,
    # the effect is the deletion of the CommentReaction (as it's the last
    # author of the CommentReaction).
    request = prepare_request(an_user)
    response = ReactToCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    response = ReactToCommentDoneView.as_view()(request)
    assert response.status_code == 200
    with pytest.raises(CommentReaction.DoesNotExist):
        get_cr_counter()


@pytest.mark.django_db
def test_POST_react_js(monkeypatch, rf, an_user, an_articles_comment):
    def fake_check_option(*args, **kwargs):
        return True

    monkeypatch.setattr(reacting.utils, "check_option", fake_check_option)
    monkeypatch.setattr(
        ReactToCommentView,
        "json_response",
        lambda self, tmpl_list, context, status: (
            tmpl_list,
            context,
            status,
        ),
    )
    request = rf.post(
        reverse("comments-ink-react", args=(an_articles_comment.pk,)),
        data={"reaction": "+"},
        follow=True,
    )
    request.user = an_user
    request._dont_enforce_csrf_checks = True
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
    tmpl_list, context, status = ReactToCommentView.as_view()(
        request, an_articles_comment.pk
    )
    assert status == 201
    assert tmpl_list == [
        "comments/tests/article/comment_reactions.html",
        "comments/tests/comment_reactions.html",
        "comments/comment_reactions.html",
    ]
    assert context["comment"] == an_articles_comment
    for key in keys_in_SingleCommentView_context:
        assert key in context


@pytest.mark.django_db
def test_GET_react_with_an_existing_comments_reaction(
    monkeypatch, rf, an_user, an_articles_comment, a_comments_reaction
):
    # fixture a_comments_reaction is needed in the signature of the test,
    # so that it is called and creates a_comments_reaction. When we then
    # request GET the react view we will get that reaction with the 'active'
    # css class.

    def fake_check_option(*args, **kwargs):
        return True

    monkeypatch.setattr(base.utils, "check_option", fake_check_option)
    request = rf.get(
        reverse("comments-ink-react", args=(an_articles_comment.pk,)),
    )
    request.user = an_user
    response = ReactToCommentView.as_view()(request, an_articles_comment.pk)
    response.render()
    assert response.status_code == 200
    html = response.content.replace(b"  ", b" ").replace(b"\n", b"")
    re_str = (  # This regexp matches the class="secondary active" in HTML.
        rb'<button\s+type="submit"\s+name="reaction"\s+value="\+"'
        rb'\s+class="(?P<classes>[a-z\s]+)"\s*>'
    )
    css_classes = re.search(re_str, html).group("classes")
    assert css_classes.find(b"active") > -1


@pytest.mark.django_db
def test_react_done_raises_404_if_no_param_c_or_comment_does_not_exist(
    rf, an_user
):
    request = rf.get(reverse("comments-ink-react-done"))
    request.user = an_user
    with pytest.raises(Http404):
        ReactToCommentDoneView.as_view()(request)

    request = rf.get(reverse("comments-ink-react-done") + "?c=1")
    request.user = an_user
    with pytest.raises(Http404):
        ReactToCommentDoneView.as_view()(request)


# ---------------------------------------------------------------------
# Test view's get_inkcomment_url.


@pytest.mark.django_db
def test_get_inkcomment_url_without_page(rf, an_article, an_articles_comment):
    args = (
        an_articles_comment.content_type.pk,
        int(an_articles_comment.object_pk),
        an_articles_comment.pk,
    )
    request = rf.get(reverse("comments-url-redirect", args=args))
    response = CommentUrlView.as_view()(request, *args)
    assert response.status_code == 302
    assert response.url.endswith(an_article.get_absolute_url())


@pytest.mark.django_db
def test_get_inkcomment_url_with_bad_page(rf, an_articles_comment):
    args = (
        an_articles_comment.content_type.pk,
        int(an_articles_comment.object_pk),
        an_articles_comment.pk,
    )
    request = rf.get(
        reverse("comments-url-redirect", args=args), {"cpage": "bad"}
    )
    with pytest.raises(Http404):
        CommentUrlView.as_view()(request, *args)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "rf, an_article, an_articles_comment, cpage",
    [
        ("rf", "an_article", "an_articles_comment", "last"),
        ("rf", "an_article", "an_articles_comment", "2"),
    ],
    indirect=["rf", "an_article", "an_articles_comment"],
)
def test_get_inkcomment_url_with_page(
    rf, an_article, an_articles_comment, cpage
):
    args = (
        an_articles_comment.content_type.pk,
        int(an_articles_comment.object_pk),
        an_articles_comment.pk,
    )
    request = rf.get(
        reverse("comments-url-redirect", args=args), {"cpage": cpage}
    )
    response = CommentUrlView.as_view()(request, *args)
    assert response.status_code == 302
    assert response.url.endswith(
        an_article.get_absolute_url() + f"?cpage={cpage}"
    )


@pytest.mark.django_db
def test_get_inkcomment_url_with_fold(rf, an_article, an_articles_comment):
    args = (
        an_articles_comment.content_type.pk,
        int(an_articles_comment.object_pk),
        an_articles_comment.pk,
    )
    request = rf.get(
        reverse("comments-url-redirect", args=args), {"cfold": "12,37"}
    )
    response = CommentUrlView.as_view()(request, *args)
    assert response.status_code == 302
    assert response.url.endswith(
        an_article.get_absolute_url() + f"?cfold=12,37"
    )


@pytest.mark.django_db
def test_get_inkcomment_url_with_fold_raises_Http404(rf, an_articles_comment):
    args = (
        an_articles_comment.content_type.pk,
        int(an_articles_comment.object_pk),
        an_articles_comment.pk,
    )
    request = rf.get(
        reverse("comments-url-redirect", args=args), {"cfold": "12,A"}
    )
    with pytest.raises(Http404):
        CommentUrlView.as_view()(request, *args)


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_POST_react_to_object_redirects_to_login(rf, an_article):
    ctype = ContentType.objects.get_for_model(an_article)
    react_url = reverse(
        "comments-ink-react-to-object", args=(ctype.id, an_article.id)
    )
    request = rf.post(
        react_url,
        data={
            "reaction": "+",
        },
        follow=True,
    )
    request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    response = ReactToObjectView.as_view()(request, ctype.id, an_article.id)
    assert response.url == settings.LOGIN_URL + "?next=" + react_url
    assert response.status_code == 302


@pytest.mark.django_db
def test_POST_react_to_an_article_is_not_enabled(rf, an_article, an_user):
    ctype = ContentType.objects.get_for_model(an_article)
    react_url = reverse(
        "comments-ink-react-to-object", args=(ctype.id, an_article.id)
    )
    request = rf.post(
        react_url,
        data={
            "reaction": "+",
        },
        follow=True,
    )
    request.user = an_user
    request._dont_enforce_csrf_checks = True
    with pytest.raises(PermissionDenied):
        ReactToObjectView.as_view()(request, ctype.id, an_article.id)


@pytest.mark.django_db
def test_POST_react_to_a_diary_entry_is_enabled(rf, a_diary_entry, an_user):
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    site = Site.objects.get(pk=1)
    react_url = reverse(
        "comments-ink-react-to-object", args=(ctype.id, a_diary_entry.id)
    )
    request = rf.post(
        react_url,
        data={"reaction": "+", "next": a_diary_entry.get_absolute_url()},
        follow=True,
    )

    # Assert no reaction has been posted to a_diary_entry yet.
    num_obj_reactions = ObjectReaction.objects.filter(
        content_type=ctype, object_pk=a_diary_entry.id, site=site
    ).count()
    assert num_obj_reactions == 0

    request.user = an_user
    request._dont_enforce_csrf_checks = True
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == a_diary_entry.get_absolute_url()

    # Assert the reaction has been added.
    num_obj_reactions = ObjectReaction.objects.filter(
        content_type=ctype, object_pk=a_diary_entry.id, site=site
    ).count()
    assert num_obj_reactions == 1


@pytest.mark.django_db
def test_POST_react_twice_to_a_diary_entry_with_same_reaction(
    rf, a_diary_entry, an_user
):
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    site = Site.objects.get(pk=1)
    react_url = reverse(
        "comments-ink-react-to-object", args=(ctype.id, a_diary_entry.id)
    )
    request = rf.post(
        react_url,
        data={"reaction": "+", "next": a_diary_entry.get_absolute_url()},
        follow=True,
    )

    # First reaction, will add the reaction.
    request.user = an_user
    request._dont_enforce_csrf_checks = True
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == a_diary_entry.get_absolute_url()

    # Second same reaction, will withdraw the reaction.
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == a_diary_entry.get_absolute_url()

    # Assert the reaction has been added.
    assert (
        ObjectReaction.objects.filter(
            reaction="+",
            content_type=ctype,
            object_pk=a_diary_entry.id,
            site=site,
        ).count()
        == 0
    )


@pytest.mark.django_db
def test_POST_react_three_times_to_a_diary_entry_with_same_reaction(
    rf, a_diary_entry, an_user, an_user_2
):
    # First send the reaction with an_user, then with an_user_2.
    # Then withdraw the reaction of an_user_2.
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    site = Site.objects.get(pk=1)
    react_url = reverse(
        "comments-ink-react-to-object", args=(ctype.id, a_diary_entry.id)
    )

    def get_request(user):
        request = rf.post(
            react_url,
            data={"reaction": "+", "next": a_diary_entry.get_absolute_url()},
            follow=True,
        )
        request._dont_enforce_csrf_checks = True
        request.user = user
        return request

    # First reaction, will add the reaction.
    request = get_request(an_user)
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == a_diary_entry.get_absolute_url()

    # Second same reaction, with an_user_2.
    request = get_request(an_user_2)
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == a_diary_entry.get_absolute_url()

    # Third, send same reaction of an_user_2, will withdraw the reaction.
    request = get_request(an_user_2)
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == a_diary_entry.get_absolute_url()

    # Assert the reaction has been added.
    assert (
        ObjectReaction.objects.filter(
            reaction="+",
            content_type=ctype,
            object_pk=a_diary_entry.id,
            site=site,
        ).count()
        == 1
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "rf, a_diary_entry, an_user, post_extra_params, expected_url_qstring",
    [
        ("rf", "a_diary_entry", "an_user", {"cpage": 2}, "?cpage=2"),
        ("rf", "a_diary_entry", "an_user", {"cfold": "1,3"}, "?cfold=1,3"),
        (
            "rf",
            "a_diary_entry",
            "an_user",
            {"cpage": 3, "cfold": "12,46"},
            "?cpage=3&cfold=12,46",
        ),
    ],
    indirect=["rf", "a_diary_entry", "an_user"],
)
def test_POST_react_to_object_with_cpage(
    rf, a_diary_entry, an_user, post_extra_params, expected_url_qstring
):
    a_diary_entry_url = a_diary_entry.get_absolute_url()
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    react_url = reverse(
        "comments-ink-react-to-object", args=(ctype.id, a_diary_entry.id)
    )
    data = {"reaction": "+", "next": a_diary_entry_url}
    data.update(post_extra_params)
    request = rf.post(react_url, data=data, follow=True)

    request.user = an_user
    request._dont_enforce_csrf_checks = True
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == (
        a_diary_entry_url + "?" + urlencode(post_extra_params)
    )


@pytest.mark.django_db
def test_POST_react_to_a_diary_entry_with_anchor(rf, a_diary_entry, an_user):
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    react_url = reverse(
        "comments-ink-react-to-object", args=(ctype.id, a_diary_entry.id)
    )
    request = rf.post(
        react_url,
        data={
            "reaction": "+",
            "next": a_diary_entry.get_absolute_url() + "#reactions",
        },
        follow=True,
    )

    request.user = an_user
    request._dont_enforce_csrf_checks = True
    response = ReactToObjectView.as_view()(request, ctype.id, a_diary_entry.id)
    assert response.url == a_diary_entry.get_absolute_url() + "#reactions"


@pytest.mark.django_db
def test_POST_react_to_non_existing_content_type(rf, an_user):
    react_url = reverse("comments-ink-react-to-object", args=(234, 1))
    request = rf.post(
        react_url,
        data={
            "reaction": "+",
        },
        follow=True,
    )
    request.user = an_user
    request._dont_enforce_csrf_checks = True
    with pytest.raises(Http404):
        ReactToObjectView.as_view()(request, 234, 1)


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_list_reacted_raises_Http404(
    rf, an_articles_comment, a_comments_reaction
):
    args = (an_articles_comment.pk, a_comments_reaction.reaction)
    request = rf.get(reverse("comments-ink-list-reacted", args=args))
    try:
        ReactedToCommentUserListView.as_view()(
            request, an_articles_comment.pk, a_comments_reaction.reaction
        )
    except Exception as exc:
        assert type(exc) == Http404


@pytest.mark.django_db
def test_list_reacted_does_work(
    monkeypatch, rf, an_articles_comment, a_comments_reaction_2
):
    monkeypatch.setattr(
        reacting.settings, "COMMENTS_INK_MAX_USERS_IN_TOOLTIP", 1
    )
    monkeypatch.setattr(
        ReactedToCommentUserListView,
        "render_to_response",
        lambda self, ctx: (self.get_template_names(), ctx),
    )
    args = (an_articles_comment.pk, a_comments_reaction_2.reaction)
    request = rf.get(reverse("comments-ink-list-reacted", args=args))
    tmpl_list, context = ReactedToCommentUserListView.as_view()(
        request, an_articles_comment.pk, a_comments_reaction_2.reaction
    )
    assert tmpl_list == [
        "comments/tests/article/users_reacted_to_comment.html",
        "comments/tests/users_reacted_to_comment.html",
        "comments/users_reacted_to_comment.html",
    ]
    assert "comment" in context
    assert context["comment"] == an_articles_comment
    assert "reaction" in context
    assert context["reaction"] == "+"
    assert "page_obj" in context


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_list_reacted_to_object_raises_one_Http404(
    rf, a_diary_entry, an_object_reaction
):
    args = (9999, a_diary_entry.pk, an_object_reaction.reaction)
    request = rf.get(reverse("comments-ink-list-reacted-to-object", args=args))
    try:
        ReactedToObjectUserListView.as_view()(
            request, 9999, a_diary_entry.pk, an_object_reaction.reaction
        )
    except Exception as exc:
        assert type(exc) == Http404


@pytest.mark.django_db
def test_list_reacted_to_object_raises_another_Http404(
    rf, a_diary_entry, an_object_reaction
):
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    args = (ctype.pk, a_diary_entry.pk, an_object_reaction.reaction)
    request = rf.get(reverse("comments-ink-list-reacted-to-object", args=args))
    try:
        ReactedToObjectUserListView.as_view()(
            request, ctype.pk, a_diary_entry.pk, an_object_reaction.reaction
        )
    except Exception as exc:
        assert type(exc) == Http404


@pytest.mark.django_db
def test_list_reacted_to_object_does_work(
    monkeypatch, rf, a_diary_entry, an_object_reaction_2
):
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    monkeypatch.setattr(
        reacting.settings, "COMMENTS_INK_MAX_USERS_IN_TOOLTIP", 1
    )
    monkeypatch.setattr(
        ReactedToObjectUserListView,
        "render_to_response",
        lambda self, ctx: (self.get_template_names(), ctx),
    )
    args = (ctype.pk, a_diary_entry.pk, an_object_reaction_2.reaction)
    request = rf.get(reverse("comments-ink-list-reacted-to-object", args=args))
    tmpl_list, context = ReactedToObjectUserListView.as_view()(
        request, ctype.pk, a_diary_entry.pk, an_object_reaction_2.reaction
    )
    assert tmpl_list == [
        "comments/tests/diary/users_reacted_to_object.html",
        "comments/tests/users_reacted_to_object.html",
        "comments/users_reacted_to_object.html",
    ]
    assert "object" in context
    assert context["object"] == a_diary_entry
    assert "reaction" in context
    assert context["reaction"] == "+"
    assert "page_obj" in context


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_GET_vote_without_comment_votes_enabled_raises(
    monkeypatch, rf, an_user, an_articles_comment
):
    def raise_PermissionDenied(*args, **kwargs):
        raise PermissionDenied(detail="Mee", code=status.HTTP_403_FORBIDDEN)

    monkeypatch.setattr(base.utils, "check_option", raise_PermissionDenied)
    request = rf.get(
        reverse("comments-ink-vote", args=(an_articles_comment.pk,))
    )
    request.user = an_user
    # request._dont_enforce_csrf_checks = True
    try:
        VoteCommentView.as_view()(request, an_articles_comment.pk)
    except Exception as exc:
        assert exc.detail == ErrorDetail(string="Mee", code=403)


@pytest.mark.django_db
def test_GET_vote_without_input_allowed_raises(
    monkeypatch, rf, an_user, an_articles_comment
):
    def get_options(*args, **kwargs):
        return {
            "check_input_allowed": "django_comments_ink.tests.test_views.nope",
            "comment_flagging_enabled": False,
            "comment_votes_enabled": True,
            "comment_reactions_enabled": False,
            "object_reactions_enabled": False,
        }

    monkeypatch.setattr(base.utils, "check_option", lambda *args, **kwds: True)
    monkeypatch.setattr(base.utils, "get_app_model_options", get_options)

    request = rf.get(
        reverse("comments-ink-vote", args=(an_articles_comment.pk,))
    )
    request.user = an_user
    try:
        VoteCommentView.as_view()(request, an_articles_comment.pk)
    except Exception as exc:
        assert type(exc) == Http404


@pytest.mark.django_db
def test_GET_vote_renders_vote_tmpl(
    monkeypatch, rf, an_user, an_articles_comment
):
    def fake_check_option(*args, **kwargs):
        return True

    monkeypatch.setattr(base.utils, "check_option", fake_check_option)
    monkeypatch.setattr(
        VoteCommentView,
        "render_to_response",
        lambda self, ctx: (self.get_template_names(), ctx),
    )
    request = rf.get(
        reverse("comments-ink-vote", args=(an_articles_comment.pk,))
    )
    request.user = an_user
    template, context = VoteCommentView.as_view()(
        request, an_articles_comment.pk
    )
    assert template == ["comments/vote.html"]
    for key in keys_in_SingleCommentView_context:
        assert key in context
    for key in [
        "user_vote",
        "next",
    ]:
        assert key in context


@pytest.mark.django_db
def test_POST_vote(monkeypatch, rf, an_user, an_articles_comment):
    def fake_check_option(*args, **kwargs):
        return True

    monkeypatch.setattr(base.utils, "check_option", fake_check_option)
    monkeypatch.setattr(
        VoteCommentDoneView,
        "render_to_response",
        lambda self, ctx: (self.get_template_names(), ctx),
    )
    request = rf.post(
        reverse("comments-ink-vote", args=(an_articles_comment.pk,)),
        data={"vote": "+"},
        follow=True,
    )
    request.user = an_user
    request._dont_enforce_csrf_checks = True
    response = VoteCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    template, context = VoteCommentDoneView.as_view()(request)
    assert template == ["comments/voted.html"]
    assert context["comment"] == an_articles_comment
    for key in keys_in_SingleCommentView_context:
        assert key in context


@pytest.mark.django_db
def test_POST_vote_user_votes_the_same_twice(
    monkeypatch, rf, an_user, an_articles_comment
):
    def fake_check_option(*args, **kwargs):
        return True

    def get_thread_score():
        return CommentThread.objects.get(id=an_articles_comment.pk).score

    def prepare_request(user):
        request = rf.post(
            reverse("comments-ink-vote", args=(an_articles_comment.pk,)),
            data={"vote": "+"},
            follow=True,
        )
        request.user = user
        request._dont_enforce_csrf_checks = True
        return request

    monkeypatch.setattr(base.utils, "check_option", fake_check_option)

    # 1: The an_user sends the "+" vote to this comment.
    request = prepare_request(an_user)
    response = VoteCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    response = VoteCommentDoneView.as_view()(request)
    assert response.status_code == 200
    assert get_thread_score() == 1

    # 2: The same an_user sends the "+" vote to this
    #    comment, what shall withdraw the vote.
    request = prepare_request(an_user)
    response = VoteCommentView.as_view()(request, an_articles_comment.pk)
    assert response.status_code == 302
    request = rf.get(response.url)
    request.user = an_user
    response = VoteCommentDoneView.as_view()(request)
    assert response.status_code == 200
    assert get_thread_score() == 0


@pytest.mark.django_db
def test_POST_vote_js(monkeypatch, rf, an_user, an_articles_comment):
    def fake_check_option(*args, **kwargs):
        return True

    monkeypatch.setattr(base.utils, "check_option", fake_check_option)
    monkeypatch.setattr(
        VoteCommentView,
        "json_response",
        lambda self, tmpl_list, ctx, status: (
            tmpl_list,
            ctx,
            status,
        ),
    )
    request = rf.post(
        reverse("comments-ink-vote", args=(an_articles_comment.pk,)),
        data={"vote": "+"},
        follow=True,
    )
    request.user = an_user
    request._dont_enforce_csrf_checks = True
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
    tmpl_list, context, status = VoteCommentView.as_view()(
        request, an_articles_comment.pk
    )
    assert status == 201
    assert tmpl_list == [
        "comments/tests/article/comment_votes.html",
        "comments/tests/comment_votes.html",
        "comments/comment_votes.html",
    ]
    assert "comment" in context
    assert context["comment"] == an_articles_comment
    for key in keys_in_SingleCommentView_context:
        assert key in context
