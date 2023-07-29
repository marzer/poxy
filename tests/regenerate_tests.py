#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

import re
import sys
from pathlib import Path
from subprocess import CalledProcessError

from utils import *

try:
    import pytomlpp as toml  # fast; based on toml++ (C++)
except ImportError:
    try:
        import tomllib as toml  # PEP 680
    except ImportError:
        import tomli as toml


def _cfg(config, path, default=None):
    assert isinstance(config, dict)
    assert path is not None
    path = coerce_collection(path)
    assert path

    for p in range(len(path) - 1):
        if path[p] not in config:
            return default
        config = config[path[p]]
        assert isinstance(config, dict)

    if path[-1] not in config:
        return default
    return config[path[-1]]


def regenerate_expected_outputs():
    test_root = Path(Path(__file__).parent).resolve()

    for subdir in enumerate_directories(test_root, filter=lambda p: p.name.startswith(r'test_')):
        html_dir = Path(subdir, r'html')
        xml_dir = Path(subdir, r'xml')
        expected_html_dir = Path(subdir, r'expected_html')
        expected_xml_dir = Path(subdir, r'expected_xml')

        # read in test config
        config = {}
        config_path = Path(subdir, r'test.toml')
        if config_path.exists():
            config = toml.loads(read_all_text_from_file(config_path, logger=True))
        if _cfg(config, r'skip', False):
            continue
        output_html = bool(_cfg(config, (r'html', r'enabled'), True))
        output_xml = bool(_cfg(config, (r'xml', r'enabled'), False))
        args = [
            r'--noassets',  #
            rf'--{"no-" if not output_html else ""}html',
            rf'--{"no-" if not output_xml else ""}xml',
            *sys.argv[1:],
        ]
        if bool(_cfg(config, (r'xml', r'v2'), False)):
            args.append(r'--xml-v2')

        # delete all previous outputs
        print(r"Deleting previous artefacts...")
        delete_directory(html_dir, logger=True)
        delete_directory(xml_dir, logger=True)
        delete_directory(expected_html_dir, logger=True)
        delete_directory(expected_xml_dir, logger=True)

        # run poxy
        print(rf"Running Poxy...")
        run_poxy(subdir, *args)

        # delete garbage
        garbage = (
            r'*.xslt',
            r'*.xsd',
            r'favicon*',
            r'search-v2.js',
            r'Doxyfile*',
            *(coerce_collection([r'garbage']) if r'garbage' in config else []),
        )
        garbage = (
            *(enumerate_files(html_dir, any=garbage) if output_html else []),
            *(enumerate_files(xml_dir, any=garbage) if output_xml else []),
        )
        for file in garbage:
            delete_file(file, logger=True)

        # sanitize + fix sources of nondeterminism (so the tests work everywhere)
        print(r"Sanitizing outputs...")
        files = (
            *(enumerate_files(html_dir, any=(r'*.html', r'*.xml')) if output_html else []),
            *(enumerate_files(xml_dir, any=(r'*.html', r'*.xml')) if output_xml else []),
        )
        for path in files:
            text = read_all_text_from_file(path)
            text = text.replace(r'href="poxy/poxy.css"', r'href="../../../src/poxy/css/poxy.css"')
            text = text.replace(r'src="poxy/poxy.js"', r'src="../../../src/poxy/js/poxy.js"')
            text = text.replace(r'src="search-v2.js"', r'src="../../../src/poxy/mcss/documentation/search.js"')
            text = re.sub(r'Poxy v[0-9]+[.][0-9]+[.][0-9]+', r'Poxy v0.0.0', text)
            text = re.sub(r'version="\s*[0-9]+[.][0-9]+[.][0-9]+\s*"', r'version="0.0.0"', text)
            text = re.sub(r'\s*doxygen_gitid="\s*[0-9a-fA-F]+\s*"', r'', text)
            print(rf"Writing {path}")
            with open(path, r'w', encoding=r'utf-8', newline='\n') as f:
                f.write(text)

        # move html files
        if not output_html:
            delete_directory(html_dir, logger=True)
        else:
            html_dir.rename(expected_html_dir)

        # move xml files
        if not output_xml:
            delete_directory(xml_dir, logger=True)
        else:
            xml_dir.rename(expected_xml_dir)


if __name__ == r'__main__':
    with ScopeTimer(r'Regenerating test outputs'):
        try:
            regenerate_expected_outputs()
        except CalledProcessError as err:
            print(rf'Error: {err}', file=sys.stderr)
            sys.exit(1)
