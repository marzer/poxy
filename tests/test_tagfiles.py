#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Unit tests for downloaded-tagfile content validation (poxy.pipeline.doxyfile.tagfile_text_is_valid).

Guards the fix for a non-tagfile (typically an HTTP error page returned when a tagfile URL has moved)
being written out and then fed to Doxygen, which interprets the HTML as a tagfile and floods the build
with confusing warnings.
"""

import pytest

from poxy.pipeline import doxyfile
from poxy.pipeline.doxyfile import tagfile_text_is_valid
from poxy.utils import Error

VALID = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<tagfile doxygen_version="1.14.0">
  <compound kind="class"><name>foo</name><filename>classfoo.html</filename></compound>
</tagfile>
"""

HTML_404 = """<!DOCTYPE html>
<html lang="en"><head><title>Site not found</title></head>
<body><h1>404</h1></body></html>
"""


def test_valid_tagfile():
    assert tagfile_text_is_valid(VALID) is True


def test_html_error_page_rejected():
    assert tagfile_text_is_valid(HTML_404) is False


@pytest.mark.parametrize('text', ['', '   \n\t ', 'not xml at all', '<tagfile><unclosed>'])
def test_garbage_rejected(text):
    assert tagfile_text_is_valid(text) is False


def test_wrong_root_element_rejected():
    assert tagfile_text_is_valid('<?xml version="1.0"?><notatagfile/>') is False


# ----------------------------------------------------------------------------------------------------------------------
# github:// tagfile resolution (GitHub API stubbed)
# ----------------------------------------------------------------------------------------------------------------------


class _Resp:
    def __init__(self, json_data=None, content=b''):
        self._json = json_data
        self.content = content

    def json(self):
        return self._json


class _Ctx:
    def verbose(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass


def _resolve(source, dest, token, fetch):
    return doxyfile._resolve_github_tagfile(_Ctx(), source, dest, token, fetch)  # type: ignore[arg-type]


def test_dest_autoresolves_from_pages_even_when_content_is_cached(monkeypatch):
    # the caching case: fetch=False (tagfile already on disk) must still resolve the dest from the Pages API,
    # otherwise the TAGFILES entry ends up with an empty link base
    calls = []

    def fake_get(url, token, accept=r'application/vnd.github+json', timeout=30):
        calls.append(url)
        if url.endswith(r'/pages'):
            return _Resp(json_data={'html_url': 'https://x.pages.github.io', 'source': {'branch': 'gh-pages'}})
        raise AssertionError(f'unexpected fetch while cached: {url}')

    monkeypatch.setattr(doxyfile, 'github_api_get', fake_get)
    text, dest = _resolve('github://o/r/a.tagfile.xml', '', 'tok', fetch=False)
    assert text is None
    assert dest == 'https://x.pages.github.io/'  # trailing slash appended
    assert any(u.endswith('/pages') for u in calls)


def test_explicit_dest_makes_no_api_calls_when_cached(monkeypatch):
    def fake_get(*a, **k):
        raise AssertionError('no API call should happen for an explicit dest + cached content')

    monkeypatch.setattr(doxyfile, 'github_api_get', fake_get)
    text, dest = _resolve('github://o/r/a.xml@main', 'https://d/', 'tok', fetch=False)
    assert text is None
    assert dest == 'https://d/'


def test_release_form_fetches_named_asset(monkeypatch):
    def fake_get(url, token, accept=r'application/vnd.github+json', timeout=30):
        if url.endswith('/releases/latest'):
            return _Resp(
                json_data={'tag_name': 'v1', 'assets': [{'name': 'a.tagfile.xml', 'url': 'https://api/asset/1'}]}
            )
        if url == 'https://api/asset/1':
            assert accept == 'application/octet-stream'
            return _Resp(content=b'<tagfile/>')
        raise AssertionError(f'unexpected url: {url}')

    monkeypatch.setattr(doxyfile, 'github_api_get', fake_get)
    text, dest = _resolve('github://o/r/a.tagfile.xml@release', 'https://d/', 'tok', fetch=True)
    assert text == '<tagfile/>'
    assert dest == 'https://d/'


def test_release_form_with_tag_hits_tagged_release(monkeypatch):
    seen = []

    def fake_get(url, token, accept=r'application/vnd.github+json', timeout=30):
        seen.append(url)
        if url.endswith('/releases/tags/v1.2.3'):
            return _Resp(json_data={'tag_name': 'v1.2.3', 'assets': [{'name': 'a.xml', 'url': 'https://api/asset/9'}]})
        if url == 'https://api/asset/9':
            return _Resp(content=b'<tagfile/>')
        raise AssertionError(f'unexpected url: {url}')

    monkeypatch.setattr(doxyfile, 'github_api_get', fake_get)
    _resolve('github://o/r/a.xml@release:v1.2.3', 'https://d/', 'tok', fetch=True)
    assert any(u.endswith('/releases/tags/v1.2.3') for u in seen)


def test_release_form_missing_asset_lists_available(monkeypatch):
    def fake_get(url, token, accept=r'application/vnd.github+json', timeout=30):
        if url.endswith('/releases/latest'):
            return _Resp(json_data={'tag_name': 'v1', 'assets': [{'name': 'other.xml', 'url': 'u'}]})
        raise AssertionError(url)

    monkeypatch.setattr(doxyfile, 'github_api_get', fake_get)
    with pytest.raises(Error, match=r"no asset named 'a.tagfile.xml'.*available assets: other.xml"):
        _resolve('github://o/r/a.tagfile.xml@release', 'https://d/', 'tok', fetch=True)


def test_missing_pages_url_raises_helpful_error(monkeypatch):
    def fake_get(url, token, accept=r'application/vnd.github+json', timeout=30):
        if url.endswith('/pages'):
            return _Resp(json_data={})  # no html_url
        raise AssertionError(url)

    monkeypatch.setattr(doxyfile, 'github_api_get', fake_get)
    with pytest.raises(Error, match=r'could not resolve a Pages URL'):
        _resolve('github://o/r/a.xml', '', 'tok', fetch=False)
