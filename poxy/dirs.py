#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Constants for various key directory paths.
"""

import tempfile
from pathlib import Path

PACKAGE = Path(Path(__file__).resolve().parent)
"""The root directory of the package installation."""

DATA = Path(PACKAGE, r'data')
"""The root directory of all package data."""

CSS = Path(DATA, r'css')
"""The css directory."""

MCSS = Path(DATA, r'm.css')
"""The root directory of the bundled m.css build."""

GENERATED = Path(DATA, r'generated')
"""The root directory of all auto-generated package data."""

FONTS = Path(GENERATED, r'fonts')
"""Directory containing all the self-hosted google fonts."""

TESTS = Path(PACKAGE, r'..', r'tests')
"""The root directory of the repository's tests."""

TEMP = Path(tempfile.gettempdir(), r'poxy')
"""A global temp directory shared by all instances of poxy."""
