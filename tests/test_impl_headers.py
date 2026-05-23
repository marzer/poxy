#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Unit tests for the implementation-header feature (poxy.pipeline.xml):
  - relink_implementation_header_refs: the fix for #defines / file-scoped members and inter-document
    references losing their links once an impl header is merged into its public header and deleted.
  - resolve_implementation_headers: matching configured header/impl paths to doxygen's real compound ids
    by <location>, robust to directory layout (the hardening over guessing mangle(basename(path))).
"""

import pytest
from lxml import etree

from poxy.pipeline.xml import (
    fold_implementation_header_index_entries,
    fold_implementation_headers_in_tagfile,
    normalize_tagfile,
    relink_implementation_header_refs,
    resolve_implementation_headers,
)
from poxy.utils import Error
from poxy.xml_utils import require


def relink(text):
    # impl header 'detail/a.hpp' (compound id 'a_8hpp') merged into 'foo.hpp' (compound id 'foo_8hpp')
    return relink_implementation_header_refs(text, 'a_8hpp', 'foo_8hpp', 'detail/a.hpp', 'foo.hpp')


def test_rewrites_file_scoped_member_id():
    # a #define's memberdef id is prefixed with the impl-file compound id
    assert relink('<memberdef id="a_8hpp_1ae680">') == '<memberdef id="foo_8hpp_1ae680">'


def test_rewrites_refs_to_file_scoped_members():
    assert relink('<ref refid="a_8hpp_1ae680">IMPL_ANSWER</ref>') == '<ref refid="foo_8hpp_1ae680">IMPL_ANSWER</ref>'


def test_rewrites_compoundref_to_the_file_compound():
    assert relink('<ref refid="x" compoundref="a_8hpp">') == '<ref refid="x" compoundref="foo_8hpp">'


def test_rewrites_bare_file_refid():
    # a prose reference to the (deleted) impl-header file compound must point at the public header
    assert relink('<ref refid="a_8hpp" kindref="compound">a.hpp</ref>') == (
        '<ref refid="foo_8hpp" kindref="compound">a.hpp</ref>'
    )


def test_rewrites_source_path():
    assert relink('<location file="detail/a.hpp"/>') == '<location file="foo.hpp"/>'


def test_does_not_corrupt_a_different_compound_sharing_the_prefix():
    # 'xa_8hpp' merely contains 'a_8hpp' as a substring; the leading quote must protect it
    text = '<memberdef id="xa_8hpp_1ab12"><ref refid="xa_8hpp_1ab12"/></memberdef>'
    assert relink(text) == text


def test_leaves_unrelated_ids_alone():
    text = '<memberdef id="namespacefoo_1a999"><ref refid="structbar_1aff0"/></memberdef>'
    assert relink(text) == text


# ----------------------------------------------------------------------------------------------------------------------
# fold_implementation_header_index_entries (regression guard: public header listed once, no dangling entries)
# ----------------------------------------------------------------------------------------------------------------------


def test_fold_index_entries_collapses_to_single_public_compound():
    index = etree.fromstring(
        '<doxygenindex>'
        '<compound refid="foo_8hpp" kind="file"><name>foo.hpp</name></compound>'
        '<compound refid="a_8hpp" kind="file"><name>a.hpp</name>'
        '<member refid="a_8hpp_1ae680" kind="define"><name>IMPL_ANSWER</name></member></compound>'
        '<compound refid="b_8hpp" kind="file"><name>b.hpp</name>'
        '<member refid="b_8hpp_1af1" kind="function"><name>make_gadget</name></member></compound>'
        '</doxygenindex>'
    )
    assert fold_implementation_header_index_entries(index, {'a_8hpp': 'foo_8hpp', 'b_8hpp': 'foo_8hpp'}) is True
    files = index.findall('compound')
    # exactly one file compound remains: the public header
    assert [c.get('refid') for c in files] == ['foo_8hpp']
    # and it now owns the members that came from the implementation headers
    assert [n.text for n in files[0].iter('name')][1:] == ['IMPL_ANSWER', 'make_gadget']
    # no implementation-header file compound entries remain (member refids are rehomed later by the relink)
    assert not any(c.get('refid') in ('a_8hpp', 'b_8hpp') for c in index.findall('compound'))


def test_fold_tagfile_collapses_impl_compounds_and_remaps_pages():
    tagfile = etree.fromstring(
        '<tagfile>'
        '<compound kind="file"><name>a.hpp</name><filename>a_8hpp.html</filename>'
        '<class kind="struct">foo::widget</class><namespace>foo</namespace>'
        '<member kind="define"><name>IMPL_ANSWER</name><anchorfile>a_8hpp.html</anchorfile>'
        '<anchor>ae680</anchor></member></compound>'
        '<compound kind="file"><name>foo.hpp</name><filename>foo_8hpp.html</filename>'
        '<includes id="a_8hpp" name="a.hpp">detail/a.hpp</includes></compound>'
        '</tagfile>'
    )
    # implementation_header_data shape: (hp, hfn, hid, [(ip, ifn, iid), ...])
    data = [('foo.hpp', 'foo.hpp', 'foo_8hpp', [('detail/a.hpp', 'a.hpp', 'a_8hpp')])]
    assert fold_implementation_headers_in_tagfile(tagfile, data) is True
    files = [c for c in tagfile.findall('compound') if c.get('kind') == 'file']
    # only the public header file compound remains
    assert [require(c.find('filename')).text for c in files] == ['foo_8hpp.html']
    foo = files[0]
    # the define moved over and its page reference was remapped to the public page
    member = require(foo.find('member'))
    assert require(member.find('name')).text == 'IMPL_ANSWER'
    assert require(member.find('anchorfile')).text == 'foo_8hpp.html'
    # the <includes> of the merged-away header is gone, and no impl page survives anywhere
    assert foo.find('includes') is None
    assert b'a_8hpp' not in etree.tostring(tagfile)


def test_fold_index_entries_noop_without_impl_headers():
    index = etree.fromstring(
        '<doxygenindex><compound refid="foo_8hpp" kind="file"><name>foo.hpp</name></compound></doxygenindex>'
    )
    assert fold_implementation_header_index_entries(index, {}) is False


# ----------------------------------------------------------------------------------------------------------------------
# resolve_implementation_headers (location-based matching)
# ----------------------------------------------------------------------------------------------------------------------


def test_resolve_basename_id_layout():
    # doxygen strips the detail/ dir, so file ids are basenames
    loc = {'foo.hpp': 'foo_8hpp', 'detail/a.hpp': 'a_8hpp', 'detail/b.hpp': 'b_8hpp'}
    data = resolve_implementation_headers([('foo.hpp', ['detail/*.hpp'])], loc)
    assert len(data) == 1
    hp, hfn, hid, impls = data[0]
    assert (hp, hid) == ('foo.hpp', 'foo_8hpp')
    assert [(ip, iid) for ip, ifn, iid in impls] == [('detail/a.hpp', 'a_8hpp'), ('detail/b.hpp', 'b_8hpp')]


def test_resolve_path_qualified_id_layout():
    # the hardening: doxygen ids the impl files by full path; the old mangle(basename) guess would miss these
    loc = {'foo.hpp': 'foo_8hpp', 'detail/a.hpp': 'detail_2a_8hpp', 'detail/b.hpp': 'detail_2b_8hpp'}
    data = resolve_implementation_headers([('foo.hpp', ['detail/*.hpp'])], loc)
    assert [iid for ip, ifn, iid in data[0][3]] == ['detail_2a_8hpp', 'detail_2b_8hpp']


def test_resolve_non_wildcard_exact_location():
    loc = {'foo.hpp': 'foo_8hpp', 'detail/a.hpp': 'detail_2a_8hpp'}
    data = resolve_implementation_headers([('foo.hpp', ['detail/a.hpp'])], loc)
    assert data[0][3] == [('detail/a.hpp', 'a.hpp', 'detail_2a_8hpp')]


def test_resolve_skips_unmatched_header():
    assert resolve_implementation_headers([('foo.hpp', ['detail/*.hpp'])], {'other.hpp': 'other_8hpp'}) == []


def test_resolve_header_with_no_matching_impls_excluded():
    assert resolve_implementation_headers([('foo.hpp', ['detail/*.hpp'])], {'foo.hpp': 'foo_8hpp'}) == []


def test_resolve_excludes_header_from_its_own_impls():
    loc = {'foo.hpp': 'foo_8hpp', 'detail/a.hpp': 'a_8hpp'}
    data = resolve_implementation_headers([('foo.hpp', ['*.hpp'])], loc)
    assert [ip for ip, ifn, iid in data[0][3]] == ['detail/a.hpp']


def test_resolve_conflicting_assignment_raises():
    loc = {'foo.hpp': 'foo_8hpp', 'bar.hpp': 'bar_8hpp', 'detail/a.hpp': 'a_8hpp'}
    with pytest.raises(Error):
        resolve_implementation_headers([('foo.hpp', ['detail/a.hpp']), ('bar.hpp', ['detail/a.hpp'])], loc)


# ----------------------------------------------------------------------------------------------------------------------
# normalize_tagfile (version-independence: drop dir compounds, dedupe namespace members out of file compounds)
# ----------------------------------------------------------------------------------------------------------------------


def _tagfile(*compounds):
    return etree.fromstring(f'<tagfile>{"".join(compounds)}</tagfile>')


def test_normalize_tagfile_strips_namespace_members_duplicated_into_file_compound():
    # older doxygen lists a namespace member in BOTH the namespace and the owning file compound; the
    # file-compound copy (same anchorfile+anchor) must be removed, the file's own #define kept
    tagfile = _tagfile(
        '<compound kind="file"><name>code.h</name>'
        '<member kind="define"><name>KEK</name><anchorfile>code_8h.html</anchorfile><anchor>d0</anchor></member>'
        '<member kind="function"><name>f</name><anchorfile>nstest.html</anchorfile><anchor>a1</anchor></member>'
        '</compound>',
        '<compound kind="namespace"><name>test</name>'
        '<member kind="function"><name>f</name><anchorfile>nstest.html</anchorfile><anchor>a1</anchor></member>'
        '</compound>',
    )
    assert normalize_tagfile(tagfile) is True
    file_members = require(tagfile.find('compound[@kind="file"]')).findall('member')
    assert [require(m.find('name')).text for m in file_members] == ['KEK']
    # the namespace compound's copy is untouched
    assert len(require(tagfile.find('compound[@kind="namespace"]')).findall('member')) == 1


def test_normalize_tagfile_keeps_file_member_with_no_namespace_twin():
    tagfile = _tagfile(
        '<compound kind="file"><name>code.h</name>'
        '<member kind="define"><name>KEK</name><anchorfile>code_8h.html</anchorfile><anchor>d0</anchor></member>'
        '</compound>'
    )
    assert normalize_tagfile(tagfile) is False
    assert len(require(tagfile.find('compound[@kind="file"]')).findall('member')) == 1


def test_normalize_tagfile_drops_dir_compounds():
    tagfile = _tagfile(
        '<compound kind="dir"><name>src</name></compound>', '<compound kind="file"><name>a.h</name></compound>'
    )
    assert normalize_tagfile(tagfile) is True
    assert tagfile.find('compound[@kind="dir"]') is None
