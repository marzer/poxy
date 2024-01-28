#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

"""
Constants for various key paths.
"""

import tempfile
from pathlib import Path

PACKAGE = Path(Path(__file__).resolve().parent)
"""The root directory of the package installation."""

SRC = Path(PACKAGE, r'..').resolve()
"""The root directory of repository's package sources."""

REPOSITORY = Path(SRC, r'..').resolve()
"""The root directory of the repository."""

TESTS = Path(REPOSITORY, r'tests')
"""The root directory of the repository's tests."""

IMG = Path(PACKAGE, r'img')
"""The img directory."""

CSS = Path(PACKAGE, r'css')
"""The css directory."""

JS = Path(PACKAGE, r'js')
"""The js directory."""

MCSS = Path(PACKAGE, r'mcss')
"""The root directory of the bundled m.css build."""

GENERATED = Path(PACKAGE, r'generated')
"""The root directory of all auto-generated package data."""

FONTS = Path(GENERATED, r'fonts')
"""Directory containing all the self-hosted google fonts."""

TEMP = Path(tempfile.gettempdir(), r'poxy')
"""A global temp directory shared by all instances of poxy."""

BUG_REPORT_DIR = (TEMP / r'bug_report').resolve()
"""Directory used for assembling bug reports."""

CASE_SENSITIVE = not (Path(str(PACKAGE).upper()).exists() and Path(str(PACKAGE).lower()).exists())
"""True if the file system is case-sensitive."""
