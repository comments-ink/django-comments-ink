from datetime import datetime
import pytest

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase

import django_comments

from django_comments_ink import (
    caching,
    get_comment_reactions_enum,
    get_model,
    get_object_reactions_enum,
)
from django_comments_ink.conf import settings
from django_comments_ink.models import CommentReaction, ObjectReaction

from django_comments_ink.tests.models import Article, Diary
from django_comments_ink.tests.test_views import (
    post_article_comment,
    post_diary_comment,
)
from django_comments_ink.tests.utils import post_flag, send_reaction


request_factory = RequestFactory()
comments_model = django_comments.get_model()


class HTTPMethodsNotAllowedTests(TestCase):
    def setUp(self):
        diary_entry = Diary.objects.create(
            body="What I did in October...",
            allow_comments=True,
            publish=datetime.now(),
        )
        form = django_comments.get_form()(diary_entry)
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmail eine kleine...",
        }
        data.update(form.initial)
        post_diary_comment(data, diary_entry, auth_user=self.user)
        self.comment = get_model().objects.first()
        self.renum = get_comment_reactions_enum()

    def test_send_delete_method_raises_405_method_not_allowed(self):
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        response = send_reaction("delete", data, auth_user=self.user)
        self.assertEqual(response.status_code, 405)

    def test_send_get_method_raises_405_method_not_allowed(self):
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        response = send_reaction("get", data, auth_user=self.user)
        self.assertEqual(response.status_code, 405)

    def test_send_put_method_raises_405_method_not_allowed(self):
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        response = send_reaction("put", data, auth_user=self.user)
        self.assertEqual(response.status_code, 405)

    def test_send_update_method_raises_405_method_not_allowed(self):
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        response = send_reaction("put", data, auth_user=self.user)
        self.assertEqual(response.status_code, 405)


class AllowedCommentReactionTests(TestCase):
    """Scenario to test like and dislike reactions on tests.diary model."""

    def setUp(self):
        diary_entry = Diary.objects.create(
            body="What I did in October...",
            allow_comments=True,
            publish=datetime.now(),
        )
        form = django_comments.get_form()(diary_entry)
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmail eine kleine...",
        }
        data.update(form.initial)
        post_diary_comment(data, diary_entry, auth_user=self.user)
        self.comment = get_model().objects.first()
        self.renum = get_comment_reactions_enum()

    def test_post_reaction_as_anonymous_user_results_in_403(self):
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        anonymous_user = AnonymousUser()
        response = send_reaction("post", data, auth_user=anonymous_user)
        self.assertEqual(response.status_code, 403)

    def test_create_LIKE_IT_reaction(self):
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        response = send_reaction("post", data, auth_user=self.user)
        # Verify the content of the response.data attribute.
        self.assertTrue("counter" in response.data)  # Total # of reactions.
        self.assertTrue("list" in response.data)  # The list of reactions.
        item = response.data["list"][0]
        self.assertEqual(item["value"], "+")
        self.assertEqual(item["authors"][0], "bob")  # 1st item of authors.
        self.assertEqual(item["counter"], 1)  # Count of LIKE_IT reactions.
        self.assertEqual(item["label"], "+1")
        self.assertEqual(item["icon"], "#128077")
        # Verify the status of the response.
        self.assertEqual(response.status_code, 201)

    def test_sending_same_reaction_twice_cancels_it(self):
        # The first like-it reaction creates the reaction.
        self.test_create_LIKE_IT_reaction()
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        # Check that the counter for this reaction is 1.
        creaction = CommentReaction.objects.get(**data)
        self.assertEqual(creaction.counter, 1)
        # The second like-it removes it.
        response = send_reaction("post", data, auth_user=self.user)
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(CommentReaction.DoesNotExist):
            creaction = CommentReaction.objects.get(**data)

    def test_create_DISLIKE_IT_reaction(self):
        data = {"comment": self.comment.id, "reaction": self.renum.DISLIKE_IT}
        response = send_reaction("post", data, auth_user=self.user)
        self.assertEqual(response.status_code, 201)

    def test_create_both_likeit_and_dislikeit_reactions(self):
        # Like and dislike reactions can be sent from the same user for
        # the same comment. Because anything can be liked and disliked at
        # the same time. Embrace diversity!
        self.test_create_LIKE_IT_reaction()
        self.test_create_DISLIKE_IT_reaction()
        comment_reactions = CommentReaction.objects.filter(authors=self.user)
        self.assertEqual(len(comment_reactions), 2)
        crec1, crec2 = comment_reactions
        self.assertEqual(crec1.comment, self.comment)
        self.assertEqual(crec1.reaction, self.renum.LIKE_IT)
        self.assertEqual(crec2.comment, self.comment)
        self.assertEqual(crec2.reaction, self.renum.DISLIKE_IT)

    def test_create_LIKE_IT_reaction_from_different_user(self):
        # First I send the LIKE_IT reaction from above, to create the
        # CommentReaction and have the counter already to 1.
        self.test_create_LIKE_IT_reaction()
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        comment_reaction = CommentReaction.objects.get(**data)
        self.assertEqual(comment_reaction.counter, 1)

        alice = User.objects.create_user("alice", "alice@tal.net", "pwd")
        response = send_reaction("post", data, auth_user=alice)
        self.assertEqual(response.status_code, 201)

        comment_reaction = CommentReaction.objects.get(**data)
        self.assertEqual(comment_reaction.counter, 2)

    def test_create_two_LIKE_IT_reaction_and_remove_one(self):
        self.test_create_LIKE_IT_reaction()
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        cm_rct_1 = CommentReaction.objects.get(**data)
        self.assertEqual(cm_rct_1.counter, 1)
        alice = User.objects.create_user("alice", "alice@tal.net", "pwd")
        response = send_reaction("post", data, auth_user=alice)
        self.assertEqual(response.status_code, 201)
        cm_rct_2 = CommentReaction.objects.get(**data)
        self.assertEqual(cm_rct_2.counter, 2)
        response = send_reaction("post", data, auth_user=self.user)
        self.assertEqual(response.status_code, 200)
        cm_rct_3 = CommentReaction.objects.get(**data)
        self.assertEqual(cm_rct_3.counter, 1)
        self.assertTrue(cm_rct_1.pk == cm_rct_2.pk == cm_rct_3.pk)


class DisallowedCommentReactionTests(TestCase):
    """Scenario to test posting reactions in a disallowed scenario."""

    def setUp(self):
        article_entry = Article.objects.create(
            title="This is the title of the article",
            slug="title-article",
            body="This is the body of the article, blah blah blah...",
            allow_comments=True,
            publish=datetime.now(),
        )
        form = django_comments.get_form()(article_entry)
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmail eine kleine...",
        }
        data.update(form.initial)
        post_article_comment(data, article_entry, auth_user=self.user)
        self.comment = get_model().objects.first()
        self.renum = get_comment_reactions_enum()

    def test_post_reaction_as_anonymous_user_results_in_403(self):
        # This test is also in the class above: AllowedCommentReactionTests.
        # And it is exactly the same as in both cases, whether the
        # 'comment_reactions_enabled' flag is True or False, the
        # authentication is checked before hand.
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        anonymous_user = AnonymousUser()
        response = send_reaction("post", data, auth_user=anonymous_user)
        self.assertEqual(response.status_code, 403)

    def test_create_LIKE_IT_reaction(self):
        # This test is also in the class above: AllowedCommentReactionTests.
        # As 'comment_reactions_enabled' is False for model 'tests.article',
        # posting a reaction to a comment posted to a 'tests.article' results
        # in a HTTP 403 (No permission).
        data = {"comment": self.comment.id, "reaction": self.renum.LIKE_IT}
        response = send_reaction("post", data, auth_user=self.user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CommentReaction.objects.filter(**data).count(), 0)

    def test_create_DISLIKE_IT_reaction(self):
        # This test is also in the class above: AllowedCommentReactionTests.
        # As 'comment_reactions_enabled' is False for model 'tests.article',
        # posting a reaction to a comment posted to a 'tests.article' results
        # in a HTTP 403 (No permission).
        data = {"comment": self.comment.id, "reaction": self.renum.DISLIKE_IT}
        response = send_reaction("post", data, auth_user=self.user)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CommentReaction.objects.filter(**data).count(), 0)


# This class tests flagging comments posted to a diary entry.
# The model 'tests.diary' has the 'comment_flagging_enabled' = True in
# tests.settings, so flagging is allowed.
class AllowedCreateReportFlagTests(TestCase):
    def setUp(self):
        diary_entry = Diary.objects.create(
            body="What I did in October...",
            allow_comments=True,
            publish=datetime.now(),
        )
        form = django_comments.get_form()(diary_entry)
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        data = {
            "name": "Bob",
            "email": "bob@example.com",
            "followup": True,
            "reply_to": 0,
            "level": 1,
            "order": 1,
            "comment": "Es war einmail eine kleine...",
        }
        data.update(form.initial)
        post_diary_comment(data, diary_entry, auth_user=self.user)
        self.comment = get_model().objects.first()

    def test_flag_as_anonymous_user_results_in_403(self):
        data = {"comment": self.comment.id, "flag": "report"}
        anonymous_user = AnonymousUser()
        response = post_flag(data, auth_user=anonymous_user)
        self.assertEqual(response.status_code, 403)

    def test_flag_as_logged_in_user(self):
        data = {"comment": self.comment.id, "flag": "report"}
        response = post_flag(data, auth_user=self.user)
        self.assertEqual(response.status_code, 201)


# ---------------------------------------------------------------------
# Test ObjectReaction class.


@pytest.mark.django_db
def test_create_object_reaction_for_an_article(an_article):
    obj_reactions_enum = get_object_reactions_enum()
    ct = ContentType.objects.get_for_model(an_article)
    site = Site.objects.get(pk=1)
    object_reaction = ObjectReaction.objects.create(
        reaction=obj_reactions_enum.LIKE_IT,
        content_type=ct,
        object_pk=an_article.id,
        site=site,
    )
    assert object_reaction.counter == 0
    assert object_reaction.authors.count() == 0


@pytest.mark.django_db
def test_object_reaction_is_deleted_from_cache(an_user, an_article):
    obj_reactions_enum = get_object_reactions_enum()
    ct = ContentType.objects.get_for_model(an_article)
    site = Site.objects.get(pk=1)
    object_reaction = ObjectReaction.objects.create(
        reaction=obj_reactions_enum.LIKE_IT,
        content_type=ct,
        object_pk=an_article.id,
        site=site,
    )
    assert object_reaction.counter == 0
    assert object_reaction.authors.count() == 0

    # Create key and put it in the cache.
    dci_cache = caching.get_cache()
    key = settings.COMMENTS_INK_CACHE_KEYS["object_reactions"].format(
        ctype_pk=ct.id, object_pk=an_article.id, site_id=site.id
    )
    dci_cache.set(key, "nothing-in-particular")
    assert dci_cache.get(key) != None

    # Add user and increment counter.
    object_reaction.authors.add(an_user)
    object_reaction.counter += 1
    object_reaction.save()  # It deletes the key on save.
    assert dci_cache.get(key) == None
