#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Helpers for working with HTML using BeautifulSoup.
"""

import typing
from typing import Union

import bs4

# the bs4 package stubs don't re-export these, so import from their defining module
from bs4.element import AttributeValueList, NavigableString, Tag

from .utils import *

# a bs4 node as yielded by find()/children (a string or an element, never None)
Node = Union[Tag, NavigableString]

# =======================================================================================================================
# BS4 HELPER FUNCTIONS
# =======================================================================================================================


def find_parent(tag: Node, names, cutoff=None) -> typing.Optional[Tag]:
    if not is_collection(names):
        names = (names,)
    parent = tag.parent
    while parent is not None:
        if cutoff is not None and parent is cutoff:
            return None
        if parent.name in names:
            return parent
        parent = parent.parent
    return parent


def destroy_node(node: Node):
    assert node is not None
    if isinstance(node, NavigableString):
        node.extract()
    else:
        node.decompose()


def replace_tag(tag: Node, new_tag_str) -> list:
    assert tag.parent is not None
    newTags = []
    if new_tag_str:
        doc = bs4.BeautifulSoup(new_tag_str, 'html5lib')
        if doc.body is not None and len(doc.body.contents) > 0:
            newTags = [f for f in doc.body.contents]
            newTags = [f.extract() for f in newTags]
            prev = tag
            for newTag in newTags:
                prev.insert_after(newTag)
                prev = newTag
    destroy_node(tag)
    return newTags


def shallow_search(starting_tag: Node, names, filter=None):
    if isinstance(starting_tag, NavigableString):
        return []

    if not is_collection(names):
        names = (names,)

    if starting_tag.name in names:
        if filter is None or filter(starting_tag):
            return [starting_tag]

    results = []
    for tag in starting_tag.children:
        if not isinstance(tag, Tag):
            continue
        if tag.name in names:
            if filter is None or filter(tag):
                results.append(tag)
        else:
            results = results + shallow_search(tag, names, filter)
    return results


def string_descendants(starting_tag: Node, filter=None):
    # a string has no tag-children to recurse into; terminal either way
    if isinstance(starting_tag, NavigableString):
        return [starting_tag] if (filter is None or filter(starting_tag)) else []

    results = []
    for tag in starting_tag.children:
        if isinstance(tag, NavigableString):
            if filter is None or filter(tag):
                results.append(tag)
        elif isinstance(tag, Tag):
            results = results + string_descendants(tag, filter)
    return results


def add_class(tag: Tag, classes) -> bool:
    assert tag is not None
    appended = False
    existing = get_classes(tag)
    if not is_collection(classes):
        classes = (classes,)
    for class_ in classes:
        if class_ not in existing:
            existing.append(class_)
            appended = True
    tag['class'] = AttributeValueList(existing)
    return appended


def remove_class(tag: Tag, classes) -> bool:
    assert tag is not None
    removed = False
    if 'class' in tag.attrs:
        existing = get_classes(tag)
        if not is_collection(classes):
            classes = (classes,)
        for class_ in classes:
            if class_ in existing:
                existing.remove(class_)
                removed = True
        if removed:
            if existing:
                tag['class'] = AttributeValueList(existing)
            else:
                del tag['class']
    return removed


def set_class(tag: Tag, classes):
    assert tag is not None
    if 'class' in tag.attrs:
        del tag['class']
    add_class(tag, classes)


def get_classes(tag: Tag) -> list[str]:
    assert tag is not None
    if 'class' not in tag.attrs:
        return []
    classes = tag['class']
    if not is_collection(classes):
        classes = [classes]
    return [str(c) for c in classes]


def has_any_classes(tag: Tag, *classes) -> bool:
    assert tag is not None
    if 'class' not in tag.attrs:
        return False
    has = get_classes(tag)
    for cls in classes:
        if cls in has:
            return True
    return False


# =======================================================================================================================
# HTML DOCUMENT
# =======================================================================================================================


class HTMLDocument:
    def __init__(self, source: Union[str, Path], logger):
        self.__logger = logger

        assert source is not None
        if isinstance(source, Path):
            with open(str(source), encoding='utf-8') as f:
                self.__doc = bs4.BeautifulSoup(f, 'html5lib', from_encoding='utf-8')
        else:
            self.__doc = bs4.BeautifulSoup(source, 'html5lib')

        self.html = self.__doc.html
        self.head = self.__doc.head
        self.body = self.__doc.body

        self.article = None
        self.article_content = None
        try:
            # dynamic bs4 child navigation, deliberately guarded by the surrounding try/except
            self.article = self.__doc.body.main.article  # type: ignore[union-attr]
            self.article_content = self.article.div.div.div  # type: ignore[union-attr]
        except Exception:
            pass

        self.table_of_contents = None
        self.sections = None
        if self.article_content is not None:
            for toc_tag in ('nav', 'div'):
                for tag in self.article_content(toc_tag, class_='m-block m-default', recursive=False):
                    if not isinstance(tag, Tag):
                        continue
                    h3 = tag.h3
                    if h3 is not None and h3.string == 'Contents':
                        self.table_of_contents = tag
                        break
                if self.table_of_contents is not None:
                    break
            self.sections = self.article_content('section', recursive=False)

    def smooth(self):
        self.__doc.smooth()

    def write(self, path):
        log(self.__logger, rf'Writing {path}')
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(str(self.__doc))

    def __str__(self) -> str:
        return str(self.__doc)

    def new_tag(self, tag_name, parent=None, string=None, class_=None, index=None, before=None, after=None, **kwargs):
        tag = self.__doc.new_tag(tag_name, **kwargs)
        if string is not None:
            if tag.string is not None:
                # stubs type Tag.string as str, but it is really a NavigableString at runtime
                typing.cast(NavigableString, tag.string).replace_with(string)
            else:
                tag.string = NavigableString(string)
        if class_ is not None:
            tag['class'] = class_
        if before is not None:
            before.insert_before(tag)
        elif after is not None:
            after.insert_after(tag)
        elif parent is not None:
            if index is None or index < 0:
                parent.append(tag)
            else:
                parent.insert(index, tag)

        return tag

    def find_all_from_sections(self, name=None, select=None, section=None, include_toc=False, **kwargs):
        tags = []
        if self.article_content is not None:
            if section is not None:
                sections = self.article_content('section', recursive=False, id='section')
            else:
                sections = self.sections
            sections = list(sections) if sections is not None else []
            if include_toc and self.table_of_contents is not None:
                sections = [self.table_of_contents, *sections]
            for sect in sections:
                if not isinstance(sect, Tag):
                    continue
                matches = sect(name, **kwargs) if name is not None else [sect]
                if select is not None:
                    newMatches = []
                    for match in matches:
                        if isinstance(match, Tag):
                            newMatches += match.select(select)
                    matches = newMatches
                tags += matches
        return tags
