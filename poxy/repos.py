#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and classes for working with various source control repositories.
"""

import re
from .utils import *
from typing import Tuple

RX_REPO_PAIR = re.compile(r"""\s*([a-zA-Z0-9_+-]+)\s*[/\\:,;|]\s*([a-zA-Z0-9_+-]+)\s*""")



def extract_user_and_repo(s) -> Tuple[str, str]:
	assert s is not None
	s = str(s)
	global RX_REPO_PAIR
	m = RX_REPO_PAIR.fullmatch(s)
	if not m:
		raise Error(rf'could not extract user-repository pair from "{s}"')
	return (m[1], m[2])



# =======================================================================================================================
# GitHub
# =======================================================================================================================



class GitHub(object):

	KEY = r'github'

	def __init__(self, user_and_repo: str):
		urp = extract_user_and_repo(user_and_repo)
		self.user = urp[0]
		self.repository = urp[1]
		self.uri = rf'https://github.com/{self.user}/{self.repository}'
		self.issues_uri = rf'{self.uri}/issues'
		self.pull_requests_uri = rf'{self.uri}/pulls'
		self.releases_uri = rf'{self.uri}/releases'
		self.release_badge_uri = rf'https://img.shields.io/github/v/release/{self.user}/{self.repository}?style=flat-square',
		self.icon_filename = rf'poxy-icon-{GitHub.KEY}.svg'

	def __bool__(self) -> bool:
		return True

	def __str__(self) -> str:
		return rf'{self.user}/{self.repository}'

	def make_user_uri(self, username) -> str:
		assert username is not None
		return rf'https://github.com/{str(username).strip()}'

	def make_issue_uri(self, key) -> str:
		assert key is not None
		return rf'{self.issues_uri}/{str(key).strip()}'

	def make_pull_request_uri(self, key) -> str:
		assert key is not None
		return rf'{self.pull_requests_uri}/{str(key).strip()}'



# =======================================================================================================================
# GitLab
# =======================================================================================================================



class GitLab(object):

	KEY = r'gitlab'

	def __init__(self, user_and_repo: str):
		urp = extract_user_and_repo(user_and_repo)
		self.user = urp[0]
		self.repository = urp[1]
		self.uri = rf'https://gitlab.com/{self.user}/{self.repository}'
		self.issues_uri = rf'{self.uri}/-/issues'
		self.pull_requests_uri = rf'{self.uri}/-/merge_requests'
		self.releases_uri = rf'{self.uri}/-/releases'
		self.release_badge_uri = None  # todo
		self.icon_filename = rf'poxy-icon-{GitLab.KEY}.svg'

	def __bool__(self) -> bool:
		return True

	def __str__(self) -> str:
		return rf'{self.user}/{self.repository}'

	def make_user_uri(self, username) -> str:
		assert username is not None
		return rf'https://gitlab.com/{str(username).strip()}'

	def make_issue_uri(self, key) -> str:
		assert key is not None
		return rf'{self.issues_uri}/{str(key).strip()}'

	def make_pull_request_uri(self, key) -> str:
		assert key is not None
		return rf'{self.pull_requests_uri}/{str(key).strip()}'



# =======================================================================================================================
# all repo types
# =======================================================================================================================

TYPES = (GitHub, GitLab)
KEYS = tuple([t.KEY for t in TYPES])
