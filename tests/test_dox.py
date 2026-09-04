#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Unit tests for the markdown -> synthetic .dox page compiler (poxy.dox).
"""

from poxy.dox import markdown_to_dox


def test_page_directive_and_comment_form():
    out = markdown_to_dox('Body text.\n', 'my_page', 'My Page')
    assert out == '/// @page my_page My Page\n///\n/// Body text.\n'


def test_optional_directives_are_emitted_in_order():
    out = markdown_to_dox('Body.\n', 'p', 'P', footer_nav=True, toc=True)
    assert out.startswith('/// @page p P\n/// @m_footernavigation\n/// @tableofcontents\n///\n')


def test_leading_h1_is_stripped_because_the_title_replaces_it():
    out = markdown_to_dox('# My Page\n\nBody.\n', 'p', 'My Page')
    assert 'My Page {#' not in out
    assert out == '/// @page p My Page\n///\n/// Body.\n'


def test_stripped_leading_h1_leaves_its_explicit_label_behind_as_an_anchor():
    # '# Changelog {#changelog}' is the conventional doxygen form; '@ref changelog' has to keep working
    out = markdown_to_dox('# My Page {#custom}\n\nBody.\n', 'p', 'My Page')
    assert out == '/// @page p My Page\n///\n/// @anchor custom\n///\n/// Body.\n'


def test_a_leading_h1_without_a_label_emits_no_anchor():
    assert '@anchor' not in markdown_to_dox('# My Page\n\nBody.\n', 'p', 'My Page')


def test_a_retained_leading_h1_keeps_its_explicit_label_in_place():
    out = markdown_to_dox('# Body Heading {#custom}\n\nBody.\n', 'p', 'Front Matter Title')
    assert '@anchor' not in out
    assert '/// # Body Heading {#custom}' in out


def test_explicit_subheading_labels_are_left_alone():
    out = markdown_to_dox('# T\n\n## A {#kept}\n\n## B\n', 'p', 'T')
    assert '/// # A {#kept}' in out
    assert '/// # B {#p_b}' in out


def test_only_the_leading_h1_is_stripped():
    out = markdown_to_dox('# Title\n\n# Later\n', 'p', 'Title')
    assert '/// # Later {#p_later}' in out


def test_headings_are_promoted_so_the_shallowest_is_h1():
    out = markdown_to_dox('# T\n\n## A\n\n### B\n', 'p', 'T')
    assert '/// # A {#p_a}' in out
    assert '/// ## B {#p_b}' in out


def test_blank_lines_carry_no_trailing_whitespace():
    out = markdown_to_dox('a\n\nb\n', 'p', 'P')
    assert '/// \n' not in out
    assert '\n///\n' in out


def test_fenced_code_survives_a_comment_terminator():
    # the '///' comment form is chosen precisely so a '*/' in a code block cannot end the comment early
    body = '```cpp\n/* a comment with */ inside\n```\n'
    out = markdown_to_dox(body, 'p', 'P')
    assert '/// /* a comment with */ inside' in out
    assert '/**' not in out


def test_hashes_and_headings_inside_fences_are_untouched():
    body = '```cpp\n#define FOO 1\n## not a heading\n```\n'
    out = markdown_to_dox(body, 'p', 'P')
    assert '/// #define FOO 1' in out
    assert '/// ## not a heading' in out


def test_indented_code_block_keeps_its_indentation():
    out = markdown_to_dox('para\n\n    indented code\n', 'p', 'P')
    assert '///     indented code' in out


def test_tables_pass_through_without_being_read_as_setext():
    out = markdown_to_dox('| a | b |\n|---|---|\n| 1 | 2 |\n', 'p', 'P')
    assert '/// | a | b |\n/// |---|---|\n/// | 1 | 2 |' in out


def test_setext_headings_are_converted_then_promoted():
    out = markdown_to_dox('Heading\n-------\n\nbody\n', 'p', 'P')
    assert '/// # Heading {#p_heading}' in out


def test_crlf_input_produces_lf_output():
    assert '\r' not in markdown_to_dox('# T\r\n\r\nbody\r\n', 'p', 'T')
