#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and classes for working with m.css.
"""

import shutil

from . import paths
from .utils import *


def update_bundled_install(source_root: Path):
    assert source_root is not None

    source_root = coerce_path(source_root).resolve()
    assert_existing_directory(source_root)
    assert_existing_file(Path(source_root, r'documentation/doxygen.py'))
    if paths.MCSS == source_root:
        raise Exception(r'm.css source path may not be the same as the internal destination.')

    # delete existing m.css
    if paths.MCSS.exists():
        delete_directory(paths.MCSS, logger=True)

    # copy new one
    print(rf'Updating bundled m.css from {source_root}')
    shutil.copytree(
        source_root,
        paths.MCSS,
        symlinks=False,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            r'.git*',  #
            r'.editor*',
            r'.circleci*',
            r'.coverage*',
            r'.istanbul*',
            r'*.idx',
            r'*.pyc',
            r'*.compiled.css',
            r'__pycache__*',
            r'artwork*',
            r'circleci*',
            r'test_doxygen*',
            r'test_python*',
            r'pelican-theme*',
            r'pygments-*.py',
            r'postprocess.sh',
            r'postprocess.py',
            r'm-*dark.css',  # the m.css themes have local copies in data/ for *reasons*
            r'm-*light.css',
        ),
    )

    # delete unwanted files
    # todo: figure how to do this as a filter, instead of copying -> deleting
    for folder in (
        r'artwork',
        r'doc',
        r'documentation/test',
        r'documentation/templates/python',
        r'package',
        r'pelican-theme',
        r'plugins/m/test',
        r'site',
    ):
        delete_directory(Path(paths.MCSS, folder), logger=True)


__all__ = ['update_bundled_install']
