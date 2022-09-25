#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

from .run import run
from .utils import lib_version, Error, WarningTreatedAsError

__all__ = [r'run', r'lib_version', r'Error', r'WarningTreatedAsError']

__version__ = r'.'.join([str(v) for v in lib_version()])
