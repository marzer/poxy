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
    label_headings,
    normalize_toc_directives,
    preprocess,
    promote_headings,
    protect_entities,
    setext_to_atx,
    slugify,
    split_heading_label,
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


def test_slugify_reduces_markup_to_bare_anchor():
    assert slugify('Hello, World!') == 'hello_world'
    assert slugify('`code` and **bold**') == 'code_and_bold'
    assert slugify('A [link](https://example.com) here') == 'a_link_here'
    assert slugify('Already {#labelled}') == 'already'


def test_slugify_returns_blank_when_nothing_survives():
    assert slugify('!!!') == ''
    assert slugify('日本語') == ''


def test_setext_headings_become_atx():
    assert setext_to_atx('Title\n=====\n\nBody\n') == '# Title\n\nBody\n'
    assert setext_to_atx('Sub\n---\n') == '## Sub\n'


def test_setext_conversion_ignores_table_separators_and_fenced_code():
    table = '| a | b |\n|---|---|\n| 1 | 2 |\n'
    assert setext_to_atx(table) == table
    fenced = '```\nnot a heading\n=====\n```\n'
    assert setext_to_atx(fenced) == fenced


def test_promote_headings_shifts_every_level_up_by_one():
    assert promote_headings('## A\n### B\n###### F\n') == '# A\n## B\n##### F\n'


def test_promote_headings_leaves_h1_and_fenced_hashes_alone():
    assert promote_headings('# A\n') == '# A\n'
    fenced = '```cpp\n#define FOO 1\n## not a heading\n```\n'
    assert promote_headings(fenced) == fenced


def test_label_headings_derives_slugs_from_text():
    assert label_headings('# Hello World\n') == '# Hello World {#hello_world}\n'


def test_label_headings_dedupes_repeated_titles():
    out = label_headings('# Notes\n\n# Notes\n\n# Notes\n')
    assert out == '# Notes {#notes}\n\n# Notes {#notes_2}\n\n# Notes {#notes_3}\n'


def test_label_headings_is_idempotent_and_respects_explicit_labels():
    once = label_headings('# A {#custom}\n\n# B\n')
    assert once == '# A {#custom}\n\n# B {#b}\n'
    assert label_headings(once) == once


def test_label_headings_avoids_colliding_with_an_explicit_label_declared_later():
    # the explicit '{#a}' below must win, so the derived slug for the first heading has to dodge it
    out = label_headings('# A\n\n# Something {#a}\n')
    assert out == '# A {#a_2}\n\n# Something {#a}\n'


def test_label_headings_falls_back_when_the_title_slugifies_to_nothing():
    assert label_headings('# 日本語\n') == '# 日本語 {#section}\n'


def test_label_headings_namespaces_slugs_by_prefix():
    # doxygen section labels share one global namespace, so two pages both headed 'Overview' would
    # collide: it warns, then m.css dies on an id-prefix assertion and the build fails
    assert label_headings('# Overview\n', 'page_a') == '# Overview {#page_a_overview}\n'
    assert label_headings('# Overview\n', 'page_b') == '# Overview {#page_b_overview}\n'


def test_label_headings_dedupe_still_applies_within_a_prefix():
    out = label_headings('# A\n\n# A\n', 'p')
    assert out == '# A {#p_a}\n\n# A {#p_a_2}\n'


def test_preprocess_keeps_explicit_subheading_labels_verbatim():
    out = preprocess('# Overview\n\n## Details {#the_details}\n\n## More\n', 'notes')
    assert '## Details {#the_details}' in out
    assert '## More {#notes_more}' in out


def test_split_heading_label():
    assert split_heading_label('Details {#the_details}') == ('Details', 'the_details')
    assert split_heading_label('## Details {#the_details}  ') == ('## Details', 'the_details')
    assert split_heading_label('Details') == ('Details', '')
    # a label needs no whitespace in it, so this is prose rather than an anchor
    assert split_heading_label('Details {# not a label}') == ('Details {# not a label}', '')


def test_preprocess_prefixes_from_the_caller():
    assert '{#notes_details}' in preprocess('# Overview\n\n## Details\n', 'notes')


def test_preprocess_leaves_the_page_title_heading_unlabelled():
    # doxygen takes that heading's label as the page id, so labelling it renames the output file
    out = preprocess('# Overview\n\n## Details\n', 'notes')
    assert out.splitlines()[0] == '# Overview'


def test_label_headings_skips_fenced_code():
    fenced = '```\n# not a heading\n```\n'
    assert label_headings(fenced) == fenced


def test_preprocess_labels_headings_before_entities_are_hidden():
    # slugs must come from the real heading text, not from a sentinel
    out = preprocess('# Title\n\n## A &amp; B\n')
    assert '{#a_amp_b}' in out
    assert SENTINEL_AMP not in out[out.index('{#') :]
