#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Compiles markdown into synthetic doxygen .dox pages.

'@page <id>' in a .dox names the output <id>.html identically on every supported doxygen version,
whereas a page doxygen generates from a markdown file gets an 'md_<mangled source path>' id whose
mangling is both version- and path-dependent. Anything poxy needs a stable URL for goes through here.
"""

import re

from .mdfilter import (
    SENTINEL_AT,
    label_headings,
    promote_headings,
    protect_entities,
    setext_to_atx,
    split_heading_label,
)

__all__ = [r'escape_command_chars', r'markdown_to_dox']

_LEADING_H1 = re.compile(r'\A\s*#(?!#)[ \t]*(?P<text>.*?)[ \t]*(?:\n|\Z)')


def escape_command_chars(text: str) -> str:
    """Hides '@' from doxygen's command parser. Used on titles, which land in '@page <id> <title>'
    where a stray '@ref' or an email address would otherwise be read as markup."""
    return text.replace(r'@', SENTINEL_AT)


def markdown_to_dox(
    body: str, page_id: str, title: str, *, brief: str = '', footer_nav: bool = False, toc: bool = False
) -> str:
    """Wraps markdown in a '///' doxygen comment as a synthetic @page.

    The '///' form (rather than '/** */') is deliberate: a '*/' inside a fenced code block would
    otherwise terminate the comment early and swallow the rest of the post.
    """
    text = body.replace('\r\n', '\n').replace('\r', '\n')
    text = setext_to_atx(text)

    # only strip the leading heading when it is the one the title came from, otherwise a post whose
    # title is set in front matter silently loses its first heading
    title_anchor = ''
    m = _LEADING_H1.match(text)
    if m:
        heading, label = split_heading_label(m[r'text'])
        if heading == title.strip():
            # the heading goes, but '@ref <label>' from elsewhere must still land somewhere
            title_anchor = label
            text = text[m.end() :]

    text = promote_headings(label_headings(text, page_id))
    text = protect_entities(text).strip('\n')

    out = [rf'/// @page {page_id} {escape_command_chars(title)}']
    if brief:
        out.append(rf'/// @brief {escape_command_chars(brief)}')
    # a blank comment line, else doxygen folds the next directive into the brief paragraph
    if brief and (footer_nav or toc):
        out.append(r'///')
    if footer_nav:
        out.append(r'/// @m_footernavigation')
    if toc:
        out.append(r'/// @tableofcontents')
    out.append(r'///')
    if title_anchor:
        out.append(rf'/// @anchor {title_anchor}')
        out.append(r'///')
    out += [rf'/// {line}' if line.strip() else r'///' for line in text.split('\n')]
    return '\n'.join(out) + '\n'
