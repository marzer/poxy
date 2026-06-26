#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Shared helpers for the poxy test suite.

The same run + sanitize + collect logic backs both the pytest snapshot tests
(tests/test_snapshots.py) and the --regenerate path (regenerate_tests.py), so
that a snapshot blessed by one is exactly what the other compares against.
"""

import re
import shutil
from pathlib import Path
from subprocess import CompletedProcess

from misk import *

try:
    import tomllib as toml  # 3.11+ (PEP 680)
except ImportError:
    import tomli as toml  # pyright: ignore[reportMissingImports]  # only installed on <3.11

TESTS_ROOT = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_ROOT.parent
POXY_MAIN = Path(REPO_ROOT, 'src', '__main__.py').resolve()

# files poxy emits that we never snapshot (assets, schemas, the input Doxyfile, etc.)
DEFAULT_GARBAGE = ('*.xslt', '*.xsd', 'favicon*', 'search-v2.js', 'Doxyfile*')


def doxygen_available() -> bool:
    return shutil.which('doxygen') is not None


def run_poxy(dir=None, *args, check=True) -> CompletedProcess:
    if dir is None:
        dir = Path.cwd()
    dir = str(coerce_path(dir).resolve())
    assert_existing_file(POXY_MAIN)
    return run_python_script(POXY_MAIN, *[str(arg) for arg in args if arg is not None], check=check, cwd=dir)


def cfg(config: dict, path, default=None):
    # coerce_collection's static type includes set (not subscriptable); list keeps ordering + indexing
    path = list(coerce_collection(path))
    for key in path[:-1]:
        if not isinstance(config, dict) or key not in config:
            return default
        config = config[key]
    if not isinstance(config, dict) or path[-1] not in config:
        return default
    return config[path[-1]]


def enumerate_test_projects():
    """yields (dir, config) for each test_* project, honouring test.toml 'skip'."""
    for subdir in enumerate_directories(TESTS_ROOT, filter=lambda p: p.name.startswith('test_')):
        config = {}
        config_path = Path(subdir, 'test.toml')
        if config_path.exists():
            config = toml.loads(read_all_text_from_file(config_path))
        if bool(cfg(config, 'skip', False)):
            continue
        yield (subdir, config)


def sanitize(text: str) -> str:
    """strip machine-, version- and run-specific noise so snapshots are portable + deterministic."""
    # asset references -> point at the editable source tree (so the goldens validate against live assets)
    text = text.replace('href="poxy/poxy.css"', 'href="../../../src/poxy/css/poxy.css"')
    text = text.replace('src="poxy/poxy.js"', 'src="../../../src/poxy/js/poxy.js"')
    text = text.replace('src="search-v2.js"', 'src="../../../src/poxy/mcss/documentation/search.js"')
    # poxy + doxygen versions
    text = re.sub(r'Poxy v[0-9]+[.][0-9]+[.][0-9]+', 'Poxy v0.0.0', text)
    text = re.sub(r'version="\s*[0-9]+[.][0-9]+[.][0-9]+\s*"', 'version="0.0.0"', text)
    text = re.sub(r'doxygen_version="[^"]*"', 'doxygen_version="0.0.0"', text)
    # doxygen build id (can carry a trailing '*' for dirty builds, hence [^"]*)
    text = re.sub(r'\s*doxygen_gitid="[^"]*"', '', text)
    # absolute path to the bundled cppreference tagfile (machine-dependent: D:/... vs /home/...)
    text = re.sub(
        r'external="[^"]*cppreference-doxygen-web\.tag\.xml"', 'external="cppreference-doxygen-web.tag.xml"', text
    )
    # doxygen member-anchor and directory ids are version-dependent MD5 hashes (the hashing changed
    # between releases), so poxy cannot reproduce a foreign version's value. normalise each distinct hash
    # to a deterministic placeholder by order of first appearance: pure hash-value differences disappear,
    # but a residual ordering difference still diverges (correctly - that is a real normalisation gap).
    # NB the unused graph subsystem is intended to replace these with poxy's own stable ids eventually.
    hash_ids = {}

    def _hash_placeholder(m) -> str:
        h = m.group(0)
        if h not in hash_ids:
            hash_ids[h] = rf'poxyhash{len(hash_ids)}'
        return hash_ids[h]

    text = re.sub(r'[0-9a-f]{32,}', _hash_placeholder, text)
    return text


def produce_outputs(project_dir, config: dict, work_dir, *extra_args) -> dict:
    """
    run poxy for a single test project and return {kind: {file_name: sanitized_text}} where
    kind is 'html' and/or 'xml' depending on test.toml. poxy is invoked inside work_dir, which
    is populated with a copy of the project inputs so the repo tree is never written to.
    """
    project_dir = coerce_path(project_dir).resolve()
    work_dir = coerce_path(work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    for item in project_dir.iterdir():
        if item.name in ('expected_html', 'expected_xml', 'html', 'xml'):
            continue
        dest = Path(work_dir, item.name)
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    output_html = bool(cfg(config, ('html', 'enabled'), True))
    output_xml = bool(cfg(config, ('xml', 'enabled'), False))
    args = ['--noassets', f'--{"" if output_html else "no-"}html', f'--{"" if output_xml else "no-"}xml', *extra_args]
    if bool(cfg(config, ('xml', 'v2'), False)):
        args.append('--xml-v2')

    run_poxy(work_dir, *args)

    garbage = (*DEFAULT_GARBAGE, *coerce_collection(cfg(config, 'garbage', [])))
    results = {}
    for kind, enabled in (('html', output_html), ('xml', output_xml)):
        if not enabled:
            continue
        out_dir = Path(work_dir, kind)
        for f in enumerate_files(out_dir, any=garbage):
            delete_file(f)
        results[kind] = {
            f.name: sanitize(read_all_text_from_file(f)) for f in enumerate_files(out_dir, any=('*.html', '*.xml'))
        }
    return results
