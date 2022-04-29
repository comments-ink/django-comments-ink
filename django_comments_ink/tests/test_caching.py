from django.core.cache.backends.base import BaseCache
from django_comments_ink import caching


def test_get_cache_returns_a_cache(monkeypatch):
    monkeypatch.setattr(caching, "dci_cache", None)
    cache = caching.get_cache()
    assert cache != None
    assert isinstance(cache, BaseCache)


def test_get_cache_can_be_none(monkeypatch):
    # I'm not sure if this can happen, but I test it just in case.
    # I mean, that accesing django's caches I can get a None
    # instead of an instance of a backend cache.
    my_cache = {"dci": None}
    monkeypatch.setattr(caching, "dci_cache", None)
    monkeypatch.setattr(caching, "caches", my_cache)
    cache = caching.get_cache()
    assert cache == None


def test_clear_cache_returns_False(monkeypatch):
    my_cache = {"dci": None}
    monkeypatch.setattr(caching, "dci_cache", None)
    monkeypatch.setattr(caching, "caches", my_cache)
    assert caching.clear_cache(1, 2, 3) == False


def test_clear_cache_returns_True(monkeypatch):
    monkeypatch.setattr(caching, "dci_cache", None)
    assert caching.clear_cache(1, 2, 3) == True
