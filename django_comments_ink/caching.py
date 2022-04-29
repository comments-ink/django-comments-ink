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

    return dci_cache


def clear_cache(content_type_id, object_pk, site_id):
    dci_cache = get_cache()
    if dci_cache == None:
        logger.warning(
            "Cannot access the cache. Could not clear the cache "
            "for content_type={%d}, object_pk={%d} and site_id={%d}. "
            % (content_type_id, object_pk, site_id)
        )
        return False

    keys = []
    for key_pattern in [
        "comments_qs",
        "comments_count",
        "comments_paged",
    ]:
        key = settings.COMMENTS_INK_CACHE_KEYS[key_pattern].format(
            ctype_pk=content_type_id, object_pk=object_pk, site_id=site_id
        )
        keys.append(key)

    for key in keys:
        if dci_cache.get(key):
            logger.debug("Delete cached key %s" % key)
            dci_cache.delete(key)

    return True
