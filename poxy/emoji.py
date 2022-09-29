#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and classes for working with emoji.
"""

import json
from .utils import *
from . import dirs
from typing import Union, Collection



def update_database_file():
	# get the raw emoji db from github
	EMOJI_URI = r'https://api.github.com/emojis'
	print(rf"Downloading {EMOJI_URI}")
	raw_emoji = json.loads(download_text(EMOJI_URI))

	# convert into our internal Emoji tuple
	emoji = dict()
	RX_GITHUB_EMOJI_URI = re.compile(r".+unicode/([0-9a-f]+(?:-[0-9a-f]+)?)[.]png.*", re.I)
	for key, uri in raw_emoji.items():
		m = RX_GITHUB_EMOJI_URI.fullmatch(uri)
		if m:
			cps = [int(cp, 16) for cp in m[1].split('-')]
			if len(cps) == 1:
				cps = cps[0]
			emoji[key.lower().replace(r'-', r'_')] = (cps, uri)

	# serialize
	path = Path(dirs.GENERATED, r'emoji.json')
	print(rf'Writing {path}')
	with open(path, 'w', encoding='utf-8', newline='\n') as f:
		f.write(json.dumps(emoji, sort_keys=True, indent=4))



class Emoji(object):

	def __init__(self, key: str, codepoints: Union[int, Collection[int]], uri: str):
		self.key = str(key)
		self.codepoints = [int(cp) for cp in coerce_collection(codepoints)]
		self.codepoints.sort()
		self.codepoints = tuple(self.codepoints)
		self.uri = str(uri)

	def __str__(self) -> str:
		s = ''
		for cp in self.codepoints:
			s += rf'&#x{cp:X};'
		return rf'{s}&#xFE0F;'



class Database(object):

	def __init__(self):

		path = Path(dirs.GENERATED, r'emoji.json')
		assert_existing_file(path)
		emoji = json.loads(read_all_text_from_file(path))

		# load by key
		self.__by_key = dict()
		for key, vals in emoji.items():
			self.__by_key[key] = Emoji(key, vals[0], vals[1])

		# load by codepoint
		self.__by_codepoint = dict()
		for key, e in self.__by_key.items():
			if len(e.codepoints) == 1:
				self.__by_codepoint[e.codepoints[0]] = e

		# apply aliases
		ALIASES = (
			('sundae', 'ice_cream'),  #
			('info', 'information_source'),
			('man_in_tuxedo', 'person_in_tuxedo'),
			('bride_with_veil', 'person_with_veil')
		)
		for alias, key in ALIASES:
			if key in self.__by_key and alias not in self.__by_key:
				self.__by_key[alias] = self.__by_key[key]

	def __contains__(self, key: Union[int, str]) -> bool:
		assert key is not None
		if isinstance(key, int):
			return key in self.__by_codepoint
		else:
			return key.lower().replace(r'-', r'_') in self.__by_key

	def __getitem__(self, key: Union[int, str]) -> Emoji:
		assert key is not None
		if isinstance(key, int):
			if key in self.__by_codepoint:
				return self.__by_codepoint[key]
		else:
			key = key.lower().replace(r'-', r'_')
			if key in self.__by_key:
				return self.__by_key[key]
		return None
