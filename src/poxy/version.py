#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/main/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import importlib.metadata
import typing

from . import paths

_version_file = paths.REPOSITORY / r'VERSION'
_in_source_tree = (
    paths.SRC.name == r'src'
    and (paths.REPOSITORY / r'pyproject.toml').is_file()
    and not any(paths.SRC.glob(r'poxy-*.dist-info'))
)
if _in_source_tree and _version_file.is_file():
    VERSION_STRING = _version_file.read_text(encoding='utf-8').strip()
else:
    VERSION_STRING = importlib.metadata.version(r'poxy')

_parts = tuple([int(v.strip()) for v in VERSION_STRING.split('.')])
assert len(_parts) == 3
VERSION = typing.cast(tuple[int, int, int], _parts)

__all__ = [r'VERSION', r'VERSION_STRING']
