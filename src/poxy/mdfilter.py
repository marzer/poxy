#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Standalone markdown input filter, wired into Doxygen via FILTER_PATTERNS so it runs uniformly on every
markdown file Doxygen reads (not just the special main_page/changelog temp copies). Doxygen invokes it as
`<this> <file>` and reads the transformed content from stdout.

Kept dependency-free (stdlib only) and free of any `poxy` package import so it starts fast when spawned
once per file. The pure functions are unit-tested directly, and poxy.dox imports the heading helpers
from here rather than the other way around, so that constraint stays intact.
"""

import os
import re
import sys
import unicodedata

SENTINEL_AMP = r'poxyentityamp'
SENTINEL_AT = r'poxyentityat'
SENTINEL_HEX = r'poxyentityhex'  # immediately followed by the entity's hex digits

_TOC_BULLET = re.compile(r'^[ \t]*[-*+][ \t]+\[[^\]]+\]\(#[^)\s]*\)[ \t]*$')
_TOC_DIRECTIVE = re.compile(r'(?m)^[ \t]*(?:[@\\]tableofcontents\b|\[TOC\][ \t]*$)')

# doxygen omits the <tableofcontents> XML element for the HTML-generator-specific '@tableofcontents{HTML:N}'
# form and for markdown's '[TOC]', so m.css (which works from the XML) renders no TOC nav for those.
_TOC_HTML_LEVEL = re.compile(r'(?m)^([ \t]*)[@\\]tableofcontents\{[^}]*\bHTML:(\d+)[^}]*\}[ \t]*$')
_TOC_MARKDOWN = re.compile(r'(?m)^([ \t]*)\[TOC\][ \t]*$')

_FENCE = re.compile(r'^[ \t]*(?P<marker>`{3,}|~{3,})')
# at most 3 spaces of indent: 4+ is an indented code block, and doxygen renders it as one
_ATX = re.compile(r'^( {0,3})(#{1,6})([ \t].*)$')
_SETEXT = re.compile(r'^[ \t]*(=+|-+)[ \t]*$')
_EXPLICIT_LABEL = re.compile(r'\{#([^}\s]+)\}[ \t]*$')
_MD_LINK = re.compile(r'\[([^\]]*)\]\([^)]*\)')
# deliberately excludes '_': it is not intra-word emphasis, and eating it would mangle the C++
# identifiers that turn up in headings constantly ('my_function' -> 'myfunction')
_MD_MARKUP = re.compile(r'[*`~]+')


def fence_mask(lines) -> list:
    """Per-line flags marking which lines are inside (or delimiting) a fenced code block."""
    mask = []
    fence = None
    for line in lines:
        m = _FENCE.match(line)
        if fence is None:
            mask.append(bool(m))
            if m:
                fence = m[r'marker']
        else:
            mask.append(True)
            if m and m[r'marker'][0] == fence[0] and len(m[r'marker']) >= len(fence):
                fence = None
    return mask


# latin letters NFKD does not decompose, so they would otherwise degrade to a separator
_TRANSLITERATIONS = str.maketrans(
    {
        'ß': r'ss',
        'æ': r'ae',
        'Æ': r'ae',
        'œ': r'oe',
        'Œ': r'oe',
        'ø': r'o',
        'Ø': r'o',
        'đ': r'd',
        'Đ': r'd',
        'ð': r'd',
        'Ð': r'd',
        'ł': r'l',
        'Ł': r'l',
        'þ': r'th',
        'Þ': r'th',
    }
)


# without this 'c++' slugs to 'c', silently merging with a 'c' tag or heading
_LANGUAGE_NAMES = re.compile(r'(?i)\b(c|g)\+\+')


def slugify(text: str) -> str:
    """Reduces text to a bare [a-z0-9_] slug, used for both heading anchors and post ids.

    NFKD-folds first so accented latin degrades to its base letter ('grusse' rather than 'gr_e').
    Returns '' when nothing survives, which callers handle: a wholly non-latin title is legitimate.
    """
    text = _MD_LINK.sub(r'\1', text)
    text = re.sub(r'\{#[^}]*\}', '', text)
    text = _MD_MARKUP.sub('', text)
    text = _LANGUAGE_NAMES.sub(r'\1pp', text)
    text = text.translate(_TRANSLITERATIONS)
    text = unicodedata.normalize(r'NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^a-zA-Z0-9]+', r'_', text.strip().lower())
    return text.strip(r'_')


def split_heading_label(heading: str) -> tuple:
    """Splits a heading's trailing '{#label}' off it, returning (text, label). label is '' if it had none."""
    m = _EXPLICIT_LABEL.search(heading)
    if not m:
        return (heading.strip(), '')
    return (heading[: m.start()].strip(), m[1])


def setext_to_atx(text: str) -> str:
    """Rewrites '===' / '---' underlined headings into their equivalent '#' / '##' form."""
    lines = text.split('\n')
    mask = fence_mask(lines)
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        underlined = (
            i + 1 < len(lines)
            and not mask[i]
            and not mask[i + 1]
            and line.strip()
            and not line.lstrip().startswith(r'#')
            and _SETEXT.fullmatch(lines[i + 1])
        )
        if underlined:
            out.append(rf'{"#" if lines[i + 1].strip()[0] == "=" else "##"} {line.strip()}')
            i += 2
            continue
        out.append(line)
        i += 1
    return '\n'.join(out)


def promote_headings(text: str) -> str:
    """Shifts every heading up so the shallowest becomes '#', preserving the relative nesting.

    Headings inside a '@page' .dox must start at '#'; a leading '##' makes doxygen emit
    "found subsection command outside of section context", which --werror turns into a build failure.
    """
    lines = text.split('\n')
    mask = fence_mask(lines)
    headings = []
    for i, line in enumerate(lines):
        m = None if mask[i] else _ATX.match(line)
        if m:
            headings.append((i, m))
    if not headings:
        return text

    shift = min(len(m[2]) for _, m in headings) - 1
    if shift <= 0:
        return text
    for i, m in headings:
        lines[i] = rf'{m[1]}{m[2][shift:]}{m[3]}'
    return '\n'.join(lines)


def label_headings(text: str, prefix: str = '', *, skip_title: bool = False) -> str:
    """Gives every unlabelled heading an explicit '{#<prefix>_<slug>}' derived from its text.

    Doxygen's fallback 'autotoc_md<N>' anchors come from a counter that is global to the whole run and
    keyed off input processing order, so adding a page silently renumbers the heading anchors of every
    other page in the site. That breaks deep links into them and makes markdown output non-convergent.

    The prefix is not decoration: doxygen section labels share one global namespace, so two pages both
    headed 'Overview' produce "multiple use of section label" and then crash m.css with an id-prefix
    assertion. Callers pass something unique to the page. Already-labelled headings are left alone, so
    this is idempotent.
    """
    lines = text.split('\n')
    mask = fence_mask(lines)
    prefix = slugify(prefix)

    # doxygen takes the opening heading's label as the whole page's id, so labelling it renames the
    # output file. it is the page title rather than a section, so it needs no anchor of its own.
    title_line = -1
    if skip_title:
        for i, line in enumerate(lines):
            if mask[i] or not line.strip():
                continue
            title_line = i if _ATX.match(line) else -1
            break

    used = set()
    for i, line in enumerate(lines):
        if mask[i] or not _ATX.match(line):
            continue
        m = _EXPLICIT_LABEL.search(line)
        if m:
            used.add(m[1])

    for i, line in enumerate(lines):
        if mask[i] or i == title_line:
            continue
        m = _ATX.match(line)
        if not m or _EXPLICIT_LABEL.search(line):
            continue
        base = slugify(m[3]) or r'section'
        base = rf'{prefix}_{base}' if prefix else base
        slug = base
        n = 2
        while slug in used:
            slug = rf'{base}_{n}'
            n += 1
        used.add(slug)
        lines[i] = rf'{line.rstrip()} {{#{slug}}}'
    return '\n'.join(lines)


def normalize_toc_directives(text: str) -> str:
    """Retarget TOC directives doxygen would drop from XML so it emits <tableofcontents> (which m.css needs):
    '@tableofcontents{HTML:N}' -> '@tableofcontents{XML:N}' (doxygen then emits it, pruned to N levels), and
    markdown '[TOC]' -> '@tableofcontents' (full depth)."""
    text = _TOC_HTML_LEVEL.sub(r'\1@tableofcontents{XML:\2}', text)
    text = _TOC_MARKDOWN.sub(r'\1@tableofcontents', text)
    return text


def strip_handrolled_toc(text: str) -> str:
    """Remove a hand-authored bullet-list table of contents - a contiguous run of list items that are each
    nothing but an in-page anchor link - and, if the document then has no TOC directive, insert an
    @tableofcontents where the list was so poxy still renders its styled TOC nav.

    Such lists are common in GitHub READMEs (auto-generated by various editors) but duplicate the TOC poxy
    builds from @tableofcontents, and their GitHub-style slug links do not resolve against doxygen's own
    heading anchors anyway."""
    lines = text.split('\n')

    # find the first maximal run of >= 2 consecutive TOC-bullet lines
    start = end = None
    i = 0
    while i < len(lines):
        if _TOC_BULLET.match(lines[i]):
            j = i
            while j < len(lines) and _TOC_BULLET.match(lines[j]):
                j += 1
            if j - i >= 2:
                start, end = i, j
                break
            i = j
        else:
            i += 1
    if start is None:
        return text

    replacement = []
    if not _TOC_DIRECTIVE.search(text):
        replacement = [r'@tableofcontents']
    out = '\n'.join(lines[:start] + replacement + lines[end:])
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out


def protect_entities(text: str) -> str:
    """Hide HTML entities behind sentinels so doxygen does not mangle them (it otherwise turns a numeric
    character reference like &#x2764; into the literal text &amp;#x2764;). The post-process
    RestoreMarkdownSentinels fixer turns these back into the real entities in the final HTML."""
    text = text.replace(r'&amp;', SENTINEL_AMP)
    text = re.sub(r'&#x([a-fA-F0-9]{2,4});', rf'{SENTINEL_HEX}\1', text)
    return text


def preprocess(text: str, prefix: str = '') -> str:
    # labelling runs before the sentinels go in, so slugs come from the real heading text
    text = label_headings(setext_to_atx(text), prefix, skip_title=True)
    return strip_handrolled_toc(normalize_toc_directives(protect_entities(text)))


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    path = sys.argv[1]
    with open(path, encoding=r'utf-8') as f:
        text = f.read()
    # the basename stem, never the full path: it is project source, so it stays the same wherever the
    # build runs, which the golden tests require
    stem = os.path.splitext(os.path.basename(path))[0]
    sys.stdout.write(preprocess(text, stem))
    return 0


if __name__ == r'__main__':
    sys.exit(main())
