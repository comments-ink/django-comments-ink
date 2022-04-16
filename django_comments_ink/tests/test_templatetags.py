import collections
import importlib
import json
import re
from collections import namedtuple
from datetime import datetime
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.paginator import PageNotAnInteger
from django.db.models.signals import pre_save
from django.http.response import Http404
from django.template import Context, Template, TemplateSyntaxError, loader
from django.test import TestCase as DjangoTestCase
from django.urls import reverse
from django_comments_ink import get_model, get_reactions_enum
from django_comments_ink.conf import settings
from django_comments_ink.models import (
    InkComment,
    publish_or_withhold_on_pre_save,
)
from django_comments_ink.templatetags import comments_ink
from django_comments_ink.tests.models import Article, MyComment
from django_comments_ink.tests.test_models import (
    thread_test_step_1,
    thread_test_step_2,
    thread_test_step_3,
    thread_test_step_4,
    thread_test_step_5,
)
from django_comments_ink.utils import get_current_site_id, get_html_id_suffix

_ink_model = "django_comments_ink.tests.models.MyComment"


class RenderInkCommentListTestCase(DjangoTestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title="September", slug="september", body="During September..."
        )

    def _create_comments(self, use_custom_model=False):
        #  step   id   parent level-0  level-1  level-2
        #    1     1      -      c1                     <- cm1
        #    2     3      1      --       c3            <-  cm1 to cm1
        #    5     8      3      --       --       c8   <-   cm1 to cm1 to cm1
        #    2     4      1      --       c4            <-  cm2 to cm1
        #    4     7      4      --       --       c7   <-   cm1 to cm2 to cm1
        #    1     2      -      c2                     <- cm2
        #    3     5      2      --       c5            <-  cm1 to cm2
        #    4     6      5      --       --       c6   <-   cm1 to cm1 to cm2
        #    5     9      -      c9                     <- cm9
        kwargs = {}
        if use_custom_model:
            kwargs = {"model": MyComment, "title": "title1"}
        thread_test_step_1(self.article, **kwargs)
        thread_test_step_2(self.article, **kwargs)
        thread_test_step_3(self.article, **kwargs)
        thread_test_step_4(self.article, **kwargs)
        thread_test_step_5(self.article, **kwargs)

    def _assert_all_comments_are_published(self, use_custom_model=False):
        t = "{% load comments comments_ink %}"
        if use_custom_model:
            t += (
                "{% render_inkcomment_list for object "
                "using my_comments/list.html %}"
            )
        else:
            t += "{% render_inkcomment_list for object %}"
        output = Template(t).render(
            Context({"object": self.article, "user": AnonymousUser()})
        )
        self.assertEqual(output.count('<div id="comment-'), 9)
        try:
            pos_c1 = output.index('<div id="comment-1"')
            pos_c3 = output.index('<div id="comment-3"')
            pos_c8 = output.index('<div id="comment-8"')
            pos_c4 = output.index('<div id="comment-4"')
            pos_c7 = output.index('<div id="comment-7"')
            pos_c2 = output.index('<div id="comment-2"')
            pos_c5 = output.index('<div id="comment-5"')
            pos_c6 = output.index('<div id="comment-6"')
            pos_c9 = output.index('<div id="comment-9"')
        except ValueError as exc:
            self.fail(exc)
        else:
            self.assertTrue(
                pos_c1
                < pos_c3
                < pos_c8
                < pos_c4
                < pos_c7
                < pos_c2
                < pos_c5
                < pos_c6
                < pos_c9
            )

        if use_custom_model:
            # Check that the title field of the custom MyComment model
            # is also part of the output.
            try:
                title_c1 = output.index('<h5 id="title-1">')
                title_c3 = output.index('<h5 id="title-3">')
                title_c8 = output.index('<h5 id="title-8">')
                title_c4 = output.index('<h5 id="title-4">')
                title_c7 = output.index('<h5 id="title-7">')
                title_c2 = output.index('<h5 id="title-2">')
                title_c5 = output.index('<h5 id="title-5">')
                title_c6 = output.index('<h5 id="title-6">')
                title_c9 = output.index('<h5 id="title-9">')
            except ValueError as exc:
                self.fail(exc)
            else:
                self.assertTrue(
                    title_c1
                    < title_c3
                    < title_c8
                    < title_c4
                    < title_c7
                    < title_c2
                    < title_c5
                    < title_c6
                    < title_c9
                )

    def test_render_inkcomment_list(self):
        self._create_comments()
        self._assert_all_comments_are_published()

    def _assert_only_comment_2_and_3_and_their_children_are_published(self):
        t = "{% load comments_ink %}" "{% render_inkcomment_list for object %}"
        output = Template(t).render(
            Context({"object": self.article, "user": AnonymousUser()})
        )
        self.assertEqual(output.count('<div id="comment-'), 4)
        # Only the following comments must be displayed, the other ones must
        # have been withheld when setting the comment 1 is_public to False.
        pos_c2 = output.index('<div id="comment-2"')
        pos_c5 = output.index('<div id="comment-5"')
        pos_c6 = output.index('<div id="comment-6"')
        pos_c9 = output.index('<div id="comment-9"')
        self.assertTrue(pos_c2 > 0)
        self.assertTrue(pos_c5 > 0)
        self.assertTrue(pos_c6 > 0)
        self.assertTrue(pos_c9 > 0)
        self.assertTrue(pos_c2 < pos_c5 < pos_c6 < pos_c9)

    def test_withhold_comment_1(self):
        self._create_comments()
        # Now set comment 1 is_public to False.
        c1 = InkComment.objects.get(pk=1)
        c1.is_public = False
        # Saving the instance triggers the pre_save signal in the models.py
        # module, which in turn withholds this comment and all its children.
        c1.save()
        self._assert_only_comment_2_and_3_and_their_children_are_published()

    def test_withhold_comment_1_and_publish_it_again(self):
        self._create_comments()
        # Now set comment 1 is_public to False.
        c1 = InkComment.objects.get(pk=1)
        c1.is_public = False
        # Saving the instance triggers the pre_save signal in the models.py
        # module, which in turn withholds this comment and all its children.
        c1.save()
        self._assert_only_comment_2_and_3_and_their_children_are_published()

        c1.is_public = True
        # Saving the instance with is_public = True publish the comment and
        # all the nested comments.
        c1.save()
        self._assert_all_comments_are_published()

    @patch.multiple(
        "django_comments_ink.conf.settings", COMMENTS_INK_MODEL=_ink_model
    )
    def test_render_inkcomment_tree_using_customized_comments(self):
        self._create_comments(use_custom_model=True)
        # Passsing use_custom_model will use the customized comments model,
        # and will check that the additional field provided with the
        # customized model is displayed in the tree of comments.
        self._assert_all_comments_are_published(use_custom_model=True)
        # Check that there are 9 instances of the custom model.
        self.assertEqual(MyComment.objects.count(), 9)

    @patch.multiple("django.conf.settings", SITE_ID=2)
    def test_render_inkcomment_list_for_one_site(self):
        site2 = Site.objects.create(domain="site2.com", name="site2.com")
        self.assertEqual(get_current_site_id(), 2)
        thread_test_step_1(self.article)
        thread_test_step_1(self.article, site=site2)
        thread_test_step_2(self.article, site=site2, parent_id=3)
        #           site    comment.id  parent.id
        #  step1      1          1          -
        #  step1      1          2          -
        #  step1      2          3          -
        #  step2      2          5          3
        #  step2      2          6          3
        #  step1      2          4          -
        t = "{% load comments_ink %}" "{% render_inkcomment_list for object %}"
        output = Template(t).render(
            Context({"object": self.article, "user": AnonymousUser()})
        )
        self.assertEqual(output.count('<div id="comment-'), 4)
        # Only the following comments must be displayed, the other ones must
        # have been withheld when setting the comment 1 is_public to False.
        pos_c3 = output.index('<div id="comment-3"')
        pos_c5 = output.index('<div id="comment-5"')
        pos_c6 = output.index('<div id="comment-6"')
        pos_c4 = output.index('<div id="comment-4"')
        self.assertTrue(pos_c3 > 0)
        self.assertTrue(pos_c5 > 0)
        self.assertTrue(pos_c6 > 0)
        self.assertTrue(pos_c4 > 0)
        self.assertTrue(pos_c3 < pos_c5 < pos_c6 < pos_c4)

    # ----------------------------------------------------------------------------
    # testcase cmt.id   parent level-0  level-1  level-2
    #  step1     2        -      c2                        <-                 cmt2
    #  step3     5        2      --       c5               <-         cmt1 to cmt2
    #  step4     6        5      --       --        c6     <- cmt1 to cmt1 to cmt2
    #  step5     9        -      c9                        <-                 cmt9
    @patch.multiple(
        "django.conf.settings",
        COMMENTS_HIDE_REMOVED=True,
        COMMENTS_INK_PUBLISH_OR_WITHHOLD_NESTED=True,
    )
    def test_render_inkcomment_list_for_HIDE_REMOVED_case_1(self):
        self._create_comments()
        # As the comment over the method shows, when COMMENTS_HIDE_REMOVE is
        # True, removing the comment 1 removes the comment from the listing and
        # withholds all the nested comments too.
        cm1 = InkComment.objects.get(pk=1)
        cm1.is_removed = True
        cm1.save()
        # Make changes in comments_ink.py so that comments are removed from the
        # queryset when COMMENTS_HIDE_REMOVED is True.
        t = "{% load comments_ink %}" "{% render_inkcomment_list for object %}"
        output = Template(t).render(
            Context({"object": self.article, "user": AnonymousUser()})
        )
        self.assertEqual(output.count('<div id="comment-'), 4)
        pos_c2 = output.index('<div id="comment-2"')
        pos_c5 = output.index('<div id="comment-5"')
        pos_c6 = output.index('<div id="comment-6"')
        pos_c9 = output.index('<div id="comment-9"')
        self.assertTrue(pos_c2 > 0)
        self.assertTrue(pos_c5 > 0)
        self.assertTrue(pos_c6 > 0)
        self.assertTrue(pos_c9 > 0)
        self.assertTrue(pos_c2 < pos_c5 < pos_c6 < pos_c9)

    # ----------------------------------------------------------------------------
    # testcase cmt.id   parent level-0  level-1  level-2
    #  step1     1        -      c1                        <-                 cmt1
    #  step1     2        -      c2                        <-                 cmt2
    #  step3     5        2      --       c5               <-         cmt1 to cmt2
    #  step4     6        5      --       --        c6     <- cmt1 to cmt1 to cmt2
    #  step5     9        -      c9                        <-                 cmt9
    @patch.multiple(
        "django.conf.settings",
        COMMENTS_HIDE_REMOVED=False,
        COMMENTS_INK_PUBLISH_OR_WITHHOLD_NESTED=True,
    )
    def test_render_inkcomment_list_for_HIDE_REMOVED_case_2(self):
        self._create_comments()
        # As the comment above the method shows, when
        # INK_COMMENTS_PUBLISH_OR_WITHHOLD_NESTED is True and
        # COMMENTS_HIDE_REMOVED is False, removing a comment make unvisible
        # its nested comments but keeps the removed one visible.
        cm1 = InkComment.objects.get(pk=1)
        cm1.is_removed = True
        cm1.save()
        t = "{% load comments_ink %}" "{% render_inkcomment_list for object %}"
        output = Template(t).render(
            Context({"object": self.article, "user": AnonymousUser()})
        )
        self.assertEqual(output.count('<div id="comment-'), 5)
        pos_c1 = output.index('<div id="comment-1"')
        pos_c2 = output.index('<div id="comment-2"')
        pos_c5 = output.index('<div id="comment-5"')
        pos_c6 = output.index('<div id="comment-6"')
        pos_c9 = output.index('<div id="comment-9"')
        self.assertTrue(pos_c1 > 0)
        self.assertTrue(pos_c2 > 0)
        self.assertTrue(pos_c5 > 0)
        self.assertTrue(pos_c6 > 0)
        self.assertTrue(pos_c9 > 0)
        self.assertTrue(pos_c1 < pos_c2 < pos_c5 < pos_c6 < pos_c9)

    # ----------------------------------------------------------------------------
    # testcase cmt.id   parent level-0  level-1  level-2
    #  step1     1        -      c1                        <-                 cmt1
    #  step2     3        1      --       c3               <-         cmt1 to cmt1
    #  step5     8        3      --       --        c8     <- cmt1 to cmt1 to cmt1
    #  step2     4        1      --       c4               <-         cmt2 to cmt1
    #  step4     7        4      --       --        c7     <- cmt1 to cmt2 to cmt1
    #  step1     2        -      c2                        <-                 cmt2
    #  step3     5        2      --       c5               <-         cmt1 to cmt2
    #  step4     6        5      --       --        c6     <- cmt1 to cmt1 to cmt2
    #  step5     9        -      c9                        <-                 cmt9
    @patch.multiple(
        "django.conf.settings",
        COMMENTS_HIDE_REMOVED=False,
        COMMENTS_INK_PUBLISH_OR_WITHHOLD_NESTED=False,
    )
    def test_render_inkcomment_tree_for_HIDE_REMOVED_case_3(self):
        self._create_comments()
        model_app_label = get_model()._meta.label
        pre_save.disconnect(
            publish_or_withhold_on_pre_save, sender=model_app_label
        )
        cm1 = InkComment.objects.get(pk=1)
        cm1.is_removed = True
        cm1.save()
        self._assert_all_comments_are_published()
        # Connect the receiver again.
        pre_save.connect(
            publish_or_withhold_on_pre_save, sender=model_app_label
        )


class CommentCSSThreadRangeTestCase(DjangoTestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title="September", slug="september", body="During September..."
        )

        # testcase cmt.id   parent level-0  level-1  level-2
        #  step1     1        -      c1                        <-                 cmt1
        #  step2     3        1      --       c3               <-         cmt1 to cmt1
        #  step5     8        3      --       --        c8     <- cmt1 to cmt1 to cmt1
        #  step2     4        1      --       c4               <-         cmt2 to cmt1
        #  step4     7        4      --       --        c7     <- cmt1 to cmt2 to cmt1
        #  step1     2        -      c2                        <-                 cmt2
        #  step3     5        2      --       c5               <-         cmt1 to cmt2
        #  step4     6        5      --       --        c6     <- cmt1 to cmt1 to cmt2
        #  step5     9        -      c9                        <-                 cmt9

        thread_test_step_1(self.article)
        thread_test_step_2(self.article)
        thread_test_step_3(self.article)
        thread_test_step_4(self.article)
        thread_test_step_5(self.article)

    def test_tag_with_comments_of_level_1(self):
        for pk in [1, 2, 9]:
            cm = InkComment.objects.get(pk=pk)
            self.assertEqual(cm.level, 0)
            t = (
                "{% load comments_ink %}"
                "{% comment_css_thread_range object %}"
            )
            output = Template(t).render(Context({"object": cm}))
            self.assertEqual(output, "l0-ini")

    def test_tag_with_comment_of_level_2(self):
        for pk in [3, 4, 5]:
            cm = InkComment.objects.get(pk=pk)
            self.assertEqual(cm.level, 1)
            t = (
                "{% load comments_ink %}"
                "{% comment_css_thread_range object %}"
            )
            output = Template(t).render(Context({"object": cm}))
            self.assertEqual(output, "l0-mid l1-ini")

    @patch.multiple(
        "django_comments_ink.conf.settings", COMMENTS_INK_MAX_THREAD_LEVEL=2
    )
    def test_tag_with_comment_of_level_3_eq_max_thread_level(self):
        for pk in [6, 7, 8]:
            cm = InkComment.objects.get(pk=pk)
            self.assertEqual(cm.level, 2)
            t = (
                "{% load comments_ink %}"
                "{% comment_css_thread_range object %}"
            )
            output = Template(t).render(Context({"object": cm}))
            self.assertEqual(output, "l0-mid l1-mid l2")

    @patch.multiple(
        "django_comments_ink.conf.settings", COMMENTS_INK_MAX_THREAD_LEVEL=2
    )
    def test_tag_with_comment_of_level_3_eq_max_thread_level_and_prefix(self):
        for pk in [6, 7, 8]:
            cm = InkComment.objects.get(pk=pk)
            self.assertEqual(cm.level, 2)
            t = (
                "{% load comments_ink %}"
                "{% comment_css_thread_range object 'thread-' %}"
            )
            output = Template(t).render(Context({"object": cm}))
            self.assertEqual(output, "thread-0-mid thread-1-mid thread-2")


def setup_paginator_example_1(an_article):
    """Set up the Example 1 (detailed in the paginator.py __docs__)."""
    article_ct = ContentType.objects.get(app_label="tests", model="article")
    site = Site.objects.get(pk=1)
    attrs = {
        "content_type": article_ct,
        "object_pk": an_article.pk,
        "content_object": an_article,
        "site": site,
        "comment": f"another comment to article {an_article.pk}",
        "submit_date": datetime.now(),
    }

    # Create 8 comments at level 0.
    for cm_level_0 in range(8):
        get_model().objects.create(**attrs)

    cmts_level_0 = get_model().objects.all()

    # Add the following number of child comments to the previous cmts_level_0.
    children_number = [10, 10, 10, 10, 10, 10, 5, 4]
    for index, cmt_level_0 in enumerate(cmts_level_0):
        for child in range(children_number[index]):
            InkComment.objects.create(**attrs, parent_id=cmt_level_0.pk)


@pytest.mark.django_db
def test_paginate_queryset(an_article):
    setup_paginator_example_1(an_article)
    queryset = get_model().objects.all()
    d = comments_ink.paginate_queryset(queryset, {})
    d_expected_keys = [
        "paginator",
        "page_obj",
        "is_paginated",
        "cpage_qs_param",
        "comment_list",
    ]
    for key in d_expected_keys:
        assert key in d

    assert d["paginator"] != None
    assert d["page_obj"].object_list.count() == 22
    assert d["is_paginated"] == True
    assert d["cpage_qs_param"] == settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
    assert d["comment_list"] == d["page_obj"].object_list


@pytest.mark.django_db
def test_paginate_queryset_with_pagination_disabled(an_article, monkeypatch):
    setup_paginator_example_1(an_article)
    monkeypatch.setattr(comments_ink.settings, "COMMENTS_INK_ITEMS_PER_PAGE", 0)
    queryset = get_model().objects.all()
    d = comments_ink.paginate_queryset(queryset, {})
    d_expected_keys = [
        "paginator",
        "page_obj",
        "is_paginated",
        "cpage_qs_param",
        "comment_list",
    ]
    for key in d_expected_keys:
        assert key in d

    assert d["paginator"] == None
    assert d["page_obj"] == None
    assert d["is_paginated"] == False
    assert d["cpage_qs_param"] == settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
    assert d["comment_list"] == queryset


class FakeRequest:
    def __init__(self, page_number=0):
        self.page_number = page_number

    def get_property(self):
        return {"cpage": self.page_number}

    GET = property(get_property)


@pytest.mark.django_db
def test_paginate_queryset_raises_ValueError(an_article):
    setup_paginator_example_1(an_article)
    queryset = get_model().objects.all()
    with pytest.raises(Http404):
        comments_ink.paginate_queryset(queryset, {"request": FakeRequest("x")})


@pytest.mark.django_db
def test_paginate_queryset_raises_ValueError_when_page_is_last(an_article):
    setup_paginator_example_1(an_article)
    queryset = get_model().objects.all()
    d = comments_ink.paginate_queryset(
        queryset, {"request": FakeRequest("last")}
    )
    d_expected_keys = [
        "paginator",
        "page_obj",
        "is_paginated",
        "cpage_qs_param",
        "comment_list",
    ]
    for key in d_expected_keys:
        assert key in d

    assert d["paginator"] != None
    assert d["page_obj"] != None
    assert d["page_obj"].object_list.count() == 33
    assert d["is_paginated"] == True
    assert d["cpage_qs_param"] == settings.COMMENTS_INK_PAGE_QUERY_STRING_PARAM
    comment_list_ids = [cm.parent_id for cm in d["comment_list"]]
    assert set(comment_list_ids) == set([5, 6, 7, 8])
    counter = collections.Counter(comment_list_ids)
    assert counter[5] == 11
    assert counter[6] == 11
    assert counter[7] == 6
    assert counter[8] == 5


@pytest.mark.django_db
def test_paginate_queryset_raises_InvalidPage(an_article):
    setup_paginator_example_1(an_article)
    queryset = get_model().objects.all()
    with pytest.raises(Http404):
        comments_ink.paginate_queryset(queryset, {"request": FakeRequest("4")})


@pytest.mark.django_db
def test_render_inkcomment_list_raises_IndexError(an_article):
    t = "{% load comments_ink %}" "{% render_inkcomment_list %}"
    with pytest.raises(IndexError):
        Template(t).render(Context({"object": an_article}))


@pytest.mark.django_db
def test_render_inkcomment_list_raises_TemplateSyntaxError(an_article):
    t = "{% load comments_ink %}" "{% render_inkcomment_list four object %}"
    with pytest.raises(TemplateSyntaxError):
        Template(t).render(Context({"object": an_article}))


def setup_small_comments_thread(an_article):
    # testcase cmt.id   parent level-0  level-1  level-2
    #  step1     1        -      c1                        <-                 cmt1
    #  step2     3        1      --       c3               <-         cmt1 to cmt1
    #  step5     8        3      --       --        c8     <- cmt1 to cmt1 to cmt1
    #  step2     4        1      --       c4               <-         cmt2 to cmt1
    #  step4     7        4      --       --        c7     <- cmt1 to cmt2 to cmt1
    #  step1     2        -      c2                        <-                 cmt2
    #  step3     5        2      --       c5               <-         cmt1 to cmt2
    #  step4     6        5      --       --        c6     <- cmt1 to cmt1 to cmt2
    #  step5     9        -      c9                        <-                 cmt9
    thread_test_step_1(an_article)
    thread_test_step_2(an_article)
    thread_test_step_3(an_article)
    thread_test_step_4(an_article)
    thread_test_step_5(an_article)


@pytest.mark.django_db
def test_render_inkcomment_list_for_app_model_pk(an_article):
    setup_small_comments_thread(an_article)
    t = (
        "{% load comments_ink %}"
        "{% render_inkcomment_list for tests.article 1 %}"
    )
    output = Template(t).render(
        Context({"object": an_article, "user": AnonymousUser()})
    )
    assert output.count('<div id="comment-') == 9
    pos_c1 = output.index('<div id="comment-1"')
    pos_c3 = output.index('<div id="comment-3"')
    pos_c8 = output.index('<div id="comment-8"')
    pos_c4 = output.index('<div id="comment-4"')
    pos_c7 = output.index('<div id="comment-7"')
    pos_c2 = output.index('<div id="comment-2"')
    pos_c5 = output.index('<div id="comment-5"')
    pos_c6 = output.index('<div id="comment-6"')
    pos_c9 = output.index('<div id="comment-9"')
    assert (
        pos_c1
        < pos_c3
        < pos_c8
        < pos_c4
        < pos_c7
        < pos_c2
        < pos_c5
        < pos_c6
        < pos_c9
    )


@pytest.mark.django_db
def test_render_inkcomment_list_for_app_model_pk_using_tmpl(an_article):
    setup_small_comments_thread(an_article)
    t = (
        "{% load comments_ink %}"
        "{% render_inkcomment_list"
        "   for tests.article 1 using my_comments/list.html"
        "%}"
    )
    output = Template(t).render(
        Context({"object": an_article, "user": AnonymousUser()})
    )
    assert output.count('<div id="comment-') == 9
    pos_c1 = output.index('<div id="comment-1"')
    pos_c3 = output.index('<div id="comment-3"')
    pos_c8 = output.index('<div id="comment-8"')
    pos_c4 = output.index('<div id="comment-4"')
    pos_c7 = output.index('<div id="comment-7"')
    pos_c2 = output.index('<div id="comment-2"')
    pos_c5 = output.index('<div id="comment-5"')
    pos_c6 = output.index('<div id="comment-6"')
    pos_c9 = output.index('<div id="comment-9"')
    assert (
        pos_c1
        < pos_c3
        < pos_c8
        < pos_c4
        < pos_c7
        < pos_c2
        < pos_c5
        < pos_c6
        < pos_c9
    )


@pytest.mark.django_db
def test_render_inkcomment_list_raises_with_many_args(an_article):
    t = (
        "{% load comments_ink %}"
        "{% render_inkcomment_list for tests.article 1 using tal pascual %}"
    )
    with pytest.raises(TemplateSyntaxError):
        Template(t).render(Context({"object": an_article}))


@pytest.mark.django_db
def test_render_inkcomment_list_raises_for_non_existing_object():
    t = (
        "{% load comments_ink %}"
        "{% render_inkcomment_list for obj_not_in_context %}"
    )
    output = Template(t).render(Context({"object": None}))
    assert output == ""


@pytest.mark.django_db
def test_get_inkcomment_permalink_in_page_eq_1(an_articles_comment):
    t = "{% load comments_ink %}" "{% get_inkcomment_permalink comment 1 %}"
    output = Template(t).render(Context({"comment": an_articles_comment}))
    assert output == an_articles_comment.get_absolute_url()


@pytest.mark.django_db
def test_get_inkcomment_permalink_in_page_gt_1(an_articles_comment):
    t = "{% load comments_ink %}" "{% get_inkcomment_permalink comment 2 %}"
    output = Template(t).render(Context({"comment": an_articles_comment}))
    assert output == "/comments/cr/11/1/1/?cpage=2#comment-1"


@pytest.mark.django_db
def test_get_inkcomment_permalink_in_page_gt_1_custom(an_articles_comment):
    t = (
        "{% load comments_ink %}"
        '{% get_inkcomment_permalink comment 2 "#c%(id)s" %}'
    )
    output = Template(t).render(Context({"comment": an_articles_comment}))
    assert output == "/comments/cr/11/1/1/?cpage=2#c1"


@pytest.mark.django_db
def test_get_inkcomment_permalink_in_page_gt_1_fails(an_articles_comment):
    t = (
        "{% load comments_ink %}"
        '{% get_inkcomment_permalink comment 2 "$c%(doesnotexist)s" %}'
    )
    output = Template(t).render(Context({"comment": an_articles_comment}))
    assert output == an_articles_comment.get_absolute_url()


@pytest.mark.django_db
def test_get_inkcomment_permalink_in_wrong_page_number(an_articles_comment):
    t = "{% load comments_ink %}" '{% get_inkcomment_permalink comment "a" %}'
    with pytest.raises(PageNotAnInteger):
        Template(t).render(Context({"comment": an_articles_comment}))


@pytest.mark.django_db
def test_get_comments_api_props(an_article):
    t = "{% load comments_ink %}" "{% get_comments_api_props for object %}"
    output = Template(t).render(Context({"object": an_article}))
    props = json.loads(output)
    assert props == {
        "comment_count": 0,
        "input_allowed": True,
        "current_user": "0:Anonymous",
        "request_name": False,
        "request_email_address": False,
        "is_authenticated": False,
        "who_can_post": "all",
        "comment_flagging_enabled": False,
        "comment_reactions_enabled": False,
        "object_reactions_enabled": False,
        "can_moderate": False,
        "react_url": "/comments/api/react/",
        "delete_url": "/comments/delete/0/",
        "reply_url": "/comments/reply/0/",
        "flag_url": "/comments/api/flag/",
        "list_url": "/comments/api/tests-article/1/",
        "count_url": "/comments/api/tests-article/1/count/",
        "send_url": "/comments/api/comment/",
        "form": {
            "content_type": "tests.article",
            "object_pk": "1",
            "timestamp": props["form"]["timestamp"],
            "security_hash": props["form"]["security_hash"],
        },
        "default_followup": False,
        "html_id_suffix": "7f7a81d9acbab29db51ca501c2d44afe313227bc",
        "max_thread_level": 3,
        "login_url": "/accounts/login/",
        "comments_page_qs_param": "cpage",
    }


@pytest.mark.django_db
def test_get_comments_api_props_raises_1(an_article):
    t = "{% load comments_ink %}" "{% get_comments_api_props %}"
    with pytest.raises(TemplateSyntaxError):
        Template(t).render(Context({"object": an_article}))


@pytest.mark.django_db
def test_get_comments_api_props_raises_2(an_article):
    t = "{% load comments_ink %}" "{% get_comments_api_props for %}"
    with pytest.raises(TemplateSyntaxError):
        Template(t).render(Context({"object": an_article}))


@pytest.mark.django_db
def test_comment_reaction_form_target(an_articles_comment):
    t = "{% load comments_ink %}" "{% comment_reaction_form_target comment %}"
    output = Template(t).render(Context({"comment": an_articles_comment}))
    assert output == reverse(
        "comments-ink-react", args=(an_articles_comment.id,)
    )


@pytest.mark.django_db
def test_render_reactions_buttons(a_comments_reaction):
    user_reactions = [get_reactions_enum()(a_comments_reaction.reaction)]
    t = (
        "{% load comments_ink %}"
        "{% render_reactions_buttons user_reactions %}"
    )
    output = Template(t).render(Context({"user_reactions": user_reactions}))
    template = loader.get_template("comments/reactions_buttons.html")
    expected = template.render(
        {
            "reactions": get_reactions_enum(),
            "user_reactions": user_reactions,
            "break_every": settings.COMMENTS_INK_REACTIONS_ROW_LENGTH,
        }
    )
    assert output == expected

    # Find the button representing the 'a_comments_reaction',
    # which is the '+1' reaction, with the CSS class 'active'.
    active_reaction = r"""<button
    type="submit" name="reaction" value="+"
    class="secondary active"
  >"""
    assert output.find(active_reaction) > -1

    # Find the button of the '-1' reaction, without the 'active' class.
    not_active_reaction = r"""<button
    type="submit" name="reaction" value="-"
    class="secondary "
  >"""
    assert output.find(not_active_reaction) > -1


def test_render_reactions_buttons_raises_TemplateSyntaxError():
    t = "{% load comments_ink %}" "{% render_reactions_buttons %}"
    with pytest.raises(TemplateSyntaxError):
        Template(t).render(Context({}))


@pytest.mark.django_db
def test_authors_list(a_comments_reaction, an_user):
    t = "{% load comments_ink %}" "{{ reaction|authors_list }}"
    output = Template(t).render(Context({"reaction": a_comments_reaction}))
    expected = Template("{{ result }}").render(
        Context({"result": [settings.COMMENTS_INK_API_USER_REPR(an_user)]})
    )
    assert output == expected


@pytest.mark.django_db
def test_reaction_enum(a_comments_reaction):
    t = "{% load comments_ink %}" "{{ reaction|get_reaction_enum }}"
    output = Template(t).render(Context({"reaction": a_comments_reaction}))
    expected = Template("{{ reaction }}").render(
        Context(
            {"reaction": get_reactions_enum()(a_comments_reaction.reaction)}
        )
    )
    assert output == expected


@pytest.mark.django_db
def test_get_comment(an_articles_comment):
    t = (
        "{% load comments_ink %}"
        "{% with comment=1|get_comment %}"
        "{{ comment.comment }}"
        "{% endwith %}"
    )
    output = Template(t).render(Context({}))
    assert output == an_articles_comment.comment


@pytest.mark.django_db
def test_render_only_users_can_post_template(an_article):
    t = (
        "{% load comments_ink %}"
        "{% render_only_users_can_post_template object %}"
    )
    output = Template(t).render(Context({"object": an_article}))
    suffix = get_html_id_suffix(an_article)
    assert output.find(f"only-users-can-post-{suffix}") > -1


def test_using_a_theme_dir(monkeypatch):
    monkeypatch.setattr(
        comments_ink.settings, "COMMENTS_INK_THEME_DIR", "feedback_in_header"
    )
    importlib.reload(comments_ink)

    templates = []
    templates.extend(comments_ink._list_html_tmpl[:3])
    templates.extend(comments_ink._form_html_tmpl[:3])
    templates.extend(comments_ink._reply_template_html_tmpl[:3])
    templates.extend(comments_ink._reactions_panel_template_tmpl[:1])
    templates.extend(comments_ink._reactions_buttons_tmpl[:1])

    for tmpl_path in templates:
        assert tmpl_path.find("{theme_dir}") > -1

    # Revert theme.
    monkeypatch.setattr(comments_ink.settings, "COMMENTS_INK_THEME_DIR", "")
    importlib.reload(comments_ink)


# ---------------------------------------------------------------------

re_field_1 = r'<input type="{type}" name="{name}" value="{value}" id="{id}">'
re_field_2 = r'<input type="{type}" name="{name}" value="[\d]+" id="{id}">'
re_field_3 = r'<input type="{type}" name="{name}" value="[\w]+" id="{id}">'


def check_form_fields_in_output(output):
    # Check field 'content_type':
    re_field_formated = re_field_1.format(
        type="hidden",
        name="content_type",
        value="tests.article",
        id="id_content_type",
    )
    match = re.search(re_field_formated, output)
    assert match != None

    # Check field 'object_pk':
    re_field_formated = re_field_1.format(
        type="hidden", name="object_pk", value="1", id="id_object_pk"
    )
    match = re.search(re_field_formated, output)
    assert match != None

    # Check field 'timestamp':
    re_field_formated = re_field_2.format(
        type="hidden", name="timestamp", id="id_timestamp"
    )
    match = re.search(re_field_formated, output)
    assert match != None

    # Check field 'security_hash':
    re_field_formated = re_field_3.format(
        type="hidden", name="security_hash", id="id_security_hash"
    )
    match = re.search(re_field_formated, output)
    assert match != None

    # Check field 'reply_to':
    re_field_formated = re_field_1.format(
        type="hidden", name="reply_to", value="0", id="id_reply_to"
    )
    match = re.search(re_field_formated, output)
    assert match != None

    # Check field 'honeypot':
    match = re.search(
        r'<input type="text" name="honeypot" id="id_honeypot">', output
    )
    assert match != None

    # Check field 'comment':
    match = re.search(
        (
            r'<textarea name="comment" placeholder="Your comment"'
            r' class="form-control" required id="id_comment">'
        ),
        output,
    )
    assert match != None

    # Check field 'name':
    match = re.search(
        (
            r'<input type="text" name="name" placeholder="name"'
            r' class="form-control" required id="id_name">'
        ),
        output,
    )
    assert match != None

    # Check field 'email':
    match = re.search(
        (
            r'<input type="text" name="email" placeholder="mail address"'
            r' class="form-control" required id="id_email">'
        ),
        output,
    )
    assert match != None

    # Check field 'url':
    match = re.search(
        (
            r'<input type="text" name="url" placeholder="url your name'
            r' links to \(optional\)" class="form-control" id="id_url">'
        ),
        output,
    )
    assert match != None

    # Check field 'followup':
    match = re.search(
        (
            r'<input type="checkbox" name="followup" id="id_followup"'
            r' class="custom-control-input">'
        ),
        output,
    )
    assert match != None


@pytest.mark.django_db
def test_render_inkcomment_form_for_object(an_article):
    re_form = (
        r'<form method="(?P<method>\w+)" autocomplete="off"'
        r' action="(?P<action>[\w\/]+)">'
    )

    t = "{% load comments_ink %}" "{% render_inkcomment_form for object %}"
    output = Template(t).render(Context({"object": an_article}))

    # Check <form> element.
    match = re.search(re_form, output)
    assert match.group("method") == "POST"
    assert match.group("action") == "/comments/post/"
    check_form_fields_in_output(output)


@pytest.mark.django_db
def test_render_inkcomment_form_for_non_existing_object():
    t = "{% load comments_ink %}" "{% render_inkcomment_form for object %}"
    output = Template(t).render(Context({"object": {}}))
    assert output == ""
    output = Template(t).render(Context({"object": None}))
    assert output == ""


@pytest.mark.django_db
def test_render_inkcomment_form_for_app_model_pk():
    t = (
        "{% load comments_ink %}"
        "{% render_inkcomment_form for tests.article 1 %}"
    )
    output = Template(t).render(Context({}))
    assert output == ""


# ---------------------------------------------------------------------
@pytest.mark.django_db
def test_render_comment_reply_template_for_object(an_article):
    re_form = (
        r'<form method="(?P<method>\w+)" autocomplete="off"'
        r' action="(?P<action>[\w\/]+)" id="reply-form"'
        r' style="display: none;">'
    )

    t = (
        "{% load comments_ink %}"
        "{% render_comment_reply_template for object %}"
    )
    output = Template(t).render(Context({"object": an_article}))

    # Check <form> element.
    match = re.search(re_form, output)
    assert match.group("method") == "POST"
    assert match.group("action") == "/comments/post/"
    check_form_fields_in_output(output)

    # Check field 'comment':
    match = re.search(
        r'<textarea rows="1" placeholder="Your reply"></textarea>',
        output,
    )
    assert match != None


@pytest.mark.django_db
def test_render_comment_reply_template_for_non_existing_object():
    t = (
        "{% load comments_ink %}"
        "{% render_comment_reply_template for object %}"
    )
    output = Template(t).render(Context({"object": {}}))
    assert output == ""
    output = Template(t).render(Context({"object": None}))
    assert output == ""


@pytest.mark.django_db
def test_render_comment_reply_template_for_app_model_pk():
    t = (
        "{% load comments_ink %}"
        "{% render_comment_reply_template for tests.article 1 %}"
    )
    output = Template(t).render(Context({}))
    assert output == ""


# ---------------------------------------------------------------------
def test_get_dci_theme_dir_is_empty():
    t = "{% load comments_ink %}" "{% get_dci_theme_dir %}"
    output = Template(t).render(Context({}))
    assert output == ""


def test_get_dci_theme_dir_is__feedback_in_header(monkeypatch):
    monkeypatch.setattr(
        comments_ink.settings, "COMMENTS_INK_THEME_DIR", "feedback_in_header"
    )
    importlib.reload(comments_ink)
    t = "{% load comments_ink %}" "{% get_dci_theme_dir %}"
    output = Template(t).render(Context({}))
    assert output == "themes/feedback_in_header"
    monkeypatch.setattr(comments_ink.settings, "COMMENTS_INK_THEME_DIR", "")
    importlib.reload(comments_ink)


# ---------------------------------------------------------------------
def test_render_reactions_panel_template():
    t = "{% load comments_ink %}" "{% render_reactions_panel_template %}"
    output = Template(t).render(Context({}))
    enum_tuples = [
        (enum.value, enum.label, enum.icon) for enum in get_reactions_enum()
    ]
    for value, label, icon in enum_tuples:
        reaction_button = (
            rf"<button"
            rf' data-title="{label}"'
            rf' data-code="{value}"'
            rf' class="emoji">&{icon};</button>'
        )
        output.find(reaction_button) > -1


# ---------------------------------------------------------------------
def test_get_gravatar_url():
    output = comments_ink.get_gravatar_url("lena.rosenthal@example.com")
    assert output.startswith("//www.gravatar.com/avatar/")


# ---------------------------------------------------------------------
def test_get_user_avatar_or_gravatar():
    t = "{% load comments_ink %}" "{% get_user_avatar_or_gravatar %}"
    try:
        Template(t).render(Context({}))
    except TemplateSyntaxError as exc:
        assert exc.args[0] == (
            "The 'get_user_avatar_or_gravatar' template tag requires "
            "to have installed the package 'django-avatar'."
        )
    else:
        assert False
