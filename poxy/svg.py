#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and classes for working with SVG files.
"""

from lxml import etree
from .utils import *



class SVG(object):
	pass

	def __init__(
		self,  #
		file_path: typing.Union[Path, str],
		logger=None,
		root_id: str = None,
		id_namespace: str = None,
		root_classes: typing.Union[str, typing.Sequence[str]] = None
	):

		# read file
		svg = read_all_text_from_file(file_path, logger=logger)

		# add a namespace prefix to the #ids if requested
		# (so they're unique when injected into HTML etc)
		if root_id is not None:
			root_id = str(root_id).strip()
		if id_namespace is not None:
			id_namespace = str(id_namespace).strip()
		if root_id and id_namespace is None:
			id_namespace = root_id
		if id_namespace:
			svg = svg.replace(r'id="', rf'id="{id_namespace}-')
			svg = re.sub(r'''url\s*\(\s*(["']?)\s*#''', rf'url(\1#{id_namespace}-', svg, flags=re.I)
			svg = re.sub(r'''xlink:href\s*=\s*(["'])\s*#''', rf"xlink:href=\1#{id_namespace}-", svg, flags=re.I)

		# parse into XML
		parser = etree.XMLParser(
			remove_blank_text=True,  #
			recover=True,
			remove_comments=True,
			ns_clean=True,
			encoding=r'utf-8'
		)
		self.__xml = etree.fromstring(svg.encode(r'utf-8'), parser=parser)
		attrs = self.__xml.attrib

		# set/normalize various attributes
		if r'xmlns' not in attrs:
			attrs[r'xmlns'] = r'http://www.w3.org/2000/svg'
		# if r'xmlns:xlink' not in attrs:
		#	attrs[r'xmlns:xlink'] = r'http://www.w3.org/1999/xlink')
		if r'version' not in attrs:
			attrs[r'version'] = r'1.1'
		if root_id:
			attrs[r'id'] = root_id

		# some editors use the root attribute to store a bunch of metadata
		# and tracking garbage so delete it
		if r'content' in attrs:
			del attrs[r'content']

		# set class attribute if specified
		if root_classes is not None:
			root_classes = list(coerce_collection(root_classes))
			if root_classes:
				attrs[r'class'] = r' '.join(list(coerce_collection(root_classes)))
			elif r'class' in attrs:
				del attrs[r'class']

	def __str__(self) -> str:
		return etree.tostring(self.__xml, encoding=r'unicode', xml_declaration=False, pretty_print=False)
