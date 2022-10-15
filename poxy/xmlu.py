#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
"XML utilities" - Helpers for working with XML using lxml.

(I wanted to call this module simply "xml" but that breaks BeautifulSoup for some reason)
"""

from lxml import etree
from .utils import *



def create_parser(remove_blank_text=False, **kwargs) -> etree.XMLParser:
	return etree.XMLParser(
		encoding=r'utf-8',  #
		remove_blank_text=remove_blank_text,
		recover=True,
		remove_comments=True,
		remove_pis=True,
		ns_clean=True,
		**kwargs
	)



DEFAULT_PARSER = create_parser()



def make_child(parent, tag_name: str, **attrs):
	assert parent is not None
	assert tag_name is not None
	assert tag_name
	return etree.SubElement(parent, tag_name, attrib=attrs)



def read(source: typing.Union[str, bytes, Path], parser=None, logger=None):
	assert source is not None
	assert source
	assert isinstance(source, (str, bytes, Path))

	if parser is None:
		parser = DEFAULT_PARSER

	if isinstance(source, Path):
		source = read_all_text_from_file(source, logger=logger)
	if isinstance(source, str):
		source = source.encode(r'utf-8')
	return etree.fromstring(source, parser=parser)



ElementTypes = typing.Union[etree.ElementBase, etree._Element, etree._ElementTree]



def write(
	source: typing.Union[str, bytes, ElementTypes],
	dest: Path,
	parser=None,
	logger=None,
	pretty_print=False,
	xml_declaration=True
):
	assert source is not None
	assert isinstance(source, (str, bytes, etree.ElementBase, etree._Element, etree._ElementTree))
	assert dest is not None
	assert dest
	dest = coerce_path(dest)

	if isinstance(source, (str, bytes)):
		source = read(source, parser=parser, logger=logger)

	tree = etree.ElementTree(source)
	tree.write(
		str(dest),  #
		encoding=r'utf-8',
		xml_declaration=xml_declaration,
		pretty_print=pretty_print
	)
