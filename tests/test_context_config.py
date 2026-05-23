#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Unit tests for Context config parsing (project.Context.__read_config).

These build a Context directly from a rich poxy.toml - no Doxygen, no m.css - and assert the derived
attributes for each config section. They give the per-section config logic real coverage (most of these
sections are not exercised by the end-to-end snapshot projects), protecting it against regressions when
__read_config is refactored.
"""

from pathlib import Path

import pytest

from poxy.project import Context

RICH_TOML = """
name = 'Rich'
author = 'Somebody'
description = 'desc'
cpp = 17
theme = 'light'
github = 'marzer/poxy'
gitlab = 'gl/poxy'
sponsor = 'marzer'
twitter = 'marzer'
navbar = ['files', 'github']
license = ['MIT', 'https://opensource.org/license/mit']
inline_namespaces = ['foo::detail']
excluded_symbols = ['foo::secret']
favicon = 'favicon.png'
logo = 'logo.svg'
stylesheets = ['style.css']
scripts = ['script.js']
extra_files = ['extra/note.txt']
changelog = 'CHANGELOG.md'
main_page = 'readme.md'
robots = false
jquery = true
generate_tagfile = true
internal_docs = true
private_repo = true
dot = true
show_includes = false
html_header = '<meta name="x" content="y">'

[badges]
'X' = ['https://img.shields.io/badge/x-y-blue', 'https://example.com']
[aliases]
'myalias' = 'bar'
[autolinks]
'\\bWidget\\b' = 'https://example.com/widget'
[meta_tags]
'keywords' = 'cpp'
[macros]
'CUSTOM' = 1
[defines]
'LEGACY' = 2
[code_blocks]
types = ['MyType']
macros = ['MY_MACRO']
[tagfiles]
'https://example.com/x.tag.xml' = 'https://example.com/'
[sources]
recursive_paths = ['src']
strip_paths = ['src']
[images]
paths = ['images']
[examples]
paths = ['examples']
"""


@pytest.fixture(scope='module')
def ctx(tmp_path_factory):
    d = tmp_path_factory.mktemp('rich')
    (d / 'src').mkdir()
    (d / 'src' / 'a.hpp').write_text('#pragma once\nnamespace foo { struct widget {}; }\n')
    (d / 'extra').mkdir()
    (d / 'images').mkdir()
    (d / 'images' / 'pic.png').write_bytes(b'x')
    (d / 'examples').mkdir()
    (d / 'examples' / 'ex.cpp').write_text('int main(){}\n')
    for name in ('favicon.png', 'logo.svg', 'style.css', 'script.js'):
        (d / name).write_bytes(b'x')
    (d / 'extra' / 'note.txt').write_bytes(b'x')
    (d / 'CHANGELOG.md').write_text('# Changes\n')
    (d / 'readme.md').write_text('# Home\n')
    (d / 'poxy.toml').write_text(RICH_TOML)
    return Context(
        config_path=d / 'poxy.toml',
        output_dir=d,
        output_html=True,
        output_xml=False,
        threads=1,
        cleanup=False,
        verbose=False,
        logger=None,
        html_include=None,
        html_exclude=None,
        treat_warnings_as_errors=False,
        theme=None,  # take theme from config
        copy_assets=False,
        temp_dir=d / 'temp',
    )


def test_metadata(ctx):
    assert ctx.name == 'Rich'
    assert ctx.author == 'Somebody'
    assert ctx.description == 'desc'


def test_cpp_coerced_to_full_year(ctx):
    assert ctx.cpp == 2017


def test_theme(ctx):
    assert ctx.theme == 'light'


def test_license(ctx):
    assert ctx.license == {'spdx': 'MIT', 'uri': 'https://opensource.org/license/mit'}


def test_inline_namespaces_and_excluded_symbols(ctx):
    assert 'foo::detail' in ctx.inline_namespaces
    assert any('foo::secret' in str(s) for s in ctx.excluded_symbols)


def test_flags(ctx):
    assert ctx.robots is False
    assert ctx.generate_tagfile is True
    assert ctx.internal_docs is True
    assert ctx.private_repo is True
    assert ctx.dot is True
    assert ctx.show_includes is False


def test_html_header(ctx):
    assert ctx.html_header == '<meta name="x" content="y">'


def test_assets_resolved(ctx):
    assert ctx.favicon is not None
    assert ctx.logo is not None
    assert Path(ctx.favicon).name == 'favicon.png'
    assert Path(ctx.logo).name == 'logo.svg'
    assert any(str(s).endswith('style.css') for s in ctx.stylesheets)
    assert any(str(s).endswith('script.js') for s in ctx.scripts)
    assert 'note.txt' in ctx.extra_files
    assert ctx.changelog is not None
    assert ctx.main_page is not None


def test_macros_merge_defines_and_custom(ctx):
    # macro values are stringified for doxygen's PREDEFINED
    assert str(ctx.macros['CUSTOM']) == '1'
    assert str(ctx.macros['LEGACY']) == '2'  # legacy [defines] folded into macros


def test_aliases_include_custom(ctx):
    # regression: user-defined aliases used to be silently dropped (dead code after a raise)
    assert ctx.aliases['myalias'] == 'bar'


def test_autolinks_include_custom(ctx):
    assert any('example.com/widget' in str(v) for _, v in ctx.autolinks)


def test_meta_tags(ctx):
    assert ctx.meta_tags['keywords'] == 'cpp'


def test_navbar_maps_github_to_repo_and_adds_sponsor(ctx):
    assert 'repo' in ctx.navbar
    assert 'sponsor' in ctx.navbar


def test_badges_include_custom(ctx):
    assert any(b[0] == 'X' for b in ctx.badges)


def test_code_blocks_include_custom(ctx):
    assert 'MyType' in ctx.code_blocks.types
    assert 'MY_MACRO' in ctx.code_blocks.macros


def test_images_and_examples_paths(ctx):
    assert any(str(p).endswith('images/pic.png') or str(p).endswith('images') for p in ctx.images.paths)
    assert any('examples' in str(p) for p in ctx.examples.paths)


def test_tagfiles_record_uri_unresolved(ctx):
    assert any('example.com/x.tag.xml' in str(k) for k in ctx.tagfiles)
    assert ctx.unresolved_tagfiles is True
