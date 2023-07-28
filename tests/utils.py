#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

from pathlib import Path
from subprocess import CompletedProcess

from misk import *

_poxy_path = None


def run_poxy(dir=Path.cwd(), *args, check=True) -> CompletedProcess:
    if dir is None:
        dir = Path.cwd()
    dir = str(coerce_path(dir).resolve())

    global _poxy_path
    if _poxy_path is None:
        _poxy_path = str(Path(Path(__file__).parents[1], r'src', r'__main__.py').resolve())
        assert_existing_file(_poxy_path)

    return run_python_script(_poxy_path, *[str(arg) for arg in args if arg is not None], check=check, cwd=dir)
