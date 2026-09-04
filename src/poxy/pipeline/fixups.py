#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Discrete, individually-documented fixes for Doxygen's XML quirks.

Each function here addresses one specific Doxygen misbehaviour, operates on a single element
(a <compounddef> or <sectiondef>) using only local state, and returns True if it changed anything.
They are applied per-file by pipeline/xml.py's preprocess_xml. This is the structured heart of
poxy's man-in-the-middle layer: closing a convergence gap should mean adding or adjusting one
named fix here, with a docstring stating the quirk (and Doxygen version, where relevant).

The stateful, cross-file machinery (implementation-header extraction, the <doxygenindex> pass,
the >=1.9.7 member-reference resolution, missing-inner-node synthesis) deliberately stays in
preprocess_xml, since those passes share accumulators and are not independent per-element fixes.
"""

import copy
import re

# sentinels used to smuggle inline code spans through m.css's plain-text section-heading rendering;
# injected by normalize_section_titles (pre-m.css) and restored by the SectionTitleCodeSpans HTML fixer
# (post-m.css). they are plain lowercase ASCII so html.escape() leaves them untouched, and m.css does not
# insert <wbr> word-breaks into heading text, so they survive intact.
SECTION_TITLE_CODE_BEGIN = r'poxysectiontitlecodebegin'
SECTION_TITLE_CODE_END = r'poxysectiontitlecodeend'

# sentinel marking a deduced 'auto' return type (marzer/poxy#26); injected into <type> here and turned back
# into 'auto' (or used to drop a redundant '-> auto') by the ReturnTypes HTML fixer. plain lowercase ASCII
# with no '_' so m.css's add_wbr() leaves it intact.
DEDUCED_AUTO_RETURN_TYPE = r'poxydeducedautoreturntype'


def _collapse_codeline_highlights(codeline) -> bool:
    """Merge a <codeline>'s <highlight> spans into a single class="normal" span, preserving the text +
    <sp/>/<ref> sequence. Doxygen's lexer partitions and classifies these spans differently across versions
    (e.g. 'this'/'for' as keywords on newer doxygen, plain on older), but m.css discards the classes entirely
    and re-highlights the reconstructed text via pygments, so collapsing them makes the programlisting
    byte-identical across versions with zero effect on the rendered output."""
    highlights = codeline.findall(r'highlight')
    if not highlights or (len(highlights) == 1 and highlights[0].get(r'class') == r'normal'):
        return False
    merged = codeline.makeelement(r'highlight', {r'class': r'normal'})

    def append_text(s):
        if not s:
            return
        kids = list(merged)
        if kids:
            kids[-1].tail = (kids[-1].tail or r'') + s
        else:
            merged.text = (merged.text or r'') + s

    for h in highlights:
        append_text(h.text)
        for child in list(h):  # moving preserves each child's own tail
            merged.append(child)
        append_text(h.tail)
    idx = list(codeline).index(highlights[0])
    for h in highlights:
        codeline.remove(h)
    codeline.insert(idx, merged)
    return True


def fix_programlisting(compounddef) -> bool:
    """Clean up <programlisting> blocks: strip zero-width-joiner mangling, drop empty <highlight>
    blocks, recover an explicitly-set file type that Doxygen dropped, map .ascii -> .shell-session, and
    collapse version-dependent highlight-class spans into a single normal span per line."""
    changed = False
    for programlisting in compounddef.iterdescendants(tag="programlisting"):
        # fix &amp;zwj; mangling (zero-width joiners don't make sense in code blocks anyways)
        for descendant in programlisting.iterdescendants():
            if descendant.text:
                new_text = descendant.text.replace('&amp;zwj;', '')
                new_text = descendant.text.replace('&zwj;', '')
                if new_text != descendant.text:
                    descendant.text = new_text
                    changed = True
            if descendant.tail:
                new_text = descendant.tail.replace('&amp;zwj;', '')
                new_text = descendant.tail.replace('&zwj;', '')
                if new_text != descendant.tail:
                    descendant.tail = new_text
                    changed = True
        # delete highlight blocks that contribute absolutely nothing:
        for highlight in programlisting.iterdescendants(tag="highlight"):
            if not highlight.text and not highlight.tail and not len(highlight):
                highlight.getparent().remove(highlight)
                changed = True
                continue
        # fix <programlisting> losing the file type if we've set it explicitly
        if not programlisting.get(r'filename') and len(programlisting) >= 2 and programlisting[0].tag == 'codeline':
            codeline = programlisting[0]
            if len(codeline) == 1 and codeline[0].tag == 'highlight':
                highlight = codeline[0]
                if len(highlight) <= 1 and highlight.text:
                    m = re.fullmatch(r"[{]([.][a-zA-Z0-9_-]+)[}]", highlight.text)
                    if m:
                        programlisting.set('filename', m[1])
                        programlisting.remove(codeline)
                        changed = True
        # map .ascii -> .shell-session
        if programlisting.get(r'filename') == '.ascii':
            programlisting.set('filename', '.shell-session')
            changed = True
        # collapse version-dependent highlight-class spans
        for codeline in programlisting.findall(r'codeline'):
            changed |= _collapse_codeline_highlights(codeline)
    return changed


def merge_userdefined_sections(compounddef) -> bool:
    """Doxygen emits a separate <sectiondef> per user-defined section even when several share the
    same header; merge those with identical header text into the first one."""
    changed = False
    sectiondefs = [s for s in compounddef.findall(r'sectiondef') if s.get(r'kind') == r'user-defined']
    sections_with_headers = dict()
    for section in sectiondefs:
        header = section.find(r'header')
        if header is not None and header.text:
            if header.text not in sections_with_headers:
                sections_with_headers[header.text] = []
            sections_with_headers[header.text].append(section)
    for key, vals in sections_with_headers.items():
        if len(vals) > 1:
            first_section = vals.pop(0)
            for section in vals:
                for member in section.findall(r'memberdef'):
                    section.remove(member)
                    first_section.append(member)
                compounddef.remove(section)
                changed = True
    return changed


def sort_userdefined_sections(compounddef) -> bool:
    """Sort user-defined sections (those with a <header>) by their header text, so their order is
    deterministic rather than dependent on Doxygen's emission order."""
    changed = False
    sectiondefs = [s for s in compounddef.findall(r'sectiondef') if s.get(r'kind') == r'user-defined']
    sectiondefs = [s for s in sectiondefs if s.find(r'header') is not None]
    for section in sectiondefs:
        compounddef.remove(section)
    sectiondefs.sort(key=lambda s: s.find(r'header').text)
    for section in sectiondefs:
        compounddef.append(section)
        changed = True
    return changed


def remove_duplicate_members(section) -> bool:
    """Remove <memberdef> entries Doxygen lists more than once (same id) within a section."""
    changed = False
    members = [tag for tag in section.findall(r'memberdef')]
    for i in range(len(members) - 1, 0, -1):
        for j in range(i):
            if members[i].get(r'id') == members[j].get(r'id'):
                section.remove(members[i])
                changed = True
                break
    return changed


def fix_leaked_keywords(section) -> bool:
    """Strip declaration keywords (constexpr, static, friend, virtual, ...) that Doxygen leaks into
    the member <type>, promoting them to their proper attributes instead."""
    changed = False
    members = [m for m in section.findall(r'memberdef') if m.get(r'kind') in (r'friend', r'function', r'variable')]

    attribute_keywords = (
        (r'constexpr', r'constexpr', r'yes'),  #
        (r'constinit', r'constinit', r'yes'),
        (r'consteval', r'consteval', r'yes'),
        (r'explicit', r'explicit', r'yes'),
        (r'static', r'static', r'yes'),
        (r'friend', None, None),
        (r'extern', None, None),
        (r'inline', r'inline', r'yes'),
        (r'virtual', r'virt', r'virtual'),
    )
    for member in members:
        type = member.find(r'type')
        if type is None or type.text is None:
            continue
        matched_bad_keyword = True
        while matched_bad_keyword:
            matched_bad_keyword = False
            for kw, attr, attr_value in attribute_keywords:
                if type.text == kw:  # constructors
                    type.text = ''
                elif type.text.startswith(kw + ' '):
                    type.text = type.text[len(kw) :].strip()
                elif type.text.endswith(' ' + kw):
                    type.text = type.text[: len(kw)].strip()
                else:
                    continue
                matched_bad_keyword = True
                changed = True
                if attr is not None:
                    member.set(attr, attr_value)
                if kw == r'friend' and type.text == r'' and member.get(r'kind') == r'variable':
                    type.text = r'friend'
                    matched_bad_keyword = False
                    break
    return changed


def fix_trailing_return_types(section) -> bool:
    """Fix Doxygen's mangling of trailing return types: the '-> void -> auto' bug
    (https://github.com/mosra/m.css/issues/94) and 'auto foo() -> auto' redundancy
    (https://github.com/marzer/poxy/issues/26)."""
    changed = False
    members = [m for m in section.findall(r'memberdef') if m.get(r'kind') in (r'friend', r'function')]

    for member in members:
        type_elem = member.find(r'type')
        if type_elem is None or type_elem.text != r'auto':
            continue
        args_elem = member.find(r'argsstring')
        if args_elem is None or not args_elem.text or args_elem.text.find(r'decltype') != -1:
            continue

        # fix "-> void -> auto" bug (https://github.com/mosra/m.css/issues/94)
        match = re.search(r'^(.*?)\s*->\s*([a-zA-Z][a-zA-Z0-9_::*&<>\s]+?)\s*$', args_elem.text)
        if match:
            args_elem.text = str(match[1])
            trailing_return_type = str(match[2]).strip()
            trailing_return_type = re.sub(r'\s+', r' ', trailing_return_type)
            trailing_return_type = re.sub(r'(::|[<>*&])\s+', r'\1', trailing_return_type)
            trailing_return_type = re.sub(r'\s+(::|[<>*&])', r'\1', trailing_return_type)
            type_elem.text = trailing_return_type
            # newer doxygen resolves the trailing type into <definition> too ('int test::f' not 'auto test::f');
            # mirror that so the definition string converges across versions
            def_elem = member.find(r'definition')
            if def_elem is not None and def_elem.text and def_elem.text.startswith(r'auto '):
                def_elem.text = trailing_return_type + def_elem.text[len(r'auto') :]
            changed = True
            continue

        # fix "auto foo() -> auto" redundancy (https://github.com/marzer/poxy/issues/26)
        if args_elem.text == r'()':
            type_elem.text = DEDUCED_AUTO_RETURN_TYPE
            changed = True
            continue
    return changed


def normalize_member_definitions(section) -> bool:
    """Iron out older-doxygen <definition>/<location> string quirks so they match newer versions:
    - a leading 'constexpr ' (already captured as an attribute; newer doxygen drops it from the string,
      but keeps it mid-string as in 'static constexpr')
    - the redundant 'typedef' in a 'using X = typedef Y' alias definition
    - bodyend="-1" on a single-line body (newer doxygen emits the real line, which equals bodystart)
    """
    changed = False
    for member in section.findall(r'memberdef'):
        def_elem = member.find(r'definition')
        if def_elem is not None and def_elem.text:
            new_text = re.sub(r'^(?:constexpr|consteval|constinit)\s+', r'', def_elem.text)
            if member.get(r'kind') == r'typedef':
                # alias form drifted across versions: '= typedef int' (<=1.9.x), '=  int' (1.14/1.15),
                # '= int' (1.16+). normalise all to the clean single-space form.
                new_text = re.sub(r'=\s+(?:typedef\s+)?', r'= ', new_text)
            if new_text != def_elem.text:
                def_elem.text = new_text
                changed = True
        loc = member.find(r'location')
        if loc is not None and loc.get(r'bodyend') == r'-1' and loc.get(r'bodystart'):
            loc.set(r'bodyend', loc.get(r'bodystart'))
            changed = True
    return changed


def add_concept_includes(compounddef, includes_template) -> bool:
    """Back-fill a concept's <includes> from a sibling compound in the same file. Doxygen 1.9.7/1.9.8
    dropped <includes> for concepts nested in a sub-namespace; newer/older versions keep it. Inserts a
    copy right after <compoundname> (doxygen's position) when the concept has none."""
    if compounddef.find(r'includes') is not None:
        return False
    name = compounddef.find(r'compoundname')
    if name is None:
        return False
    includes = copy.deepcopy(includes_template)
    includes.tail = name.tail
    compounddef.insert(list(compounddef).index(name) + 1, includes)
    return True


def normalize_concept_definition(compounddef) -> bool:
    """Iron out concept <compounddef> differences across doxygen versions:
    - rstrip the trailing whitespace newer versions trim from the <initializer> body
    - drop the <conceptparts> token dump (1.16+); nothing consumes it and the concept's full
      definition, with cross-link refs, is already carried by <initializer>
    """
    changed = False
    init = compounddef.find(r'initializer')
    if init is not None:
        # the trailing whitespace lives on the last child's tail (the body ends in a <ref>), or on
        # .text when the initializer has no element children
        children = list(init)
        node, attr = (children[-1], r'tail') if children else (init, r'text')
        text = getattr(node, attr)
        if text:
            stripped = text.rstrip()
            if stripped != text:
                setattr(node, attr, stripped)
                changed = True
    for parts in compounddef.findall(r'conceptparts'):
        compounddef.remove(parts)
        changed = True
    return changed


def resort_members(section, compound_kind) -> bool:
    """Re-sort a section's members into poxy's preferred grouping/order, overriding Doxygen's own
    sorting rules (defines, typedefs, concepts, enums, variables, functions, friends)."""
    changed = False

    # sort_members_by_name = lambda tag: tag.find(r'name').text
    def sort_members_by_name(tag):
        n = tag.find(r'name')
        if n is None:
            return ''
        return '' if n.text is None else n.text

    members = [tag for tag in section.findall(r'memberdef')]
    for tag in members:
        section.remove(tag)
    # fmt: off
    groups = [
        ([tag for tag in members if tag.get(r'kind') == r'define'], True),  #
        ([tag for tag in members if tag.get(r'kind') == r'typedef'], True),
        ([tag for tag in members if tag.get(r'kind') == r'concept'], True),
        ([tag for tag in members if tag.get(r'kind') == r'enum'], True),
        ([tag for tag in members if tag.get(r'kind') == r'variable' and tag.get(r'static') == r'yes'], True),
        ([tag for tag in members if tag.get(r'kind') == r'variable' and tag.get(r'static') == r'no'], compound_kind not in (r'class', r'struct', r'union')),
        ([tag for tag in members if tag.get(r'kind') == r'function' and tag.get(r'static') == r'yes'], True),
        ([tag for tag in members if tag.get(r'kind') == r'function' and tag.get(r'static') == r'no'], True),
        ([tag for tag in members if tag.get(r'kind') == r'friend'], True)
    ]
    # fmt: on
    for group, sort in groups:
        if sort:
            group.sort(key=sort_members_by_name)
        for tag in group:
            members.remove(tag)
            section.append(tag)
            changed = True
    # if we've missed any groups just glob them on the end
    if members:
        members.sort(key=sort_members_by_name)
        changed = True
        for tag in members:
            section.append(tag)
    return changed


def _resolve_type_name(name: str, type_ids_by_name: dict, scope: str):
    # exact match handles already-qualified names; otherwise do a C++-style outward scope lookup
    if name in type_ids_by_name:
        return type_ids_by_name[name]
    parts = [p for p in scope.split(r'::') if p] if scope else []
    while parts:
        candidate = r'::'.join(parts) + r'::' + name
        if candidate in type_ids_by_name:
            return type_ids_by_name[candidate]
        parts.pop()
    return None


def resolve_plain_type_references(compounddef, type_ids_by_name: dict, scope: str) -> bool:
    """Some doxygen versions (e.g. 1.15.0) emit a member's <type> as plain text even when it names a
    documented type, where earlier versions wrapped it in a <ref>. Re-link a bare, child-free <type> that
    resolves by C++-style scope lookup to a documented class/struct/union/concept, so the cross-reference
    is present regardless of doxygen version. Conservative: only a single (optionally-qualified) identifier
    is considered, never a compound type expression we can't safely resolve."""
    if not type_ids_by_name:
        return False
    changed = False
    for member in compounddef.findall(r'sectiondef/memberdef'):
        type_elem = member.find(r'type')
        if type_elem is None or len(type_elem) or not type_elem.text:
            continue
        name = type_elem.text.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*', name):
            continue
        refid = _resolve_type_name(name, type_ids_by_name, scope)
        if refid is None:
            continue
        type_elem.text = None
        ref = type_elem.makeelement(r'ref', {r'refid': refid, r'kindref': r'compound'})
        ref.text = name
        type_elem.append(ref)
        changed = True
    return changed


def set_innerconcept_prot(compounddef) -> bool:
    """Normalise the prot attribute on <innerconcept> refs. Some doxygen versions emit them natively
    without prot while others (or poxy's own concept back-fill) tag them prot="public"; concepts at
    namespace scope are always public, so force it for convergence."""
    changed = False
    for tag in compounddef.findall(r'innerconcept'):
        if tag.get(r'prot') != r'public':
            tag.set(r'prot', r'public')
            changed = True
    return changed


def sort_inner_refs(compounddef) -> bool:
    """Sort inner(class|namespace|group|concept) references by their text, since Doxygen's ordering
    of these is not stable/sensible."""
    changed = False
    inners = [tag for tag in compounddef.iterchildren() if tag.tag.startswith(r'inner')]
    if inners:
        changed = True
        for tag in inners:
            compounddef.remove(tag)
        inners.sort(key=lambda tag: tag.text)
        for tag in inners:
            compounddef.append(tag)
    return changed


def normalize_section_titles(compounddef) -> bool:
    """
    m.css renders a section heading as plain text via html.escape(title.text). If the heading begins with
    inline markup (e.g. a `code` span) or is empty, title.text is None and m.css crashes; if inline markup
    appears mid-heading, m.css silently truncates the heading at the first child element.

    So flatten each rich section <title> to a single plain-text string. Inline code spans (<computeroutput>,
    i.e. markdown backticks) are preserved by wrapping their text in sentinels that survive m.css unscathed
    and are turned back into <code> in the HTML by the SectionTitleCodeSpans fixer; other inline markup is
    flattened to its text content.
    """
    changed = False
    for level in (r'sect1', r'sect2', r'sect3', r'sect4', r'sect5', r'sect6'):
        for sect in compounddef.iter(level):
            title = sect.find(r'title')
            if title is None:
                continue
            if not len(title) and title.text is not None:
                continue  # already a plain-text heading, leave it alone
            parts = [title.text] if title.text else []
            for child in title:
                content = ''.join(child.itertext())
                if child.tag == r'computeroutput':
                    parts.append(SECTION_TITLE_CODE_BEGIN + content + SECTION_TITLE_CODE_END)
                else:
                    parts.append(content)
                if child.tail:
                    parts.append(child.tail)
            for child in list(title):
                title.remove(child)
            title.text = ''.join(parts)
            changed = True
    return changed


_SECTION_PROMOTION = {
    r'sect2': r'sect1',
    r'sect3': r'sect2',
    r'sect4': r'sect3',
    r'sect5': r'sect4',
    r'sect6': r'sect5',
}


def unwrap_synthetic_page_sections(compounddef) -> bool:
    """When a markdown page's first heading (H1) becomes the page title, Doxygen wraps each subsequent
    top-level H2 in a synthetic titleless <sect1> (id '..._1s1'). m.css renders that as an empty TOC entry
    (<a href="#"></a>) nesting the real heading a level deeper, and bumps every heading down one level.
    Unwrap each such wrapper and promote its nested sections up a level (sect2->sect1, sect3->sect2, ...)."""
    dd = compounddef.find(r'detaileddescription')
    if dd is None:
        return False
    changed = False
    for sect1 in dd.findall(r'sect1'):
        if sect1.find(r'title') is not None or sect1.find(r'sect2') is None:
            continue
        for elem in sect1.iter():
            if elem is not sect1 and elem.tag in _SECTION_PROMOTION:
                elem.tag = _SECTION_PROMOTION[elem.tag]
        idx = list(dd).index(sect1)
        children = list(sect1)
        if children:
            children[-1].tail = sect1.tail
        for offset, child in enumerate(children):
            dd.insert(idx + offset, child)
        dd.remove(sect1)
        changed = True
    return changed


def fix_nested_tableofcontents(compounddef) -> bool:
    """Flatten Doxygen's redundant <tableofcontents><tableofcontents>...</...></...> nesting on pages."""
    changed = False
    while True:
        tocs = compounddef.findall(r'tableofcontents')
        tocs = [t for t in tocs if len(t) == 1 and t[0].tag == r'tableofcontents']
        tocs = [t for t in tocs if t.getparent() is not None and t.getparent().tag != r'tableofcontents']
        if not tocs:
            break
        for toc in tocs:
            toc_parent = toc.getparent()
            toc_index = toc_parent.getchildren().index(toc)
            assert toc_index >= 0
            toc_child = toc[0]
            toc_parent.remove(toc)
            toc_parent.insert(toc_index, toc_child)
            changed = True
    return changed


def split_paragraphs_around_tables(compounddef) -> bool:
    """Give every <table> a <para> of its own. Most doxygen versions close the enclosing paragraph before
    a markdown table and open a fresh one for it, but 1.10.0 - 1.12.0 leave the table inline in the
    paragraph that preceded it."""
    changed = False
    for para in list(compounddef.iter(r'para')):
        parent = para.getparent()
        if parent is None or not any(child.tag == r'table' for child in para):
            continue

        segments = []
        text = para.text
        children = []
        for child in list(para):
            if child.tag != r'table':
                children.append(child)
                continue
            segments.append((text, children))
            text = child.tail
            child.tail = None
            segments.append((None, [child]))
            children = []
        segments.append((text, children))

        paras = []
        for seg_text, seg_children in segments:
            if not seg_children and not (seg_text or r'').strip():
                continue
            new_para = para.makeelement(r'para', {})
            new_para.text = seg_text
            for child in seg_children:
                new_para.append(child)
            if len(new_para):
                last = new_para[-1]
                if last.tail is not None and not last.tail.strip():
                    last.tail = None
            paras.append(new_para)

        index = parent.index(para)
        tail = para.tail
        parent.remove(para)
        for offset, new_para in enumerate(paras):
            new_para.tail = tail
            parent.insert(index + offset, new_para)
        changed = True
    return changed


def strip_toc_section_docs(compounddef) -> bool:
    """Drop the <docs> child doxygen 1.14+ adds to each <tocsect>. It just repeats the sibling <name>,
    and m.css reads only <name>/<reference> plus the nesting depth, so it is pure divergence."""
    changed = False
    for tocsect in compounddef.iter(r'tocsect'):
        for docs in tocsect.findall(r'docs'):
            tocsect.remove(docs)
            changed = True
    return changed


_LEADING_LIST_BULLET = re.compile(r'^\s*[-*+]\s+')
_LEADING_LIST_BLOCK_TAGS = (
    r'para',
    r'itemizedlist',
    r'orderedlist',
    r'simplesect',
    r'parameterlist',
    r'variablelist',
    r'table',
    r'programlisting',
    r'blockquote',
    r'verbatim',
    r'xrefsect',
)


def fix_leading_list_item(compounddef) -> bool:
    """Repair a markdown list whose first item shares the opening line of a block command, e.g.

        @see - @ref foo
             - @ref bar

    Doxygen only treats '-' as a list marker at the start of a line, so the first item is left inline as
    literal '- ...' text directly followed by an <itemizedlist> holding the rest. Fold that leading inline
    content into a new first <listitem> so the whole block renders as one list."""
    changed = False
    for para in list(compounddef.iter(r'para')):
        m = _LEADING_LIST_BULLET.match(para.text) if para.text else None
        if m is None:
            continue
        # the missed first item is the inline content up to the first <itemizedlist>; bail if a block
        # element gets in the way (then the leading bullet is something else, not a split-off list item)
        il = None
        for child in para:
            if child.tag == r'itemizedlist':
                il = child
                break
            if child.tag in _LEADING_LIST_BLOCK_TAGS:
                break
        if il is None:
            continue
        new_item = para.makeelement(r'listitem', {})
        new_para = para.makeelement(r'para', {})
        new_item.append(new_para)
        new_para.text = para.text[m.end() :] or None
        moved = []
        for child in list(para):
            if child is il:
                break
            para.remove(child)
            new_para.append(child)
            moved.append(child)
        # tidy trailing whitespace that used to sit between the first item and the list
        if moved:
            if moved[-1].tail and not moved[-1].tail.strip():
                moved[-1].tail = None
        elif new_para.text and not new_para.text.strip():
            new_para.text = None
        elif new_para.text:
            new_para.text = new_para.text.rstrip() or None
        para.text = None
        il.insert(0, new_item)
        changed = True
    return changed


def strip_duplicated_ref_text(compounddef) -> bool:
    """Drop the copy of a <ref>'s own label that doxygen 1.17.0 leaves sitting in its tail. Only markdown
    in-page anchor links ('[text](#anchor)') are affected; '@ref' and cross-page links are not."""
    changed = False
    for ref in compounddef.iter(r'ref'):
        text = ref.text
        if not text or not ref.tail or not ref.tail.startswith(text):
            continue
        ref.tail = ref.tail[len(text) :] or None
        changed = True
    return changed


def strip_table_cell_padding(compounddef) -> bool:
    """Trim the whitespace doxygen carries over from a markdown table's cell padding into <entry><para>.
    How much of it survives depends on the version (1.13.2 keeps one more space than 1.14.0 for the same
    '| option |' cell), and it renders as nothing either way."""
    changed = False
    for entry in compounddef.iter(r'entry'):
        for para in entry.findall(r'para'):
            if para.text and para.text != para.text.lstrip():
                para.text = para.text.lstrip() or None
                changed = True
            children = list(para)
            node, attr = (children[-1], r'tail') if children else (para, r'text')
            text = getattr(node, attr)
            if text and text != text.rstrip():
                setattr(node, attr, text.rstrip() or None)
                changed = True
    return changed


def strip_trailing_paragraph_linebreaks(compounddef) -> bool:
    """Drop a <linebreak/> sitting at the very end of a <para> (last child, whitespace-only tail). A line
    break immediately before the paragraph closes renders nothing, but doxygen 1.11.0 emits one at the end
    of a detailed description's final paragraph (e.g. after a trailing block command) where other versions
    do not, so strip it for convergence."""
    changed = False
    for para in list(compounddef.iter(r'para')):
        while len(para):
            last = para[-1]
            if last.tag != r'linebreak' or (last.tail and last.tail.strip()):
                break
            para.remove(last)
            changed = True
    return changed
