#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Fast, deterministic unit tests for poxy's pure helpers. These need neither doxygen nor network
access, so they run in the full python matrix as the project's primary safety net.
"""

import re
from pathlib import Path

import bs4
import pytest
from bs4.element import Tag

from poxy import config, doxygen, schemas, soup, utils
from poxy.version import VERSION, VERSION_STRING

# ----------------------------------------------------------------------------------------------------------------------
# utils
# ----------------------------------------------------------------------------------------------------------------------


def test_regex_or_matches_any_alternative():
    rx = utils.regex_or(('foo', 'bar'))
    assert rx.search('xxfooxx')
    assert rx.search('--bar--')
    assert not rx.search('baz')


def test_regex_or_empty_input_matches_nothing_meaningful():
    rx = utils.regex_or([])
    assert rx.pattern == ''


def test_regex_or_applies_prefix_suffix_and_flags():
    rx = utils.regex_or(('foo',), pattern_prefix='^', pattern_suffix='$', flags=re.IGNORECASE)
    assert rx.fullmatch('FOO')
    assert not rx.search('a foo b')


def test_regex_trie_matches_inputs():
    rx = re.compile(utils.regex_trie('apple', 'apply', 'apt'))
    for word in ('apple', 'apply', 'apt'):
        assert rx.fullmatch(word), word
    assert not rx.fullmatch('ap')


def test_combine_dicts_is_nondestructive_and_right_biased():
    x = {'a': 1, 'b': 2}
    y = {'b': 3, 'c': 4}
    z = utils.combine_dicts(x, y)
    assert z == {'a': 1, 'b': 3, 'c': 4}
    assert x == {'a': 1, 'b': 2}  # original untouched


@pytest.mark.parametrize(
    'value,expected',
    [
        ('https://example.com/x', True),
        ('http://a.b', True),
        ('file:///tmp/x', True),
        ('ftp://host/path', True),
        ('/home/user/file', False),
        ('C:/Windows/x', False),
        ('relative/path', False),
        ('', False),
    ],
)
def test_is_uri(value, expected):
    assert utils.is_uri(value) is expected


@pytest.mark.parametrize(
    'value,expected',
    [
        ('github://owner/repo/file.tagfile.xml', True),
        ('github://owner/repo/sub/dir/file.xml', True),
        ('github://owner/repo/file.xml@gh-pages', True),
        ('https://example.com/x.tagfile.xml', False),  # plain https is not a github:// source
        ('github://owner/repo', False),  # missing path
        ('github://owner', False),
        ('', False),
    ],
)
def test_is_github_uri(value, expected):
    assert utils.is_github_uri(value) is expected


@pytest.mark.parametrize(
    'value,owner,repo,path,ref',
    [
        ('github://o/r/a.xml', 'o', 'r', 'a.xml', None),
        ('github://o/r/sub/a.xml', 'o', 'r', 'sub/a.xml', None),
        ('github://o/r/a.xml@gh-pages', 'o', 'r', 'a.xml', 'gh-pages'),
        ('github://o/r/sub/a.xml@main', 'o', 'r', 'sub/a.xml', 'main'),
        ('github://o/r/a.xml@release', 'o', 'r', 'a.xml', 'release'),
        ('github://o/r/a.xml@release:v1.2.3', 'o', 'r', 'a.xml', 'release:v1.2.3'),
    ],
)
def test_github_tagfile_uri_groups(value, owner, repo, path, ref):
    m = utils.GITHUB_TAGFILE_URI.fullmatch(value)
    assert m is not None
    assert (m.group('owner'), m.group('repo'), m.group('path'), m.group('ref')) == (owner, repo, path, ref)


def test_github_token_prefers_env(monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'tok-from-gh-token')
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    assert utils.github_token() == 'tok-from-gh-token'


def test_github_token_falls_back_to_github_token_env(monkeypatch):
    monkeypatch.delenv('GH_TOKEN', raising=False)
    monkeypatch.setenv('GITHUB_TOKEN', 'tok-from-github-token')
    assert utils.github_token() == 'tok-from-github-token'


def test_path_exists_false_on_overlong_component(tmp_path):
    # a path component longer than the filesystem limit (255 bytes) makes stat() raise ENAMETOOLONG;
    # path_exists must treat that as absent rather than propagating the OSError (marzer/poxy#21)
    overlong = tmp_path / (('a' * 300) + '.xml')
    assert utils.path_exists(overlong) is False


def test_path_exists_true_for_real_file(tmp_path):
    f = tmp_path / 'real.xml'
    f.write_text('x')
    assert utils.path_exists(f) is True


def test_ai_instruction_files_are_excluded_by_name():
    # auto-ignored so they aren't scanned as documentation pages (they choke doxygen with '@'-prefixed words)
    from poxy.pipeline.doxyfile import AI_INSTRUCTION_FILES

    for name in ('AGENTS.md', 'CLAUDE.md', 'BUGBOT.md'):
        assert name in AI_INSTRUCTION_FILES
    # rendered as path-anchored globs so they match wherever doxygen finds them in the input tree
    patterns = [rf'*/{name}' for name in AI_INSTRUCTION_FILES]
    assert '*/CLAUDE.md' in patterns


@pytest.mark.parametrize(
    'text,split,expected',
    [
        ('a::b::c', '::', 'c'),
        ('std::vector', '::', 'vector'),
        ('noseparator', '::', 'noseparator'),
        ('trailing::', '::', ''),
    ],
)
def test_tail(text, split, expected):
    assert utils.tail(text, split) == expected


def test_remove_duplicates_preserves_first_seen_order():
    assert utils.remove_duplicates([3, 1, 3, 2, 1, 3]) == [3, 1, 2]


def test_temp_dir_name_sanitizes_punctuation():
    out = utils.temp_dir_name_for('My Project: v1.0/foo')
    assert re.fullmatch(r'[A-Za-z0-9._]+', out), out
    assert ' ' not in out and ':' not in out and '/' not in out


def test_temp_dir_name_hashes_overly_long_input():
    out = utils.temp_dir_name_for('x' * 500)
    assert len(out) < 256


def test_regex_replacer_collects_groups_and_reports_match():
    rx = re.compile(r'<(\w+)>')
    rep = utils.RegexReplacer(rx, lambda m, data: (data.append(m[1]), '[' + m[1] + ']')[1], 'a <b> c <d>')
    assert bool(rep) is True
    assert str(rep) == 'a [b] c [d]'
    assert len(rep) == 2
    assert rep[0] == 'b' and rep[1] == 'd'


def test_regex_replacer_reports_no_match():
    rx = re.compile(r'<(\w+)>')
    rep = utils.RegexReplacer(rx, lambda m, data: m[0], 'nothing here')
    assert bool(rep) is False
    assert str(rep) == 'nothing here'


def test_defer_runs_callable_on_exit():
    calls = []
    with utils.Defer(calls.append, 'done'):
        assert calls == []
    assert calls == ['done']


def test_error_joins_message_parts():
    assert str(utils.Error('a', 'b', 'c')) == 'a b c'


# ----------------------------------------------------------------------------------------------------------------------
# soup (bs4 helpers)
# ----------------------------------------------------------------------------------------------------------------------


def _soup(html: str) -> bs4.BeautifulSoup:
    return bs4.BeautifulSoup(html, 'html.parser')


def test_class_helpers_roundtrip():
    tag = _soup('<div></div>').div
    assert isinstance(tag, Tag)
    assert soup.get_classes(tag) == []
    assert soup.add_class(tag, 'a') is True
    assert soup.add_class(tag, 'a') is False  # already present
    soup.add_class(tag, ('b', 'c'))
    assert soup.get_classes(tag) == ['a', 'b', 'c']
    assert soup.has_any_classes(tag, 'x', 'b') is True
    assert soup.has_any_classes(tag, 'x', 'y') is False
    assert soup.remove_class(tag, 'b') is True
    assert soup.get_classes(tag) == ['a', 'c']
    soup.set_class(tag, 'only')
    assert soup.get_classes(tag) == ['only']


def test_remove_last_class_drops_attribute():
    tag = _soup('<div class="a"></div>').div
    assert isinstance(tag, Tag)
    soup.remove_class(tag, 'a')
    assert 'class' not in tag.attrs


def test_find_parent_by_name_and_cutoff():
    doc = _soup('<section><div><span><em>x</em></span></div></section>')
    em = doc.em
    section = doc.section
    div = doc.div
    assert isinstance(em, Tag)
    assert soup.find_parent(em, 'div') is div
    assert soup.find_parent(em, ('section',)) is section
    assert soup.find_parent(em, 'section', cutoff=div) is None
    assert soup.find_parent(em, 'table') is None


def test_shallow_search_does_not_descend_into_matches():
    doc = _soup('<div><p>1</p><div><p>2</p></div></div>')
    outer = doc.div
    assert isinstance(outer, Tag)
    # outer itself is a div and matches first, so search returns just it
    assert soup.shallow_search(outer, 'div') == [outer]
    ps = soup.shallow_search(outer, 'p')
    assert [p.get_text() for p in ps] == ['1', '2']


# ----------------------------------------------------------------------------------------------------------------------
# schemas
# ----------------------------------------------------------------------------------------------------------------------


def test_value_or_array_coerces_scalar_to_list():
    s = schemas.Schema(schemas.ValueOrArray(str))
    assert s.validate('x') == ['x']
    assert s.validate(['x', 'y']) == ['x', 'y']


def test_value_or_array_enforces_fixed_length():
    s = schemas.Schema(schemas.ValueOrArray(int, length=2))
    assert s.validate([1, 2]) == [1, 2]
    with pytest.raises(schemas.SchemaError):
        s.validate([1, 2, 3])


def test_fixed_array_of_rejects_wrong_length():
    s = schemas.Schema(schemas.FixedArrayOf(int, 3))
    assert s.validate([1, 2, 3]) == [1, 2, 3]
    with pytest.raises(schemas.SchemaError):
        s.validate([1, 2])


def test_stripped_trims_and_can_reject_empty():
    assert schemas.Schema(schemas.Stripped(str)).validate('  hi  ') == 'hi'
    with pytest.raises(schemas.SchemaError):
        schemas.Schema(schemas.Stripped(str, allow_empty=False)).validate('   ')


def test_schema_context_stack():
    assert schemas.current_schema_context() == ''
    with schemas.SchemaContext('outer'):
        with schemas.SchemaContext('inner'):
            assert schemas.current_schema_context() == 'outer: inner: '
    assert schemas.current_schema_context() == ''


# ----------------------------------------------------------------------------------------------------------------------
# version
# ----------------------------------------------------------------------------------------------------------------------


def test_version_is_three_part_tuple_matching_string():
    assert isinstance(VERSION, tuple)
    assert len(VERSION) == 3
    assert all(isinstance(v, int) for v in VERSION)
    assert VERSION_STRING == '.'.join(str(v) for v in VERSION)


def test_version_file_on_disk_is_a_clean_triplet():
    # the wheel build (setuptools file=) and the release tag (v$version) read this file raw, so it must be
    # exactly a 3-part numeric semver - no comment header, no extra lines, no pre-release suffix.
    # locate it relative to this test (the repo checkout), not via paths.REPOSITORY, which points into
    # site-packages when poxy is installed non-editable (as the unit CI job does)
    raw = (Path(__file__).parents[1] / r'VERSION').read_text(encoding='utf-8')
    stripped = raw.strip()
    assert '\n' not in stripped
    parts = stripped.split('.')
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
    assert stripped == VERSION_STRING


# ----------------------------------------------------------------------------------------------------------------------
# config.Inputs (regression: the 'ignore' key used to be silently dropped, so it filtered nothing)
# ----------------------------------------------------------------------------------------------------------------------


def test_inputs_ignore_excludes_matching_paths(tmp_path):
    (tmp_path / 'keep.hpp').write_text('', encoding='utf-8')
    (tmp_path / 'dropme_xyz.hpp').write_text('', encoding='utf-8')
    inputs = config.Inputs(
        {'src': {'paths': ['keep.hpp', 'dropme_xyz.hpp'], 'ignore': ['dropme_xyz']}}, 'src', tmp_path
    )
    names = {p.name for p in inputs.paths}
    assert 'keep.hpp' in names
    assert 'dropme_xyz.hpp' not in names


def test_inputs_without_ignore_keeps_all_paths(tmp_path):
    (tmp_path / 'keep.hpp').write_text('', encoding='utf-8')
    (tmp_path / 'dropme_xyz.hpp').write_text('', encoding='utf-8')
    inputs = config.Inputs({'src': {'paths': ['keep.hpp', 'dropme_xyz.hpp']}}, 'src', tmp_path)
    names = {p.name for p in inputs.paths}
    assert names == {'keep.hpp', 'dropme_xyz.hpp'}


# ----------------------------------------------------------------------------------------------------------------------
# doxygen version policy + capabilities
# ----------------------------------------------------------------------------------------------------------------------


class _WarningSink:
    def __init__(self):
        self.warnings = []

    def warning(self, msg, indent=None):
        self.warnings.append(msg)


def test_check_supported_rejects_too_old(monkeypatch):
    monkeypatch.setattr(doxygen, 'version', lambda: (1, 8, 0))
    monkeypatch.setattr(doxygen, 'raw_version_string', lambda: '1.8.0')
    with pytest.raises(utils.Error):
        doxygen.check_supported(_WarningSink())


def test_check_supported_warns_on_untested_new(monkeypatch):
    newer = (
        doxygen.HIGHEST_TESTED_VERSION[0],
        doxygen.HIGHEST_TESTED_VERSION[1],
        doxygen.HIGHEST_TESTED_VERSION[2] + 1,
    )
    monkeypatch.setattr(doxygen, 'version', lambda: newer)
    sink = _WarningSink()
    doxygen.check_supported(sink)
    assert len(sink.warnings) == 1


def test_check_supported_silent_within_range(monkeypatch):
    monkeypatch.setattr(doxygen, 'version', lambda: doxygen.REFERENCE_VERSION)
    sink = _WarningSink()
    doxygen.check_supported(sink)
    assert sink.warnings == []


def test_has_unresolved_member_references_boundary(monkeypatch):
    monkeypatch.setattr(doxygen, 'version', lambda: (1, 9, 6))
    assert doxygen.has_unresolved_member_references() is False
    monkeypatch.setattr(doxygen, 'version', lambda: (1, 9, 7))
    assert doxygen.has_unresolved_member_references() is True


# ----------------------------------------------------------------------------------------------------------------------
# tagfile normalisation (version-independence)
# ----------------------------------------------------------------------------------------------------------------------


def test_collect_namespace_member_keys_maps_ids_to_anchors(tmp_path):
    from poxy.pipeline.xml import collect_namespace_member_keys

    (tmp_path / 'namespacetest.xml').write_text(
        '<doxygen>'
        '<compounddef kind="namespace"><compoundname>test</compoundname>'
        '<sectiondef><memberdef kind="enum" id="code_8h_1aDEAD"><name>e</name></memberdef></sectiondef>'
        '</compounddef>'
        '<compounddef kind="file"><compoundname>code.h</compoundname>'
        '<sectiondef><memberdef kind="define" id="code_8h_1aBEEF"><name>M</name></memberdef></sectiondef>'
        '</compounddef>'
        '</doxygen>',
        encoding='utf-8',
    )
    # index.xml is skipped, and only namespace members count (the file-scoped #define must not appear)
    (tmp_path / 'index.xml').write_text('<doxygenindex></doxygenindex>', encoding='utf-8')

    assert collect_namespace_member_keys(tmp_path) == {('code_8h.html', 'aDEAD')}


def test_normalize_tagfile_strips_leaked_namespace_members_from_file_compound():
    from poxy import xml_utils
    from poxy.pipeline.xml import normalize_tagfile

    # mimics older doxygen duplicating a namespace enum into the owning file compound while emitting no
    # namespace compound of its own (e.g. an undocumented namespace); the genuine #define must survive
    root = xml_utils.read(
        '<tagfile>'
        '<compound kind="file"><name>code.h</name><filename>code_8h.html</filename>'
        '<member kind="define"><name>M</name><anchorfile>code_8h.html</anchorfile><anchor>aBEEF</anchor></member>'
        '<member kind="enumeration"><name>e</name><anchorfile>code_8h.html</anchorfile><anchor>aDEAD</anchor></member>'
        '</compound>'
        '</tagfile>'
    )

    changed = normalize_tagfile(root, {('code_8h.html', 'aDEAD')})

    assert changed is True
    file_compound = root.find('compound')
    assert file_compound is not None
    members = file_compound.findall('member')
    assert [m.get('kind') for m in members] == ['define']
    assert members[0].findtext('anchor') == 'aBEEF'


# ----------------------------------------------------------------------------------------------------------------------
# define ref resolution (macros referenced from pages, issue #42)
# ----------------------------------------------------------------------------------------------------------------------


def _define_xml(body: str):
    from poxy import xml_utils

    return xml_utils.read(
        f'<doxygen><compounddef kind="page"><detaileddescription>{body}</detaileddescription></compounddef></doxygen>'
    )


def test_collect_defines_maps_names_to_memberdef_ids():
    from poxy import xml_utils
    from poxy.pipeline.xml import collect_defines

    root = xml_utils.read(
        '<doxygen><compounddef kind="file">'
        '<sectiondef>'
        '<memberdef kind="define" id="code_8h_1aBEEF"><name>M</name></memberdef>'
        '<memberdef kind="define" id="group__g_1aF00D"><name>GROUPED</name></memberdef>'
        '<memberdef kind="enum" id="code_8h_1aDEAD"><name>e</name></memberdef>'
        '<memberdef kind="define" id="badid"><name>NO_ANCHOR</name></memberdef>'
        '</sectiondef>'
        '</compounddef></doxygen>'
    )
    assert collect_defines(root) == {'M': 'code_8h_1aBEEF', 'GROUPED': 'group__g_1aF00D'}


def test_collect_defines_picks_smallest_refid_for_duplicate_names():
    from poxy import xml_utils
    from poxy.pipeline.xml import collect_defines

    a = xml_utils.read('<doxygen><memberdef kind="define" id="b_8h_1a2"><name>M</name></memberdef></doxygen>')
    b = xml_utils.read('<doxygen><memberdef kind="define" id="a_8h_1a1"><name>M</name></memberdef></doxygen>')
    defines = collect_defines(a)
    assert collect_defines(b, defines) == {'M': 'a_8h_1a1'}
    # merge order must not matter
    defines = collect_defines(b)
    assert collect_defines(a, defines) == {'M': 'a_8h_1a1'}


def test_resolve_define_refs_replaces_explicit_link_text():
    from lxml import etree

    from poxy import xml_utils
    from poxy.pipeline.xml import resolve_define_refs_in_tree

    root = _define_xml('<para>Use #M and #M_XL, but not #OTHER or x#M or ##M or #M_XLS.</para>')
    changed = resolve_define_refs_in_tree(root, {'M': 'a_8h_1a1', 'M_XL': 'a_8h_1a2'})

    assert changed is True
    para = etree.tostring(xml_utils.require(root.find('.//para')), encoding='unicode')
    assert para == (
        '<para>Use <ref refid="a_8h_1a1" kindref="member">M</ref>'
        ' and <ref refid="a_8h_1a2" kindref="member">M_XL</ref>,'
        ' but not #OTHER or x#M or ##M or #M_XLS.</para>'
    )


def test_resolve_define_refs_handles_leading_trailing_and_nested_positions():
    from lxml import etree

    from poxy.pipeline.xml import resolve_define_refs_in_tree

    root = _define_xml(
        '<para>#M</para><para><itemizedlist><listitem><para>in a bullet: #M</para></listitem></itemizedlist></para>'
    )
    assert resolve_define_refs_in_tree(root, {'M': 'a_8h_1a1'}) is True
    paras = [etree.tostring(p, encoding='unicode') for p in root.iter('para')]
    assert paras[0] == '<para><ref refid="a_8h_1a1" kindref="member">M</ref></para>'
    assert paras[-1] == '<para>in a bullet: <ref refid="a_8h_1a1" kindref="member">M</ref></para>'


def test_resolve_define_refs_skips_code_and_link_contexts_but_not_their_tails():
    from lxml import etree

    from poxy.pipeline.xml import resolve_define_refs_in_tree

    root = _define_xml(
        '<para><computeroutput>#M</computeroutput> tail #M</para>'
        '<para><programlisting><codeline><highlight>#M</highlight></codeline></programlisting></para>'
        '<para><ulink url="https://example.com">#M</ulink></para>'
        '<para><ref refid="a_8h_1a1" kindref="member">#M</ref></para>'
    )
    assert resolve_define_refs_in_tree(root, {'M': 'a_8h_1a1'}) is True
    text = etree.tostring(root, encoding='unicode')
    assert text.count('<ref') == 2  # the pre-existing ref plus the one injected in the tail
    assert '<computeroutput>#M</computeroutput> tail <ref refid="a_8h_1a1" kindref="member">M</ref>' in text
    assert '<highlight>#M</highlight>' in text
    assert '<ulink url="https://example.com">#M</ulink>' in text
    assert '<ref refid="a_8h_1a1" kindref="member">#M</ref>' in text


def test_resolve_define_refs_no_defines_is_a_noop():
    from lxml import etree

    from poxy import xml_utils
    from poxy.pipeline.xml import resolve_define_refs_in_tree

    root = _define_xml('<para>#M</para>')
    assert resolve_define_refs_in_tree(root, {}) is False
    assert etree.tostring(xml_utils.require(root.find('.//para')), encoding='unicode') == '<para>#M</para>'


def test_unlink_code_spans_unwraps_refs_but_leaves_other_content():
    from lxml import etree

    from poxy.pipeline.xml import unlink_code_spans

    root = _define_xml(
        '<para><computeroutput>#<ref refid="a_8h_1a1" kindref="member">M</ref> tail</computeroutput></para>'
        '<para><computeroutput><ref refid="x" kindref="member">a</ref><ref refid="y" kindref="member">b</ref></computeroutput></para>'
        '<para><computeroutput>plain</computeroutput> and a prose <ref refid="z" kindref="member">link</ref></para>'
    )
    assert unlink_code_spans(root) is True
    text = etree.tostring(root, encoding='unicode')
    assert '<computeroutput>#M tail</computeroutput>' in text
    assert '<computeroutput>ab</computeroutput>' in text
    assert '<ref refid="z" kindref="member">link</ref>' in text  # refs outside code spans survive


def test_strip_markdown_file_anchors_removes_anchor_and_emptied_para():
    from lxml import etree

    from poxy.pipeline.xml import strip_markdown_file_anchors

    root = _define_xml(
        '<para><anchor id="macro_refs_1md_src_2macro__refs"/></para>'
        '<para><anchor id="apage_1a_real_anchor"/>kept</para>'
        '<para><anchor id="apage_1md_other"/>text keeps the para</para>'
    )
    assert strip_markdown_file_anchors(root) is True
    text = etree.tostring(root, encoding='unicode')
    assert 'md_src_2macro__refs' not in text
    assert 'md_other' not in text
    assert '<para>text keeps the para</para>' in text
    assert '<anchor id="apage_1a_real_anchor"/>kept' in text
    assert text.count('<para>') == 2  # the emptied para is gone


def test_normalize_tagfile_drops_synthetic_markdown_docanchors():
    from poxy import xml_utils
    from poxy.pipeline.xml import normalize_tagfile

    root = xml_utils.read(
        '<tagfile>'
        '<compound kind="page"><name>macro_refs</name><filename>macro_refs.html</filename>'
        '<docanchor file="macro_refs.html" title="src/macro_refs.md">md_src_2macro__refs</docanchor>'
        '<docanchor file="macro_refs.html" title="A real section">real_section</docanchor>'
        '</compound>'
        '</tagfile>'
    )
    assert normalize_tagfile(root) is True
    anchors = [d.text for d in root.iter('docanchor')]
    assert anchors == ['real_section']


def test_read_index_define_names(tmp_path):
    from poxy.pipeline.xml import read_index_define_names

    (tmp_path / 'index.xml').write_text(
        '<doxygenindex>'
        '<compound kind="file" refid="code_8h"><name>code.h</name>'
        '<member kind="define" refid="code_8h_1aBEEF"><name>M</name></member>'
        '<member kind="enum" refid="code_8h_1aDEAD"><name>e</name></member>'
        '</compound>'
        '</doxygenindex>',
        encoding='utf-8',
    )
    assert read_index_define_names(tmp_path) == {'M'}
    assert read_index_define_names(tmp_path / 'nonexistent') == set()


@pytest.mark.parametrize(
    'text,name',
    [
        ("explicit link request to 'M' could not be resolved", 'M'),
        ("explicit link request to `M' could not be resolved", 'M'),
    ],
)
def test_unresolvable_define_link_warning_regex(text, name):
    from poxy import run

    m = run._unresolvable_define_link.search(f'file.md:3: {text}')
    assert m is not None and m[1] == name


@pytest.mark.parametrize(
    'text,name',
    [
        ("unable to resolve reference to 'M' for \\ref command", 'M'),
        ("unable to resolve reference to `M' for \\ref command", 'M'),
    ],
)
def test_unresolvable_define_ref_warning_regex(text, name):
    from poxy import run

    m = run._unresolvable_define_ref.search(f'file.md:3: {text}')
    assert m is not None and m[1] == name


# ----------------------------------------------------------------------------------------------------------------------
# run (m.css failure diagnosis)
# ----------------------------------------------------------------------------------------------------------------------

_MCSS_PARSE_CRASH_STDERR = """WARNING:root:rpcc.xml: inline code has multiple lines, fallback to a code block
WARNING:root:rpcc.xml: no filename attribute in <programlisting>, assuming C++
Traceback (most recent call last):
  File ".../doxygen.py", line 4249, in run
    parsed = parse_xml(state, file)
  File ".../doxygen.py", line 1939, in parse_toplevel_desc
    parsed = parse_desc_internal(state, element)
  File ".../doxygen.py", line 1491, in parse_desc_internal
    content = parse_inline_desc(state, i).strip()
  File ".../doxygen.py", line 1971, in parse_inline_desc
    parsed = parse_desc_internal(state, element, trim=False)
  File ".../doxygen.py", line 839, in parse_desc_internal
    assert element.tag in ['para', '{http://mcss.mosra.cz/doxygen/}div']
AssertionError"""


# an AssertionError inside the same parser functions but on an unrelated assert (e.g. a poxy
# normalisation gap) must NOT be misdiagnosed as malformed block-in-inline markup
_MCSS_UNRELATED_ASSERT_STDERR = """Traceback (most recent call last):
  File ".../doxygen.py", line 4249, in run
    parsed = parse_xml(state, file)
  File ".../doxygen.py", line 1939, in parse_toplevel_desc
    parsed = parse_desc_internal(state, element)
  File ".../doxygen.py", line 836, in parse_desc_internal
    assert not parsed.section
AssertionError"""


def test_diagnose_mcss_failure_recognises_block_in_inline_crash_and_hints_file():
    from poxy import run

    msg = run.diagnose_mcss_failure(_MCSS_PARSE_CRASH_STDERR)
    assert msg is not None
    assert "last working on 'rpcc.xml'" in msg
    assert 'block-level element' in msg
    assert 'bug-report' in msg


def test_diagnose_mcss_failure_recognises_crash_without_named_file():
    from poxy import run

    stderr = '\n'.join(line for line in _MCSS_PARSE_CRASH_STDERR.splitlines() if not line.startswith('WARNING:root:'))
    msg = run.diagnose_mcss_failure(stderr)
    assert msg is not None
    assert 'm.css crashed' in msg
    assert 'last working on' not in msg


@pytest.mark.parametrize(
    'stderr',
    [
        '',
        'WARNING:root:rpcc.xml: some warning but no crash',
        "Traceback (most recent call last):\n  File 'x'\nKeyError: 'foo'",
        _MCSS_UNRELATED_ASSERT_STDERR,
    ],
)
def test_diagnose_mcss_failure_ignores_unrelated_output(stderr):
    from poxy import run

    assert run.diagnose_mcss_failure(stderr) is None


# ----------------------------------------------------------------------------------------------------------------------
# config.PostBuild
# ----------------------------------------------------------------------------------------------------------------------


def test_post_build_absent_is_empty():
    assert config.PostBuild(None).commands == []
    assert config.PostBuild({}).commands == []


def test_post_build_flattens_entries_and_applies_defaults():
    pb = config.PostBuild(
        {
            'post': [
                {'commands': ['echo hi', ['python', 'p.py']]},
                {
                    'commands': ['deploy'],
                    'shell': True,
                    'working_directory': 'config',
                    'allow_failure': True,
                    'timeout': 30,
                },
            ]
        }
    )
    assert len(pb.commands) == 3
    assert pb.commands[0] == dict(
        raw='echo hi', argv=None, shell=False, working_directory='output', allow_failure=False, timeout=None
    )
    assert pb.commands[1]['argv'] == ['python', 'p.py'] and pb.commands[1]['raw'] is None
    assert pb.commands[2] == dict(
        raw='deploy', argv=None, shell=True, working_directory='config', allow_failure=True, timeout=30.0
    )


def test_post_build_skips_blank_commands():
    assert config.PostBuild({'post': [{'commands': ['  ', ['', '  ']]}]}).commands == []
