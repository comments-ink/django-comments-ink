from datetime import datetime

import pytest
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django_comments.models import CommentFlag
from django_comments_ink import (
    get_comment_reactions_enum,
    get_object_reactions_enum,
)
from django_comments_ink.models import (
    CommentReaction,
    InkComment,
    ObjectReaction,
)
from django_comments_ink.tests.models import Article, Diary


@pytest.mark.django_db
@pytest.fixture
def an_article():
    """Creates an article that can receive comments."""
    return Article.objects.create(
        title="September", slug="september", body="During September..."
    )


@pytest.mark.django_db
@pytest.fixture
def a_diary_entry():
    """Creates a diary entry that can receive comments."""
    return Diary.objects.create(body="About today...")


@pytest.mark.django_db
@pytest.fixture
def an_articles_comment(an_article):
    """Send a comment to the article."""
    article_ct = ContentType.objects.get(app_label="tests", model="article")
    site = Site.objects.get(pk=1)
    return InkComment.objects.create(
        content_type=article_ct,
        object_pk=an_article.pk,
        content_object=an_article,
        site=site,
        comment="First comment to the article.",
        submit_date=datetime.now(),
    )


@pytest.mark.django_db
@pytest.fixture
def an_user():
    """Add a user to the DB."""
    return User.objects.create_user(
        "joe", "joe@example.com", "joepwd", first_name="Joe", last_name="Bloggs"
    )


@pytest.mark.django_db
@pytest.fixture
def an_user_2():
    """Add a user2 to the DB."""
    return User.objects.create_user(
        "alice",
        "alice@example.com",
        "alicepwd",
        first_name="Alice",
        last_name="Bloggs",
    )


@pytest.mark.django_db
@pytest.fixture
def a_comments_reaction(an_articles_comment, an_user):
    """Send a comment reaction to a comment."""
    reaction = get_comment_reactions_enum().LIKE_IT
    cmr = CommentReaction.objects.create(
        reaction=reaction, comment=an_articles_comment, counter=1
    )
    cmr.authors.add(an_user)
    cmr.save()
    return cmr


@pytest.mark.django_db
@pytest.fixture
def a_comments_flag(an_articles_comment, an_user):
    """Send a CommentFlag.SUGGEST_REMOVAL flag to a comment."""
    return CommentFlag.objects.create(
        user=an_user,
        comment=an_articles_comment,
        flag=CommentFlag.SUGGEST_REMOVAL,
    )


@pytest.mark.django_db
@pytest.fixture
def an_object_reaction(a_diary_entry, an_user):
    """Send an object reaction to a diary entry."""
    ctype = ContentType.objects.get_for_model(a_diary_entry)
    site = Site.objects.get(pk=1)
    reaction = get_object_reactions_enum().LIKE_IT
    objr = ObjectReaction.objects.create(
        content_type=ctype,
        object_pk=a_diary_entry.id,
        site=site,
        reaction=reaction,
        counter=1,
    )
    objr.authors.add(an_user)
    objr.save()
    return objr
