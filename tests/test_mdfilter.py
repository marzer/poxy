#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Unit tests for the standalone markdown input filter (poxy.mdfilter), wired into Doxygen via FILTER_PATTERNS.
"""

from poxy.mdfilter import (
    SENTINEL_AMP,
    SENTINEL_AT,
    SENTINEL_HEX,
    normalize_toc_directives,
    protect_entities,
    strip_handrolled_toc,
)


def test_toc_html_level_retargeted_to_xml():
    # doxygen omits <tableofcontents> from XML for the HTML-only form; retarget to XML so it emits it (pruned)
    assert (
        normalize_toc_directives('# T\n\n@tableofcontents{HTML:2}\n\n## A\n')
        == '# T\n\n@tableofcontents{XML:2}\n\n## A\n'
    )


def test_toc_backslash_html_level_retargeted():
    assert normalize_toc_directives('\\tableofcontents{HTML:1}\n') == '@tableofcontents{XML:1}\n'


def test_toc_markdown_marker_retargeted():
    assert normalize_toc_directives('# T\n\n[TOC]\n\n## A\n') == '# T\n\n@tableofcontents\n\n## A\n'


def test_plain_tableofcontents_unchanged():
    text = '# T\n\n@tableofcontents\n\n## A\n'
    assert normalize_toc_directives(text) == text


def test_toc_marker_in_prose_not_touched():
    # only a standalone [TOC] line is a directive; a bracketed link/text elsewhere must survive
    text = 'see the [TOC] section for details\n'
    assert normalize_toc_directives(text) == text


def test_strips_handrolled_toc_and_inserts_directive():
    text = "# Title\n\nIntro.\n\n- [A](#a)\n- [B](#b)\n  - [B1](#b1)\n\n## A\n"
    out = strip_handrolled_toc(text)
    assert '[A](#a)' not in out
    assert '[B1](#b1)' not in out
    assert '@tableofcontents' in out  # inserted where the list was, since none existed
    assert '## A' in out  # real content untouched


def test_strips_handrolled_toc_without_duplicating_existing_directive():
    text = "# Title\n\n@tableofcontents\n\n- [A](#a)\n- [B](#b)\n\n## A\n"
    out = strip_handrolled_toc(text)
    assert '[A](#a)' not in out
    assert out.count('@tableofcontents') == 1  # not duplicated


def test_respects_existing_toc_marker_variants():
    for marker in ('[TOC]', '\\tableofcontents'):
        text = f"# T\n\n{marker}\n\n- [A](#a)\n- [B](#b)\n\n## A\n"
        out = strip_handrolled_toc(text)
        assert '[A](#a)' not in out
        assert '@tableofcontents' not in out  # the existing marker already provides the TOC


def test_leaves_ordinary_link_lists_alone():
    # a list of EXTERNAL links is not a TOC and must survive
    text = "# T\n\n- [Home](https://example.com)\n- [Docs](https://example.com/docs)\n\n## Section\n"
    assert strip_handrolled_toc(text) == text


def test_leaves_mixed_content_lists_alone():
    # items that are not purely a single in-page anchor link are not a TOC
    text = "# T\n\n- [A](#a) and some prose\n- plain bullet\n\n## A\n"
    assert strip_handrolled_toc(text) == text


def test_ignores_single_item_list():
    # a lone anchor-link bullet is not enough to be considered a TOC
    text = "# T\n\n- [A](#a)\n\n## A\n"
    assert strip_handrolled_toc(text) == text


def test_noop_when_no_list():
    text = "# T\n\nJust prose.\n\n## A\n\ntext\n"
    assert strip_handrolled_toc(text) == text


# ----------------------------------------------------------------------------------------------------------------------
# protect_entities (hide &amp; / &#x..; behind underscore-free sentinels so doxygen doesn't mangle them)
# ----------------------------------------------------------------------------------------------------------------------


def test_protect_entities_replaces_amp_and_hex():
    out = protect_entities('a &amp; b and a heart &#x2764; here')
    assert out == f'a {SENTINEL_AMP} b and a heart {SENTINEL_HEX}2764 here'
    assert '&amp;' not in out and '&#x' not in out


def test_sentinels_are_underscore_free_so_mcss_add_wbr_leaves_them_intact():
    # m.css's add_wbr() injects <wbr/> at '_', '::' and '/'; the sentinels must contain none of those
    for s in (SENTINEL_AMP, SENTINEL_AT, SENTINEL_HEX):
        assert '_' not in s and '::' not in s and '/' not in s


def test_protect_entities_leaves_bare_text_alone():
    text = 'no entities here, just prose & a bare ampersand'
    assert protect_entities(text) == text


def test_restore_fixer_reverses_all_sentinels():
    from poxy.fixers import RestoreMarkdownSentinels

    # &amp; and &#x..; come from protect_entities; the @ sentinel is injected by the changelog path
    protected = protect_entities('a &amp; b, heart &#x2764;') + f' at {SENTINEL_AT} here'
    restored = RestoreMarkdownSentinels()(None, protected, None)  # type: ignore[arg-type]
    assert restored == 'a &amp; b, heart &#x2764; at @ here'
