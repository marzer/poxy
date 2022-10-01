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
from typing import Union
from io import StringIO



class SVG(object):
	pass

	def __init__(
		self,  #
		file_path: Union[Path, str],
		logger=None,
		id_prefix: str = None,
		root_id: str = None
	):

		# read file
		svg = read_all_text_from_file(file_path, logger=logger)

		# add a prefix to the #ids if requested
		# (so they're unique when injected into HTML etc)
		if id_prefix is not None:
			id_prefix = str(id_prefix)
		if id_prefix:
			svg = svg.replace(r'id="', rf'id="{id_prefix}')
			svg = re.sub(r'url\(\s*"\s*#', rf'url("#{id_prefix}', svg, flags=re.I)
			svg = re.sub(r"url\(\s*'\s*#", rf"url('#{id_prefix}", svg, flags=re.I)
			svg = re.sub(r'url\(\s*#', rf'url(#{id_prefix}', svg, flags=re.I)
			svg = re.sub(r'xlink:href="\s*#', rf'xlink:href="#{id_prefix}', svg, flags=re.I)
			svg = re.sub(r"xlink:href='\s*#", rf"xlink:href='#{id_prefix}", svg, flags=re.I)

		# parse into XML
		parser = etree.XMLParser(
			remove_blank_text=True,  #
			recover=True,
			remove_comments=True,
			ns_clean=True,
			encoding=r'utf-8'
		)
		self.__xml = etree.parse(StringIO(svg), parser=parser)
		root = self.__xml.getroot()
		attrs = root.attrib

		# set root id
		if root_id is not None:
			root_id = str(root_id)
		if root_id:
			attrs[r'id'] = root_id

		# normalize various svg attributes
		if r'xmlns' not in attrs:
			attrs[r'xmlns'] = r'http://www.w3.org/2000/svg'
		# if r'xmlns:xlink' not in attrs:
		#	attrs[r'xmlns:xlink'] = r'http://www.w3.org/1999/xlink')
		if r'version' not in attrs:
			attrs[r'version'] = r'1.1'

	def __str__(self) -> str:
		return etree.tostring(self.__xml.getroot(), encoding=r'unicode', xml_declaration=False, pretty_print=True)
