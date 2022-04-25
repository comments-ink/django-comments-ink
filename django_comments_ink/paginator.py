"""
Pagination for comments threads.

Given the following comments structure the paginator will display comments
in several pages containing different number of comments, so that comment
threads (a thread of comments have all the same value for thread_id) are
fully displayed in one page. Even if the number of comments in the thread
exceed the `per_page` value.

Relevant settings:
 * COMMENTS_INK_ITEMS_PER_PAGE = 25
 * COMMENTS_INK_MAX_LAST_PAGE_ORPHANS = 10

Example 1:
  Comment IDs of level 0:  [ 1,  2,  3,  4,  5,  6,  7,  8]
  Their `nested_count`:    [10, 10, 10, 10, 10, 10,  5,  4]
  Computed comments/page:  [    22,     22,             33]

  Thread 1 has 11 comments, still below per_page. We add Comment thread 2, now
  we have 22 comments, still below per_page. We add Comment thread 3 and now
  the result exceeds per_page, so we will only accept it if not only adding
  Comment thread 3 but all the rest represents a number of comments below
  per_page + orphans, which is not the case: 77 comments > per_page + orphans.
  So page 1 contains 22 comments, and we move to compute comments for page 2.
  Page 2 start with 11 comments of Thread 3, we add 11 comments of Thread 4,
  and when we try to add Thread 5 we have over per_page, so we will only accept
  it if adding all the rest will represent a number of comments below
  per_page + orphans, which is not the case: 55 > 35, so page 2 will contain
  22 comments of Thread 3 and Thread 4. Page 3 starts with 11 comments of
  Thread 5 + 11 comments of Thread 6. Adding the 6 comments of Thread 7 would
  exceed per_page, so we will only accept to change page 3 if adding all the
  rest would keep the number of comments below per_page + orphans. And that is
  the case now: 22 comments (thread 5 + thread 6) + 11 (thread 7 + thread 8) is
  33 comments, which is below 35, so the last page contains 33 comments.

Example 2:
  Comment IDs of level 0:  [ 1,  2, 3]
  Their `nested_count`:    [24, 24, 8]
  Computed comments/page:  [25,    34]

  Comment 1 has 24 nested comments, it doesn't exceed per_page (25), but
  adding all the rest of comment threads would exceed per_page + orphans, so
  the 1st page displays 25 comments (comment 1 + its 24 nested comments).
  Comment thread 2 is made of 25 comments. Adding all the rest (34) would not
  exceed per_page + orphans (35), so the 2nd (or last page) will have 34
  comments.

Example 3:
  Comment IDs of level 0:  [ 1,  2, 3]
  Their `nested_count`:    [24,  8, 8]
  Computed comments/page:  [25,    18]

  Comment 1 has 24 nested comments, it doesn't exceed per_page (25). Adding
  all the rest (18) would represent 43 comments which exceed per_page + orphans
  (35). So the 1st page displays the 25 comments of thread 1. For page 2,
  comment thread 2 has 9 comments, and adding the rest is still below
  per_page + orphans, so the 2nd page will contain 18 comments.

"""
import logging

from django.core.paginator import Paginator
from django.db.models.query import QuerySet
from django.utils.functional import cached_property
from django_comments_ink import caching

logger = logging.getLogger(__name__)


class CommentsPaginator(Paginator):
    """
    Paginator for comments.

    Given an `object_list` of comments, it checks how many threads fit per page.
    If a thread has more comments than the given `per_page` limit it ignores the
    limit so that the thread is not cut in several pages.
    """

    def __init__(self, *args, **kwargs):
        self.comments_folded = kwargs.pop("comments_folded", {})
        self.ckey_prefix = kwargs.pop("cache_key_prefix", "")
        self.dci_cache = caching.get_cache()

        # Comment out next lines when debugging paginator's cache keys.
        if self.dci_cache != None and self.ckey_prefix != "":
            sub_keys_set = self.dci_cache.get(self.ckey_prefix)
            if sub_keys_set:
                logger.debug(
                    "sub_keys_set for %s: %s", self.ckey_prefix, sub_keys_set
                )

        super().__init__(*args, **kwargs)
        if type(self.object_list) is not QuerySet:
            raise TypeError("'object_list' is not a QuerySet.")

    def get_subkey_cache(self, subkey):
        if self.dci_cache == None or self.ckey_prefix == "":
            return
        # If the key <sub_ckey> does exist as a key in
        # the set stored in the <ckey_prefix> in the cache, then
        # access the combinaned <self.ckey_prefix>/<sub_ckey>
        # to get the previously computed object_list.
        sub_keys_set = self.dci_cache.get(self.ckey_prefix)
        if sub_keys_set and subkey in sub_keys_set:
            composed_key = f"{self.ckey_prefix}/{subkey}"
            result = self.dci_cache.get(composed_key)
            if result != None:
                return result

    def set_subkey_cache(self, subkey, value):
        if self.dci_cache == None or self.ckey_prefix == "":
            return
        # Save the object_list in cache.
        sub_keys_set = self.dci_cache.get(self.ckey_prefix)
        if sub_keys_set != None:
            if not subkey in sub_keys_set:
                sub_keys_set.add(subkey)
        else:
            sub_keys_set = {subkey}
        logger.debug("Caching key %s, value %s", self.ckey_prefix, sub_keys_set)
        self.dci_cache.set(self.ckey_prefix, sub_keys_set, timeout=None)

        # Store the object_list in cache using a composed key.
        composed_key = f"{self.ckey_prefix}/{subkey}"
        logger.debug("Adding %s to the cache", composed_key)
        self.dci_cache.set(composed_key, value, timeout=None)

    def get_count_in_thread(self, comment):
        if self.comments_folded and comment.id in self.comments_folded:
            return 1
        else:
            return comment.nested_count + 1

    def get_sub_ckey(self, page, fold):
        page_part = "all-pages" if page == None else f"page-{str(page)}"
        if fold:
            fold_part = f"folded-{','.join([str(cid) for cid in fold])}"
        else:
            fold_part = "all-unfolded"
        return page_part + "-" + fold_part

    @cached_property
    def in_page(self):
        """
        Calculate the variable number of comments displayed in each page.

        Returns a list. Each index item represents the number of comments to
        display in the page index + 1.
        """
        inpage_subkey = (
            self.get_sub_ckey(None, self.comments_folded) + ":in_page_list"
        )
        inpage = self.get_subkey_cache(inpage_subkey)
        if inpage != None:
            logger.debug("in_page from cache %s: %s", self.ckey_prefix, inpage)
            return inpage

        ptotal = 0  # Page total number of comments.
        inpage = []

        cgroups = [
            self.get_count_in_thread(cm)
            for cm in self.object_list.filter(level=0)
        ]
        for index, group_count in enumerate(cgroups):
            if ptotal > 0 and ptotal + group_count > self.per_page:
                if sum(cgroups[index:], ptotal) > self.per_page + self.orphans:
                    # All comments are too many to be in this page.
                    inpage.append(ptotal)
                    ptotal = group_count
                else:
                    inpage.append(sum(cgroups[index:], ptotal))
                    ptotal = 0
                    break
            else:
                ptotal += group_count
        if ptotal:
            inpage.append(ptotal)
        self.set_subkey_cache(inpage_subkey, inpage)  # Store it in cache.
        logger.debug(
            "in_page computed (saved in cache) %s: %s", self.ckey_prefix, inpage
        )
        return inpage

    def page(self, number):
        number = self.validate_number(number)

        # See whether the object_list has been stored in the cache.
        sub_ckey = self.get_sub_ckey(number, self.comments_folded)
        object_list = self.get_subkey_cache(sub_ckey)
        if object_list != None:
            return self._get_page(object_list, number, self)

        if number == 1:
            bottom = 0
        else:
            bottom = sum(self.in_page[0 : number - 1])
        top = bottom + self.in_page[number - 1]
        object_list = self.object_list[bottom:top]

        # Store it in cache.
        self.set_subkey_cache(sub_ckey, object_list)

        return self._get_page(object_list, number, self)

    @cached_property
    def count(self):
        subkey = "count"
        result = self.get_subkey_cache(subkey)
        if result != None:
            return result
        count = super().count
        self.set_subkey_cache(subkey, count)  # Store it in cache.
        return count

    @cached_property
    def num_pages(self):
        """Return the total number of pages."""
        if self.count == 0 and not self.allow_empty_first_page:
            return 0
        return len(self.in_page)
