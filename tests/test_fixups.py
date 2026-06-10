#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Unit tests for the individual Doxygen-XML quirk fixes (poxy.pipeline.fixups).

These exercise each fix in isolation on small XML fragments, so the fixes are protected even though
the end-to-end snapshot project doesn't trigger every one of them.
"""

import pytest
from lxml import etree

from poxy.pipeline import fixups
from poxy.xml_utils import require


def E(xml: str):
    return etree.fromstring(xml)


def test_fix_trailing_return_void_auto_bug():
    # 'auto f() -> int' should move the trailing return type into <type> (mosra/m.css#94)
    cd = E(
        '<sectiondef><memberdef kind="function">'
        '<type>auto</type><argsstring>() -&gt; int</argsstring><name>f</name>'
        '</memberdef></sectiondef>'
    )
    assert fixups.fix_trailing_return_types(cd) is True
    m = require(cd.find('memberdef'))
    assert require(m.find('type')).text == 'int'
    assert require(m.find('argsstring')).text == '()'


def test_fix_trailing_return_collapses_qualified_spacing():
    cd = E(
        '<sectiondef><memberdef kind="function">'
        '<type>auto</type><argsstring>() -&gt; std :: vector&lt; int &gt;</argsstring><name>f</name>'
        '</memberdef></sectiondef>'
    )
    assert fixups.fix_trailing_return_types(cd) is True
    assert require(require(cd.find('memberdef')).find('type')).text == 'std::vector<int>'


def test_fix_trailing_return_redundant_auto():
    # 'auto foo() -> auto' redundancy (marzer/poxy#26)
    cd = E(
        '<sectiondef><memberdef kind="function">'
        '<type>auto</type><argsstring>()</argsstring><name>f</name>'
        '</memberdef></sectiondef>'
    )
    assert fixups.fix_trailing_return_types(cd) is True
    assert require(require(cd.find('memberdef')).find('type')).text == fixups.DEDUCED_AUTO_RETURN_TYPE


def test_fix_trailing_return_ignores_decltype():
    cd = E(
        '<sectiondef><memberdef kind="function">'
        '<type>auto</type><argsstring>() -&gt; decltype(x)</argsstring><name>f</name>'
        '</memberdef></sectiondef>'
    )
    assert fixups.fix_trailing_return_types(cd) is False


def test_fix_trailing_return_also_rewrites_definition():
    # older doxygen leaves the trailing return as 'auto' in <definition> too; it must converge to the type
    cd = E(
        '<sectiondef><memberdef kind="function">'
        '<type>auto</type><argsstring>() -&gt; int</argsstring>'
        '<definition>auto test::f</definition><name>f</name>'
        '</memberdef></sectiondef>'
    )
    assert fixups.fix_trailing_return_types(cd) is True
    m = require(cd.find('memberdef'))
    assert require(m.find('type')).text == 'int'
    assert require(m.find('definition')).text == 'int test::f'


# ----------------------------------------------------------------------------------------------------------------------
# normalize_member_definitions (older-doxygen <definition>/<location> string quirks)
# ----------------------------------------------------------------------------------------------------------------------


def test_normalize_definition_strips_leading_constexpr():
    cd = E(
        '<sectiondef><memberdef kind="variable" constexpr="yes">'
        '<definition>constexpr bool test::v</definition><name>v</name></memberdef></sectiondef>'
    )
    assert fixups.normalize_member_definitions(cd) is True
    assert require(require(cd.find('memberdef')).find('definition')).text == 'bool test::v'


def test_normalize_definition_keeps_static_constexpr():
    # 'static constexpr' is kept by newer doxygen (constexpr is not leading), so leave it untouched
    cd = E(
        '<sectiondef><memberdef kind="function" static="yes" constexpr="yes">'
        '<definition>static constexpr int test::f</definition><name>f</name></memberdef></sectiondef>'
    )
    assert fixups.normalize_member_definitions(cd) is False
    assert require(require(cd.find('memberdef')).find('definition')).text == 'static constexpr int test::f'


@pytest.mark.parametrize(
    'definition',
    (
        'using test::a = typedef int',  # <=1.9.x
        'using test::a =  int',  # 1.14/1.15 (stray double space)
        'using test::a = int',  # 1.16+ (already clean)
    ),
)
def test_normalize_definition_collapses_using_alias_to_clean_form(definition):
    cd = E(
        f'<sectiondef><memberdef kind="typedef">'
        f'<definition>{definition}</definition><name>a</name></memberdef></sectiondef>'
    )
    fixups.normalize_member_definitions(cd)
    assert require(require(cd.find('memberdef')).find('definition')).text == 'using test::a = int'


def test_normalize_location_bodyend_minus_one():
    cd = E(
        '<sectiondef><memberdef kind="variable"><name>v</name>'
        '<location file="x.h" bodystart="135" bodyend="-1"/></memberdef></sectiondef>'
    )
    assert fixups.normalize_member_definitions(cd) is True
    assert require(require(cd.find('memberdef')).find('location')).get('bodyend') == '135'


# ----------------------------------------------------------------------------------------------------------------------
# normalize_concept_definition (rstrip initializer body, drop the unused <conceptparts> token dump (1.16+))
# ----------------------------------------------------------------------------------------------------------------------


def test_normalize_concept_strips_initializer_tail_whitespace():
    # trailing whitespace lives on the last child's tail, the legitimate space before <ref> must survive
    cd = E(
        '<compounddef kind="concept"><initializer>concept <ref refid="c">C</ref> = requires {};\n}    '
        '</initializer></compounddef>'
    )
    assert fixups.normalize_concept_definition(cd) is True
    init = require(cd.find('initializer'))
    assert init.text == 'concept '
    assert require(init.find('ref')).tail == ' = requires {};\n}'


def test_normalize_concept_strips_initializer_text_when_no_children():
    cd = E('<compounddef kind="concept"><initializer>concept C = true;   </initializer></compounddef>')
    assert fixups.normalize_concept_definition(cd) is True
    assert require(cd.find('initializer')).text == 'concept C = true;'


def test_normalize_concept_drops_conceptparts():
    cd = E(
        '<compounddef kind="concept"><initializer>x</initializer>'
        '<conceptparts><codepart line="1"/></conceptparts></compounddef>'
    )
    assert fixups.normalize_concept_definition(cd) is True
    assert cd.find('conceptparts') is None


def test_normalize_concept_noop_when_already_clean():
    cd = E('<compounddef kind="concept"><initializer>concept C = true;</initializer></compounddef>')
    assert fixups.normalize_concept_definition(cd) is False


def test_add_concept_includes_backfills_after_compoundname():
    cd = E('<compounddef kind="concept"><compoundname>test::nested::c</compoundname><templateparamlist/></compounddef>')
    template = E('<includes local="no">code.h</includes>')
    assert fixups.add_concept_includes(cd, template) is True
    kids = [child.tag for child in cd]
    assert kids == ['compoundname', 'includes', 'templateparamlist']
    inc = require(cd.find('includes'))
    assert inc.text == 'code.h' and inc.get('local') == 'no'


def test_add_concept_includes_noop_when_already_present():
    cd = E(
        '<compounddef kind="concept"><compoundname>c</compoundname><includes local="no">a.h</includes></compounddef>'
    )
    assert fixups.add_concept_includes(cd, E('<includes local="no">other.h</includes>')) is False
    assert require(cd.find('includes')).text == 'a.h'


# ----------------------------------------------------------------------------------------------------------------------
# resolve_plain_type_references (re-link a plain-text <type> some doxygen versions stopped cross-referencing)
# ----------------------------------------------------------------------------------------------------------------------


def _member_type_only(xml: str):
    return E(f'<compounddef><sectiondef>{xml}</sectiondef></compounddef>')


def test_resolve_plain_type_links_by_scope():
    # 'struct_1' in scope 'test::class_1' must resolve to the namespace-level 'test::struct_1'
    cd = _member_type_only('<memberdef kind="function"><type>struct_1</type><name>f</name></memberdef>')
    ids = {'test::struct_1': 'structtest_1_1struct__1'}
    assert fixups.resolve_plain_type_references(cd, ids, 'test::class_1') is True
    ref = cd.find('.//type/ref')
    assert ref is not None
    assert ref.text == 'struct_1'
    assert ref.get('refid') == 'structtest_1_1struct__1'
    assert ref.get('kindref') == 'compound'


def test_resolve_plain_type_skips_already_linked():
    cd = _member_type_only(
        '<memberdef kind="function"><type><ref refid="x">struct_1</ref></type><name>f</name></memberdef>'
    )
    assert fixups.resolve_plain_type_references(cd, {'test::struct_1': 'x'}, 'test') is False


def test_resolve_plain_type_skips_unknown_type():
    cd = _member_type_only('<memberdef kind="function"><type>int</type><name>f</name></memberdef>')
    assert fixups.resolve_plain_type_references(cd, {'test::struct_1': 'x'}, 'test') is False
    assert require(cd.find('.//type')).text == 'int'


def test_resolve_plain_type_skips_compound_expressions():
    # only a bare identifier is safe to resolve; 'const struct_1&' must be left alone
    cd = _member_type_only('<memberdef kind="function"><type>const struct_1&amp;</type><name>f</name></memberdef>')
    assert fixups.resolve_plain_type_references(cd, {'struct_1': 'x'}, 'test') is False


def test_fix_leaked_keywords_promotes_constexpr():
    cd = E('<sectiondef><memberdef kind="function"><type>constexpr void</type><name>f</name></memberdef></sectiondef>')
    assert fixups.fix_leaked_keywords(cd) is True
    m = require(cd.find('memberdef'))
    assert require(m.find('type')).text == 'void'
    assert m.get('constexpr') == 'yes'


def test_fix_leaked_keywords_friend_variable_kept_as_type():
    # a 'friend' variable with nothing left becomes type 'friend' rather than empty
    cd = E('<sectiondef><memberdef kind="variable"><type>friend</type><name>f</name></memberdef></sectiondef>')
    assert fixups.fix_leaked_keywords(cd) is True
    assert require(require(cd.find('memberdef')).find('type')).text == 'friend'


def test_remove_duplicate_members():
    cd = E(
        '<sectiondef>'
        '<memberdef kind="function" id="a"><name>a</name></memberdef>'
        '<memberdef kind="function" id="a"><name>a</name></memberdef>'
        '<memberdef kind="function" id="b"><name>b</name></memberdef>'
        '</sectiondef>'
    )
    assert fixups.remove_duplicate_members(cd) is True
    assert [m.get('id') for m in cd.findall('memberdef')] == ['a', 'b']


def test_resort_members_groups_by_kind():
    cd = E(
        '<sectiondef>'
        '<memberdef kind="function" static="no"><name>z</name></memberdef>'
        '<memberdef kind="define"><name>a</name></memberdef>'
        '<memberdef kind="typedef"><name>m</name></memberdef>'
        '</sectiondef>'
    )
    assert fixups.resort_members(cd, 'namespace') is True
    assert [m.get('kind') for m in cd.findall('memberdef')] == ['define', 'typedef', 'function']


def test_resort_members_sorts_within_group_by_name():
    cd = E(
        '<sectiondef>'
        '<memberdef kind="function" static="no"><name>zebra</name></memberdef>'
        '<memberdef kind="function" static="no"><name>apple</name></memberdef>'
        '</sectiondef>'
    )
    assert fixups.resort_members(cd, 'namespace') is True
    assert [require(m.find('name')).text for m in cd.findall('memberdef')] == ['apple', 'zebra']


def test_sort_inner_refs():
    cd = E('<compounddef><innerclass refid="2">B</innerclass><innerclass refid="1">A</innerclass></compounddef>')
    assert fixups.sort_inner_refs(cd) is True
    assert [e.text for e in cd.findall('innerclass')] == ['A', 'B']


def test_merge_userdefined_sections_with_shared_header():
    cd = E(
        '<compounddef>'
        '<sectiondef kind="user-defined"><header>H</header>'
        '<memberdef kind="function" id="a"><name>a</name></memberdef></sectiondef>'
        '<sectiondef kind="user-defined"><header>H</header>'
        '<memberdef kind="function" id="b"><name>b</name></memberdef></sectiondef>'
        '</compounddef>'
    )
    assert fixups.merge_userdefined_sections(cd) is True
    sections = cd.findall('sectiondef')
    assert len(sections) == 1
    assert [m.get('id') for m in sections[0].findall('memberdef')] == ['a', 'b']


def test_sort_userdefined_sections_by_header():
    cd = E(
        '<compounddef>'
        '<sectiondef kind="user-defined"><header>Zoo</header></sectiondef>'
        '<sectiondef kind="user-defined"><header>Ant</header></sectiondef>'
        '</compounddef>'
    )
    assert fixups.sort_userdefined_sections(cd) is True
    assert [require(s.find('header')).text for s in cd.findall('sectiondef')] == ['Ant', 'Zoo']


def test_fix_nested_tableofcontents_flattens():
    cd = E(
        '<compounddef><tableofcontents><tableofcontents><tocsect/></tableofcontents></tableofcontents></compounddef>'
    )
    assert fixups.fix_nested_tableofcontents(cd) is True
    tocs = cd.findall('tableofcontents')
    assert len(tocs) == 1
    assert [c.tag for c in tocs[0]] == ['tocsect']


def test_unwrap_synthetic_page_sections_promotes_and_flattens():
    # doxygen wraps each top-level H2 (when H1 became the page title) in a titleless <sect1>
    cd = E(
        '<compounddef kind="page"><detaileddescription>'
        '<para>preamble</para>'
        '<sect1 id="p_1autotoc_md1_1s1"><sect2 id="p_1autotoc_md1"><title>v1.0</title>'
        '<sect3 id="p_1autotoc_md2"><title>lib</title><para>x</para></sect3></sect2></sect1>'
        '<sect1 id="p_1autotoc_md3_1s1"><sect2 id="p_1autotoc_md3"><title>v0.9</title></sect2></sect1>'
        '</detaileddescription></compounddef>'
    )
    assert fixups.unwrap_synthetic_page_sections(cd) is True
    dd = require(cd.find('detaileddescription'))
    # the synthetic sect1 wrappers are gone; versions promoted to sect1, components to sect2
    assert [c.tag for c in dd] == ['para', 'sect1', 'sect1']
    versions = dd.findall('sect1')
    assert require(versions[0].find('title')).text == 'v1.0'
    assert versions[0].get('id') == 'p_1autotoc_md1'  # real heading id preserved
    assert require(versions[0].find('sect2/title')).text == 'lib'
    assert require(versions[1].find('title')).text == 'v0.9'


def test_unwrap_synthetic_page_sections_leaves_titled_sect1_alone():
    cd = E(
        '<compounddef kind="page"><detaileddescription>'
        '<sect1 id="s"><title>Real Heading</title><sect2 id="s2"><title>Sub</title></sect2></sect1>'
        '</detaileddescription></compounddef>'
    )
    assert fixups.unwrap_synthetic_page_sections(cd) is False
    dd = require(cd.find('detaileddescription'))
    assert require(dd.find('sect1/title')).text == 'Real Heading'
    assert require(dd.find('sect1/sect2/title')).text == 'Sub'


def _code(content):
    return fixups.SECTION_TITLE_CODE_BEGIN + content + fixups.SECTION_TITLE_CODE_END


def test_normalize_section_title_preserves_leading_code_span():
    # '## `code` heading' -> <title> starts with a child, .text is None (crashes m.css); the code span
    # must survive as a sentinel for later restoration to <code>
    cd = E(
        '<compounddef><detaileddescription><sect1><title>'
        '<computeroutput>python-client</computeroutput> ships a transport</title>'
        '<para>x</para></sect1></detaileddescription></compounddef>'
    )
    assert fixups.normalize_section_titles(cd) is True
    title = require(cd.find('.//sect1/title'))
    assert title.text == _code('python-client') + ' ships a transport'
    assert len(title) == 0


def test_normalize_section_title_preserves_midheading_code_span():
    # mid-heading markup that m.css would otherwise truncate at 'Why '
    cd = E(
        '<compounddef><detaileddescription><sect2><title>'
        'Why <computeroutput>RPCC</computeroutput>?</title></sect2></detaileddescription></compounddef>'
    )
    assert fixups.normalize_section_titles(cd) is True
    assert require(cd.find('.//sect2/title')).text == 'Why ' + _code('RPCC') + '?'


def test_normalize_section_title_flattens_other_markup():
    cd = E(
        '<compounddef><detaileddescription><sect1><title>'
        'A <emphasis>bold</emphasis> claim</title></sect1></detaileddescription></compounddef>'
    )
    assert fixups.normalize_section_titles(cd) is True
    assert require(cd.find('.//sect1/title')).text == 'A bold claim'


def test_normalize_empty_section_title():
    cd = E('<compounddef><detaileddescription><sect1><title/></sect1></detaileddescription></compounddef>')
    assert fixups.normalize_section_titles(cd) is True
    assert require(cd.find('.//sect1/title')).text == ''


def test_normalize_leaves_plain_titles_untouched():
    cd = E(
        '<compounddef><detaileddescription><sect1><title>Plain heading</title>'
        '</sect1></detaileddescription></compounddef>'
    )
    assert fixups.normalize_section_titles(cd) is False
    assert require(cd.find('.//sect1/title')).text == 'Plain heading'


def test_section_title_code_span_sentinels_restored_to_code():
    # the post-HTML fixer turns the sentinels back into <code> (the other half of the round-trip)
    from poxy.fixers import SectionTitleCodeSpans

    text = 'Why ' + _code('RPCC') + '? and ' + _code('foo')
    # this fixer ignores context/path, so None is fine here
    assert SectionTitleCodeSpans()(None, text, None) == 'Why <code>RPCC</code>? and <code>foo</code>'  # type: ignore[arg-type]


def test_fix_programlisting_ascii_to_shell_session():
    cd = E('<compounddef><programlisting filename=".ascii"><codeline/></programlisting></compounddef>')
    assert fixups.fix_programlisting(cd) is True
    assert require(cd.find('programlisting')).get('filename') == '.shell-session'


def test_fix_programlisting_recovers_explicit_filetype():
    # doxygen drops an explicitly-set type into the first codeline as '{.cpp}'
    cd = E(
        '<compounddef><programlisting>'
        '<codeline><highlight>{.cpp}</highlight></codeline>'
        '<codeline><highlight>int x;</highlight></codeline>'
        '</programlisting></compounddef>'
    )
    assert fixups.fix_programlisting(cd) is True
    pl = require(cd.find('programlisting'))
    assert pl.get('filename') == '.cpp'
    assert len(pl.findall('codeline')) == 1


def _reconstruct_code(codeline) -> str:
    # mirror m.css's text reconstruction (documentation/doxygen.py): concatenate highlight text,
    # <sp/> as a space, <ref> text, and every tail in document order
    code = ''
    for tag in codeline.findall('highlight'):
        if tag.text:
            code += tag.text
        for token in tag:
            code += ' ' if token.tag == 'sp' else (token.text or '')
            if token.tail:
                code += token.tail
        if tag.tail:
            code += tag.tail
    return code


def test_collapse_codeline_highlights_merges_to_single_normal_span():
    cd = E(
        '<compounddef><programlisting filename=".cpp"><codeline>'
        '<highlight class="keyword">using<sp/></highlight>'
        '<highlight class="normal">x<sp/>=<sp/>int;</highlight>'
        '</codeline></programlisting></compounddef>'
    )
    codeline = require(cd.find('.//codeline'))
    before = _reconstruct_code(codeline)
    assert fixups.fix_programlisting(cd) is True
    spans = codeline.findall('highlight')
    assert len(spans) == 1
    assert spans[0].get('class') == 'normal'
    assert _reconstruct_code(codeline) == before == 'using x = int;'


def test_collapse_codeline_highlights_preserves_refs():
    cd = E(
        '<compounddef><programlisting filename=".cpp"><codeline>'
        '<highlight class="normal"><ref refid="r1">Foo</ref><sp/>f;</highlight>'
        '<highlight class="comment"><sp/>//<sp/>note</highlight>'
        '</codeline></programlisting></compounddef>'
    )
    codeline = require(cd.find('.//codeline'))
    before = _reconstruct_code(codeline)
    assert fixups.fix_programlisting(cd) is True
    span = require(codeline.find('highlight'))
    ref = require(span.find('ref'))
    assert ref.get('refid') == 'r1' and ref.text == 'Foo'
    assert _reconstruct_code(codeline) == before == 'Foo f; // note'


def test_collapse_codeline_highlights_noop_on_single_normal_span():
    cd = E(
        '<compounddef><programlisting filename=".cpp">'
        '<codeline><highlight class="normal">already clean</highlight></codeline>'
        '</programlisting></compounddef>'
    )
    assert fixups.fix_programlisting(cd) is False


def test_fix_leading_list_item_folds_first_item_into_list():
    # '@see - @ref a' / '- @ref b': doxygen strands the first item as inline '- <ref/>' text directly
    # before the <itemizedlist> holding the rest; the fix folds it into a proper first <listitem>.
    cd = E(
        '<compounddef><detaileddescription><para><simplesect kind="see">'
        '<para>- <ref refid="a" kindref="compound">A</ref>'
        '<itemizedlist><listitem><para><ref refid="b" kindref="compound">B</ref></para></listitem></itemizedlist>'
        '</para></simplesect></para></detaileddescription></compounddef>'
    )
    assert fixups.fix_leading_list_item(cd) is True
    para = require(require(cd.find('.//simplesect')).find('para'))
    assert (para.text or '').strip() == ''  # no stray '- ' text left in the para
    lists = para.findall('itemizedlist')
    assert len(lists) == 1
    items = lists[0].findall('listitem')
    assert len(items) == 2
    refs = [require(li.find('.//ref')) for li in items]
    assert [r.get('refid') for r in refs] == ['a', 'b']
    assert [r.text for r in refs] == ['A', 'B']


def test_fix_leading_list_item_plain_text_first_item():
    cd = E(
        '<compounddef><detaileddescription><para><simplesect kind="see">'
        '<para>- first<itemizedlist><listitem><para>second</para></listitem></itemizedlist></para>'
        '</simplesect></para></detaileddescription></compounddef>'
    )
    assert fixups.fix_leading_list_item(cd) is True
    items = require(cd.find('.//itemizedlist')).findall('listitem')
    assert [require(li.find('para')).text for li in items] == ['first', 'second']


def test_fix_leading_list_item_noop_on_clean_list():
    # body already a proper list (the list started on the next line) - nothing to fold
    cd = E(
        '<compounddef><detaileddescription><para><simplesect kind="see"><para>'
        '<itemizedlist><listitem><para>one</para></listitem><listitem><para>two</para></listitem></itemizedlist>'
        '</para></simplesect></para></detaileddescription></compounddef>'
    )
    assert fixups.fix_leading_list_item(cd) is False


def test_fix_leading_list_item_noop_without_following_list():
    # a single inline item (no <itemizedlist> to merge into) is left as-is
    cd = E('<compounddef><para>- <ref refid="a">A</ref></para></compounddef>')
    assert fixups.fix_leading_list_item(cd) is False


def test_fix_leading_list_item_ignores_intro_text_before_list():
    # a paragraph that legitimately introduces a list (no leading bullet) must not be touched
    cd = E(
        '<compounddef><para>Intro:'
        '<itemizedlist><listitem><para>one</para></listitem></itemizedlist></para></compounddef>'
    )
    assert fixups.fix_leading_list_item(cd) is False
