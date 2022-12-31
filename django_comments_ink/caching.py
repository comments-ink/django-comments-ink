import logging

from django.core.cache import InvalidCacheBackendError, caches
from django_comments_ink.conf import settings

logger = logging.getLogger(__name__)

dci_cache = None


def get_cache():
    global dci_cache
    if dci_cache != None:
        return dci_cache

    try:
        dci_cache = caches[settings.COMMENTS_INK_CACHE_NAME]
    except InvalidCacheBackendError:
        logger.warning(
            "Cache '%s' is not defined in the settings module, "
            "using 'default' instead.",
            settings.COMMENTS_INK_CACHE_NAME,
        )
        dci_cache = caches["default"]
    except TypeError:
        logger.debug("COMMENTS_INK_CACHE_KEY=None => App cache is disabled.")

    return dci_cache


def clear_comment_cache(content_type_id, object_pk, site_id):
    dci_cache = get_cache()
    if dci_cache == None:
        logger.warning(
            "Cannot access the cache. Could not clear the cache "
            "for content_type={%d}, object_pk={%s} and site_id={%d}. "
            % (content_type_id, object_pk, site_id)
        )
        return False

    keys = []
    for key_pattern in ["comment_qs", "comment_count", "comments_paged"]:
        key = settings.COMMENTS_INK_CACHE_KEYS[key_pattern].format(
            ctype_pk=content_type_id, object_pk=object_pk, site_id=site_id
        )
        keys.append(key)

    for key_pattern in ["comment_list_auth", "comment_list_anon"]:
        key = settings.COMMENTS_INK_CACHE_KEYS[key_pattern].format(path="*")
        keys.append(key)

    for key in keys:
        if dci_cache.get(key):
            logger.debug("Delete cached key %s" % key)
            dci_cache.delete(key)

    return True


def clear_item(key, **kwargs):
    item = settings.COMMENTS_INK_CACHE_KEYS[key].format(**kwargs)
    if dci_cache.get(item):
        logger.debug("Delete cached key %s" % item)
        dci_cache.delete(item)
