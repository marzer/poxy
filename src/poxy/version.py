#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

import importlib.metadata
import typing

from . import paths

# prefer the root VERSION file when running from a source tree (incl. editable installs) so the dev always
# sees the live value; fall back to the version stamped into the package metadata for a real wheel install,
# where VERSION lives outside the package and isn't shipped.
_version_file = paths.REPOSITORY / r'VERSION'
if _version_file.is_file():
    VERSION_STRING = _version_file.read_text(encoding='utf-8').strip()
else:
    VERSION_STRING = importlib.metadata.version(r'poxy')

_parts = tuple([int(v.strip()) for v in VERSION_STRING.split('.')])
assert len(_parts) == 3
VERSION = typing.cast(tuple[int, int, int], _parts)

__all__ = [r'VERSION', r'VERSION_STRING']
