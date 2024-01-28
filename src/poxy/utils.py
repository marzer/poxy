#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Low-level helper functions and useful bits.
"""

import io
import logging
import re
import sys
import typing  # used transitively
from pathlib import Path  # used transitively

import requests
from misk import *
from trieregex import TrieRegEx

from . import paths  # used transitively

# =======================================================================================================================
# FUNCTIONS
# =======================================================================================================================


def regex_trie(*words) -> str:
    assert words
    assert len(words)
    trie = TrieRegEx(*words)
    return trie.regex()


def regex_or(patterns, pattern_prefix='', pattern_suffix='', flags=0):
    patterns = [str(r) for r in patterns if r is not None and r]
    patterns.sort()
    pattern = ''
    if patterns:
        pattern = '(?:(?:' + ')|(?:'.join(patterns) + '))'
    patterns = re.compile(rf'{pattern_prefix}{pattern}{pattern_suffix}', flags=flags)
    return patterns


def log(logger, msg, level=logging.INFO):
    if logger is None or msg is None:
        return
    if isinstance(logger, bool):
        if logger:
            print(msg, file=sys.stderr if level >= logging.WARNING else sys.stdout, flush=True)
    elif isinstance(logger, logging.Logger):
        logger.log(level, msg)
    elif isinstance(logger, io.IOBase):
        print(msg, file=logger)
    else:
        logger(msg)


def combine_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


RX_IS_URI = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*://.+$')


def is_uri(s):
    global RX_IS_URI
    return RX_IS_URI.fullmatch(str(s)) is not None


def filter_filenames(files, include, exclude):
    if include is not None:
        files = [f for f in files if include.search(f.name)]
    if exclude is not None:
        files = [f for f in files if not exclude.search(f.name)]
    return files


DOWNLOAD_HEADERS = {r'User-Agent': r'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0'}


def download_text(uri: str, timeout=10, encoding='utf-8') -> str:
    assert uri is not None
    global DOWNLOAD_HEADERS
    response = requests.get(str(uri), headers=DOWNLOAD_HEADERS, timeout=timeout, stream=False, allow_redirects=True)
    if encoding is not None:
        response.encoding = encoding
    return response.text


def download_binary(uri: str, timeout=10) -> bytes:
    assert uri is not None
    global DOWNLOAD_HEADERS
    response = requests.get(str(uri), headers=DOWNLOAD_HEADERS, timeout=timeout, stream=False, allow_redirects=True)
    return response.content


def tail(s: str, split: str) -> str:
    assert s is not None
    assert split is not None
    assert split
    idx = s.rfind(split)
    if idx == -1:
        return s
    return s[idx + len(split) :]


def remove_duplicates(vals: list) -> list:
    new_vals = []
    for v in coerce_collection(vals):
        if v not in new_vals:
            new_vals.append(v)
    return new_vals


def temp_dir_name_for(input, path=None):
    out = re.sub(r'''[!@#$%^&*()+={}<>;:'"_\\/\n\t -]+''', r'_', str(input).strip(r'\/'))
    if len(out) > 256:
        out = str(input)
        if not paths.CASE_SENSITIVE:
            out = out.upper()
        out = sha1(out)
    return out


# =======================================================================================================================
# REGEX REPLACER
# =======================================================================================================================


class RegexReplacer(object):
    def __substitute(self, m):
        self.__result = True
        return self.__handler(m, self.__out_data)

    def __init__(self, regex, handler, value):
        self.__handler = handler
        self.__result = False
        self.__out_data = []
        self.__value = regex.sub(lambda m: self.__substitute(m), value)

    def __str__(self):
        return self.__value

    def __bool__(self):
        return self.__result

    def __len__(self):
        return len(self.__out_data)

    def __getitem__(self, index):
        return self.__out_data[index]


# =======================================================================================================================
# Custom exceptions
# =======================================================================================================================


class Error(Exception):
    """Base class for other exceptions."""

    def __init__(self, *message):
        self.__message = r' '.join([str(m) for m in message])
        super().__init__(self.__message)

    def __str__(self):
        return self.__message


class WarningTreatedAsError(Error):
    """Raised when a warning is generated and the user has chosen to treat warnings as errors."""

    pass


# =======================================================================================================================
# Defer (baby's first RAII)
# =======================================================================================================================


class Defer(object):
    def __init__(self, callable, *args, **kwargs):
        self.__callable = callable
        self.__args = args
        self.__kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.__callable is not None:
            self.__callable(*self.__args, **self.__kwargs)
