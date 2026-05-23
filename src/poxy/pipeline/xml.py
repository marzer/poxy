#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
The Doxygen-XML preprocessing stage of the poxy pipeline.

This is poxy's "man-in-the-middle" layer: it rewrites Doxygen's XML to iron out the quirks and
version-to-version differences before m.css ever sees it. Extracted verbatim from run.py; the
internals are slated to be restructured into discrete, individually-named fixes.
"""

import copy
import os
import typing

from lxml import etree
from trieregex import TrieRegEx

from .. import doxygen, graph, xml_utils
from ..project import Context
from ..utils import *
from ..xml_utils import require
from . import fixups


def relink_implementation_header_refs(xml_text: str, iid: str, hid: str, impl_path: str, header_path: str) -> str:
    """
    Re-home a merged-away implementation header onto its public header within one XML file's text.

    When an implementation header's compound (id `iid`, path `impl_path`) is merged into the public header
    (`hid`, `header_path`) and then deleted, the result should read as if the definitions had always lived in
    the public header - no reference to the old compound may survive. We rewrite:
      - <compoundref>/<refid> that point at the old file compound,
      - file-scoped member <id>s and every <refid> to them (these are prefixed with the old compound id; the
        leading quote anchors the match to the start of an id value so a longer compound id that merely shares
        the prefix is never corrupted),
      - the source path.

    The <doxygenindex>'s own `<compound kind="file" refid="{iid}">` entries are NOT relinked here (that would
    duplicate the public header in the file list); they are folded into the public header's entry beforehand by
    fold_implementation_header_index_entries.
    """
    xml_text = xml_text.replace(rf'compoundref="{iid}"', rf'compoundref="{hid}"')
    xml_text = xml_text.replace(rf'refid="{iid}"', rf'refid="{hid}"')
    xml_text = xml_text.replace(rf'"{iid}_1', rf'"{hid}_1')
    xml_text = xml_text.replace(impl_path, header_path)
    return xml_text


def fold_implementation_header_index_entries(index_root, public_id_by_impl_id: dict) -> bool:
    """
    Fold each implementation header's <doxygenindex> entry into its public header's entry: move the impl
    header's <member>s onto the public header's <compound> and drop the impl entry, so the index reads as if
    the definitions had always lived in the public header (no dangling file compound in the "Files" list).

    `public_id_by_impl_id` maps an implementation-header compound id to its public-header compound id.
    """
    changed = False
    compounds_by_id = {c.get(r'refid'): c for c in index_root.findall(r'compound')}
    for compound in list(index_root.findall(r'compound')):
        hid = public_id_by_impl_id.get(compound.get(r'refid'))
        if hid is None:
            continue
        target = compounds_by_id.get(hid)
        if target is not None:
            for member in compound.findall(r'member'):
                compound.remove(member)
                target.append(member)
        index_root.remove(compound)
        changed = True
    return changed


def fold_implementation_headers_in_tagfile(tagfile_root, implementation_header_data) -> bool:
    """
    Apply the implementation-header merge to the doxygen tagfile so it, too, reads as if the definitions had
    always lived in the public header (otherwise a downstream project consuming the tagfile gets broken links
    to the merged-away implementation pages). For each impl header we:
      - fold its <compound kind="file"> into the public header's (moving members/classes/namespaces, de-duping
        the class/namespace cross-refs) and drop the impl entry,
      - drop now-meaningless <includes> of the merged-away headers,
      - remap page references (<filename>/<anchorfile>) from the impl page to the public page.
    """
    changed = False
    impl_ids = set()
    page_remap = {}
    for _, _, hid, impls in implementation_header_data:
        for _, _, iid in impls:
            impl_ids.add(iid)
            page_remap[rf'{iid}.html'] = rf'{hid}.html'

    file_compounds = {}
    for compound in tagfile_root.findall(r'compound'):
        if compound.get(r'kind') != r'file':
            continue
        fn = compound.find(r'filename')
        if fn is not None and fn.text:
            file_compounds[fn.text] = compound

    movable = (r'member', r'class', r'namespace', r'concept')
    for _, _, hid, impls in implementation_header_data:
        target = file_compounds.get(rf'{hid}.html')
        for _, _, iid in impls:
            src = file_compounds.get(rf'{iid}.html')
            if src is None:
                continue
            if target is not None:
                existing = {(c.tag, c.text) for c in target}
                for child in list(src):
                    if child.tag not in movable:
                        continue
                    if child.tag != r'member' and (child.tag, child.text) in existing:
                        continue  # de-dupe class/namespace cross-refs
                    src.remove(child)
                    target.append(child)
                    existing.add((child.tag, child.text))
            tagfile_root.remove(src)
            changed = True

    for compound in tagfile_root.findall(r'compound'):
        for inc in list(compound.findall(r'includes')):
            if inc.get(r'id') in impl_ids:
                compound.remove(inc)
                changed = True

    for elem in tagfile_root.iter():
        if elem.tag in (r'filename', r'anchorfile') and elem.text in page_remap:
            elem.text = page_remap[elem.text]
            changed = True

    return changed


def normalize_tagfile(tagfile_root) -> bool:
    """
    Normalise a doxygen tagfile for version-independence:
      - drop <compound kind="dir"> entries (directory cross-refs that some doxygen versions emit and
        others don't; they are noise to a tagfile consumer)
      - strip namespace members that older doxygen (<=1.9.x) also duplicates into the owning file
        compound; modern doxygen lists them only in the namespace compound (the file keeps its #defines
        plus a <namespace> backref). every member stays tag-linkable via the namespace compound.
      - sort each compound's inner namespace/class/concept refs by name, since doxygen's ordering of
        these is version-dependent
    """
    changed = False
    # capture the closing whitespace (the last child's tail sits before </tagfile>) so we can restore it
    # after removing trailing dir compounds, otherwise the previous compound's inter-element tail leaks out
    children = list(tagfile_root)
    closing_tail = children[-1].tail if children else None
    for compound in list(tagfile_root.findall(r'compound')):
        if compound.get(r'kind') == r'dir':
            tagfile_root.remove(compound)
            changed = True
    if changed:
        remaining = list(tagfile_root)
        if remaining and closing_tail is not None:
            remaining[-1].tail = closing_tail

    # de-duplicate namespace members out of file compounds (keyed on (anchorfile, anchor), which a
    # genuinely file-scoped #define never shares with a namespace member)
    namespace_member_keys = set()
    for compound in tagfile_root.findall(r'compound'):
        if compound.get(r'kind') != r'namespace':
            continue
        for member in compound.findall(r'member'):
            anchor = member.findtext(r'anchor')
            if anchor:
                namespace_member_keys.add((member.findtext(r'anchorfile'), anchor))
    if namespace_member_keys:
        for compound in tagfile_root.findall(r'compound'):
            if compound.get(r'kind') != r'file':
                continue
            kids = list(compound)
            compound_tail = kids[-1].tail if kids else None
            removed = False
            for member in compound.findall(r'member'):
                if (member.findtext(r'anchorfile'), member.findtext(r'anchor')) in namespace_member_keys:
                    compound.remove(member)
                    removed = True
            if removed:
                changed = True
                kids = list(compound)
                if kids and compound_tail is not None:
                    kids[-1].tail = compound_tail
    for compound in tagfile_root.findall(r'compound'):
        for tag_name in (r'namespace', r'class', r'concept'):
            refs = compound.findall(tag_name)
            if len(refs) < 2:
                continue
            ordered = sorted(refs, key=lambda e: e.text or r'')
            if ordered == refs:
                continue
            idx = list(compound).index(refs[0])
            for r in refs:
                compound.remove(r)
            for i, r in enumerate(ordered):
                compound.insert(idx + i, r)
            changed = True
    return changed


def resolve_implementation_headers(configured, file_id_by_location: dict) -> list:
    """
    Resolve the configured implementation_headers against doxygen's real file compounds.

    `configured` is the list of (header_path, [impl_pattern, ...]) from the project config; `file_id_by_location`
    maps each documented file's <location> to its doxygen compound id. Each header/impl path is matched by
    location (impl patterns may contain '*' wildcards), and resolved to that compound's actual id.

    This is robust regardless of directory layout: doxygen's file-compound ids depend on STRIP_FROM_PATH
    (basename in some layouts, path-qualified in others), but <location> is always the relative source path.
    The previous approach guessed mangle(basename(path)) and silently failed whenever the id was path-qualified.

    Returns a list of (header_path, header_basename, header_id, [(impl_path, impl_basename, impl_id), ...]) for
    each public header that matched at least one implementation file. Raises Error if an implementation file is
    assigned to more than one public header.
    """

    def match_locations(pattern: str) -> list:
        if pattern.find(r'*') == -1:
            return [pattern] if pattern in file_id_by_location else []
        rx = re.sub(r'[*][*]+', r'*', pattern)
        rx = rx.replace(r'*', '\x00')
        rx = re.escape(rx)
        rx = rx.replace('\x00', r'''[^<>:"'|?*\^]*''')
        return sorted(loc for loc in file_id_by_location if re.fullmatch(rx, loc))

    data = []
    impl_owner = dict()  # impl location -> owning header path (to detect conflicting assignments)
    for header_path, impl_patterns in configured:
        header_id = file_id_by_location.get(header_path)
        if header_id is None:
            continue
        impls = []
        seen = set()
        for pattern in impl_patterns:
            for loc in match_locations(pattern):
                if loc == header_path or loc in seen:
                    continue
                if impl_owner.get(loc, header_path) != header_path:
                    raise Error(
                        rf"implementation_headers: '{loc}' is assigned to both "
                        rf"'{impl_owner[loc]}' and '{header_path}'"
                    )
                seen.add(loc)
                impl_owner[loc] = header_path
                impls.append((loc, os.path.basename(loc), file_id_by_location[loc]))
        if impls:
            data.append((header_path, os.path.basename(header_path), header_id, sorted(impls)))
    return data


def preprocess_xml(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    xml_files = [f for f in get_all_files(context.temp_xml_dir, any=(r'*.xml')) if f.name.lower() != r'doxyfile.xml']
    if not xml_files:
        return

    context.verbose(rf'Post-processing {len(xml_files) + len(context.tagfiles)} XML files...')

    # resolve implementation headers against doxygen's actual file compounds (matched by <location>),
    # so the compound ids we work with are doxygen's real ids regardless of directory layout / mangling.
    implementation_header_data = None
    implementation_header_mappings = dict()
    implementation_header_innernamespaces = dict()
    implementation_header_sectiondefs = dict()
    implementation_header_unused_keys = set()
    implementation_header_unused_values = dict()
    if context.implementation_headers:
        file_id_by_location = dict()
        for xml_file in xml_files:
            root = xml_utils.read(xml_file)
            if root.tag != r'doxygen':
                continue
            compounddef = root.find(r'compounddef')
            if compounddef is None or compounddef.get(r'kind') != r'file':
                continue
            location = compounddef.find(r'location')
            location = location.get(r'file') if location is not None else None
            cid = compounddef.get(r'id')
            if location and cid:
                file_id_by_location[location] = cid

        implementation_header_data = resolve_implementation_headers(context.implementation_headers, file_id_by_location)
        context.verbose_value(r'implementation_header_data', implementation_header_data)

        resolved_headers = {hp for hp, _, _, _ in implementation_header_data}
        for hp, _ in context.implementation_headers:
            if hp not in resolved_headers:
                context.warning(rf"implementation_headers: nothing matched for '{hp}'")

        if not implementation_header_data:
            implementation_header_data = None
        else:
            implementation_header_unused_keys = set(hp for hp, _, _, _ in implementation_header_data)
            implementation_header_unused_values = dict()
            implementation_header_mappings = dict()
            implementation_header_innernamespaces = dict()
            implementation_header_sectiondefs = dict()
            for hdata in implementation_header_data:
                implementation_header_innernamespaces[hdata[2]] = []
                implementation_header_sectiondefs[hdata[2]] = []
                for ip, ifn, iid in hdata[3]:
                    implementation_header_unused_values[iid] = (ip, hdata[0])
                    implementation_header_mappings[iid] = hdata

    # local alias for the same dict stored on context (Context doesn't declare 'compounds' up front);
    # downstream stages read context.compounds, so keep storing it there
    compounds = dict()
    typing.cast(typing.Any, context).compounds = compounds
    context.compound_pages = dict()
    context.compound_kinds = set()

    inline_namespace_ids = []
    if context.inline_namespaces:
        inline_namespace_ids = [f'namespace{doxygen.mangle_name(ns)}' for ns in context.inline_namespaces]

    # process xml files
    if 1:
        # pre-pass to delete junk files
        if 1:
            # 'file' entries for markdown and dox files
            dox_files = [rf'*{doxygen.mangle_name(ext)}.xml' for ext in (r'.dox', r'.md')]
            dox_files.append(r'md_home.xml')
            for xml_file in get_all_files(context.temp_xml_dir, any=dox_files):
                delete_file(xml_file, logger=context.verbose_logger)

            # 'dir' entries for empty directories
            deleted = True
            while deleted:
                deleted = False
                for xml_file in get_all_files(context.temp_xml_dir, all=(r'dir*.xml')):
                    root = xml_utils.read(xml_file)
                    compounddef = root.find(r'compounddef')
                    if compounddef is None or compounddef.get(r'kind') != r'dir':
                        continue
                    existing_inners = 0
                    for subtype in (r'innerfile', r'innerdir'):
                        for inner in compounddef.findall(subtype):
                            ref_file = Path(context.temp_xml_dir, rf'{inner.get(r"refid")}.xml')
                            if path_exists(ref_file):
                                existing_inners = existing_inners + 1
                    if not existing_inners:
                        delete_file(xml_file, logger=context.verbose_logger)
                        deleted = True

        extracted_implementation = False
        xml_files = [
            f for f in get_all_files(context.temp_xml_dir, any=(r'*.xml')) if f.name.lower() != r'doxyfile.xml'
        ]
        all_inners_by_type = {r'namespace': set(), r'class': set(), r'concept': set()}
        # for back-filling <innerconcept> into file compounds: concept location -> [(id, name), ...]
        # and file location -> file compound id (newer doxygen lists concepts in files, older doesn't)
        concepts_by_file_location = dict()
        file_id_by_location = dict()
        # an <includes> template per source file, so a concept that lost it (doxygen 1.9.7/1.9.8 dropped
        # <includes> for concepts nested in a sub-namespace) can be back-filled from a sibling compound
        includes_by_file_location = dict()

        # do '<doxygenindex>' first
        for xml_file in xml_files:
            root = xml_utils.read(xml_file)
            if root.tag != r'doxygenindex':
                continue

            context.verbose(rf'Post-processing {xml_file}')
            changed = False

            # fold implementation-header file entries into their public header
            if implementation_header_mappings:
                changed |= fold_implementation_header_index_entries(
                    root, {iid: hdata[2] for iid, hdata in implementation_header_mappings.items()}
                )

            # remove entries for files we might have explicitly deleted above
            for compound in [
                tag for tag in root.findall(r'compound') if tag.get(r'kind') in (r'file', r'dir', r'concept')
            ]:
                ref_file = Path(context.temp_xml_dir, rf'{compound.get(r"refid")}.xml')
                if not path_exists(ref_file):
                    root.remove(compound)
                    changed = True

            # enumerate all compound pages and their types for later (e.g. HTML post-process)
            for tag in root.findall(r'compound'):
                refid = require(tag.get(r'refid')).strip()
                assert refid
                filename = refid
                if refid == r'indexpage':
                    filename = r'index'
                filename = filename + r'.html'
                title = tag.find(r'title')
                compounds[refid] = {
                    r'refid': refid,
                    r'filename': filename,
                    r'kind': tag.get(r'kind'),
                    r'name': require(tag.find(r'name')).text,
                    r'title': require(title.text).strip() if title is not None else r'',
                }
                context.compound_pages[filename] = compounds[refid]
                context.compound_kinds.add(tag.get(r'kind'))

            if changed:
                xml_utils.write(root, xml_file)

        # some doxygen versions emit member references m.css can't resolve; poxy resolves them itself
        if doxygen.has_unresolved_member_references():
            member_references = dict()

            # collect all the unresolved references
            for xml_file in xml_files:
                root = xml_utils.read(xml_file)
                if root.tag != r'doxygen':
                    continue
                compounddef = root.find(r'compounddef')
                if compounddef is None:
                    continue
                compound_kind = compounddef.get(r'kind')
                if compound_kind is None or not compound_kind or compound_kind not in (r'file', r'namespace'):
                    continue
                for sectiondef in compounddef.findall(r'sectiondef'):
                    for member in sectiondef.findall(r'member'):
                        refid = member.get(r'refid')
                        if refid is not None:
                            refid = str(refid)
                        if refid and refid not in member_references:
                            member_references[refid] = None

            if member_references:
                # resolve
                for xml_file in xml_files:
                    root = xml_utils.read(xml_file)
                    if root.tag != r'doxygen':
                        continue
                    compounddef = root.find(r'compounddef')
                    if compounddef is None:
                        continue
                    for sectiondef in compounddef.findall(r'sectiondef'):
                        for memberdef in sectiondef.findall(r'memberdef'):
                            id = memberdef.get(r'id')
                            if id is not None:
                                id = str(id)
                            if id and id in member_references and member_references[id] is None:
                                member_references[id] = memberdef
                for id, memberdef in member_references.items():
                    if memberdef is None:
                        context.warning(rf"could not resolve <member> reference with id '{id}'!")

                # replace
                for xml_file in xml_files:
                    root = xml_utils.read(xml_file)
                    if root.tag != r'doxygen':
                        continue
                    compounddef = root.find(r'compounddef')
                    if compounddef is None:
                        continue
                    compound_kind = compounddef.get(r'kind')
                    if compound_kind is None or not compound_kind or compound_kind not in (r'file', r'namespace'):
                        continue
                    changed = False
                    for sectiondef in compounddef.findall(r'sectiondef'):
                        replacements = []
                        for member in sectiondef.findall(r'member'):
                            refid = member.get(r'refid')
                            if refid is not None:
                                refid = str(refid)
                            if refid and refid in member_references and member_references[refid] is not None:
                                replacements.append((member, member_references[refid]))
                        for member, memberdef in replacements:
                            sectiondef.replace(member, copy.deepcopy(memberdef))
                            changed = True
                    if changed:
                        xml_utils.write(root, xml_file)

        # documented types we can re-link a plain-text <type> to (see resolve_plain_type_references)
        type_ids_by_name = {
            data[r'name']: refid
            for refid, data in compounds.items()
            if data.get(r'kind') in (r'class', r'struct', r'union', r'concept') and data.get(r'name')
        }

        # now do '<doxygen>' files
        for xml_file in xml_files:
            root = xml_utils.read(xml_file)
            if root.tag != r'doxygen':
                continue

            context.verbose(rf'Post-processing {xml_file}')
            changed = False

            compounddef = root.find(r'compounddef')
            if compounddef is None:
                context.warning(rf'{xml_file} did not contain a <compounddef>!')
                continue

            compound_id = compounddef.get(r'id')
            if compound_id is None or not compound_id:
                context.warning(rf'{xml_file} did not have attribute "id"!')
                continue

            compound_kind = compounddef.get(r'kind')
            if compound_kind is None or not compound_kind:
                context.warning(rf'{xml_file} did not have attribute "kind"!')
                continue

            compound_name = compounddef.find(r'compoundname')
            if compound_name is None or not compound_name.text:
                context.warning(rf'{xml_file} did not contain a valid <compoundname>!')
                continue
            compound_name = str(compound_name.text).strip()

            compound_filename = rf'{compound_id}.html'
            if compound_id == r'indexpage':
                compound_filename = r'index.html'

            compound_title = compounddef.find(r'title')
            compound_title = compound_title.text if compound_title is not None else compound_name

            # clean up <programlisting> blocks
            changed |= fixups.fix_programlisting(compounddef)

            # normalize section headings (m.css can't handle rich/empty <title>s); code spans are
            # preserved via sentinels and restored to <code> by the SectionTitleCodeSpans HTML fixer
            changed |= fixups.normalize_section_titles(compounddef)

            # add entry to compounds etc
            if compound_id not in compounds:
                compounds[compound_id] = {
                    r'refid': compound_id,
                    r'filename': compound_filename,
                    r'kind': compound_kind,
                    r'name': compound_name,
                    r'title': compound_title,
                }
                context.compound_pages[compound_filename] = compounds[compound_id]
            compound_page = context.compound_pages[compound_filename]
            if r'title' not in compound_page or not compound_page[r'title']:
                compound_page[r'title'] = compound_title

            if compound_kind != r'page':
                changed |= fixups.merge_userdefined_sections(compounddef)
                changed |= fixups.sort_userdefined_sections(compounddef)
                for section in compounddef.findall(r'sectiondef'):
                    changed |= fixups.remove_duplicate_members(section)
                    changed |= fixups.fix_leaked_keywords(section)
                    changed |= fixups.fix_trailing_return_types(section)
                    changed |= fixups.normalize_member_definitions(section)
                    changed |= fixups.resort_members(section, compound_kind)
                # re-link plain-text member types some doxygen versions stopped cross-referencing
                changed |= fixups.resolve_plain_type_references(compounddef, type_ids_by_name, compound_name)

            # namespaces
            if compound_kind == r'namespace':
                # set inline namespaces
                if context.inline_namespaces:
                    for nsid in inline_namespace_ids:
                        if compound_id == nsid:
                            compounddef.set(r'inline', r'yes')
                            changed = True
                            break

            # dirs
            if compound_kind == r'dir':
                # remove implementation headers
                if implementation_header_mappings:
                    for innerfile in compounddef.findall(r'innerfile'):
                        if innerfile.get(r'refid') in implementation_header_mappings:
                            compounddef.remove(innerfile)
                            changed = True

            # files
            if compound_kind == r'file':
                # simplify the XML by removing unnecessary junk
                for tag in (r'includes', r'includedby', r'incdepgraph', r'invincdepgraph'):
                    for t in compounddef.findall(tag):
                        compounddef.remove(t)
                        changed = True

                # rip the good bits out of implementation headers
                if implementation_header_mappings:
                    iid = compound_id
                    if iid in implementation_header_mappings:
                        hid = implementation_header_mappings[iid][2]
                        innernamespaces = compounddef.findall(r'innernamespace')
                        if innernamespaces:
                            implementation_header_innernamespaces[hid] = (
                                implementation_header_innernamespaces[hid] + innernamespaces
                            )
                            extracted_implementation = True
                            if iid in implementation_header_unused_values:
                                del implementation_header_unused_values[iid]
                            for tag in innernamespaces:
                                compounddef.remove(tag)
                                changed = True
                        sectiondefs = compounddef.findall(r'sectiondef')
                        if sectiondefs:
                            implementation_header_sectiondefs[hid] = (
                                implementation_header_sectiondefs[hid] + sectiondefs
                            )
                            extracted_implementation = True
                            if iid in implementation_header_unused_values:
                                del implementation_header_unused_values[iid]
                            for tag in sectiondefs:
                                compounddef.remove(tag)
                                changed = True

            # groups and namespaces
            if compound_kind in (r'group', r'namespace'):
                changed |= fixups.set_innerconcept_prot(compounddef)
                changed |= fixups.sort_inner_refs(compounddef)

            if compound_kind == r'concept':
                changed |= fixups.normalize_concept_definition(compounddef)

            # all namespace 'innerXXXXXX'
            if compound_kind in (r'namespace', r'struct', r'class', r'union', r'concept'):
                if compound_name.rfind(r'::') != -1:
                    all_inners_by_type[r'class' if compound_kind in (r'struct', r'union') else compound_kind].add(
                        (compound_id, compound_name)
                    )

            # collect concept + file <location>s so concepts can be back-filled into their file compounds
            if compound_kind in (r'concept', r'file'):
                location = compounddef.find(r'location')
                location = location.get(r'file') if location is not None else None
                if location:
                    if compound_kind == r'concept':
                        concepts_by_file_location.setdefault(location, []).append((compound_id, compound_name))
                    else:
                        file_id_by_location[location] = compound_id

            # capture an <includes> template keyed by source file (see includes_by_file_location)
            if compound_kind in (r'class', r'struct', r'union', r'concept'):
                includes = compounddef.find(r'includes')
                location = compounddef.find(r'location')
                location = location.get(r'file') if location is not None else None
                if includes is not None and location and location not in includes_by_file_location:
                    includes_by_file_location[location] = includes

            # pages
            if compound_kind == r'page':
                changed |= fixups.unwrap_synthetic_page_sections(compounddef)
                changed |= fixups.fix_nested_tableofcontents(compounddef)

            if changed:
                xml_utils.write(root, xml_file)

        context.verbose_value(r'Context.compounds', compounds)
        context.verbose_value(r'Context.compound_pages', context.compound_pages)
        context.verbose_value(r'Context.compound_kinds', context.compound_kinds)

        # fix up namespaces/classes that are missing <innerXXXX> nodes
        if 1:
            outer_namespaces = dict()
            for inner_type, ids_and_names in all_inners_by_type.items():
                for id, name in ids_and_names:
                    ns = name[: name.rfind(r'::')]
                    assert ns
                    if ns not in outer_namespaces:
                        outer_namespaces[ns] = []
                    outer_namespaces[ns].append((inner_type, id, name))
            for ns, vals in outer_namespaces.items():
                xml_file = None
                for outer_type in (r'namespace', r'struct', r'class', r'union'):
                    f = Path(context.temp_xml_dir, rf'{outer_type}{doxygen.mangle_name(ns)}.xml')
                    if path_exists(f):
                        xml_file = f
                        break
                if not xml_file:
                    continue
                root = xml_utils.read(xml_file)
                compounddef = root.find(r'compounddef')
                if compounddef is None:
                    continue
                changed = False
                existing_inner_ids = set()
                for inner_type in (r'class', r'namespace', r'concept'):
                    for elem in compounddef.findall(rf'inner{inner_type}'):
                        id = elem.get(r'refid')
                        if id:
                            existing_inner_ids.add(str(id))
                for inner_type, id, name in vals:
                    if id not in existing_inner_ids:
                        elem = xml_utils.make_child(compounddef, rf'inner{inner_type}')
                        elem.text = name
                        elem.set(r'refid', id)
                        elem.set(r'prot', r'public')  # todo: this isn't necessarily correct
                        existing_inner_ids.add(id)
                        changed = True
                if changed:
                    # back-filled refs were appended at the end; re-sort so the order is identical to
                    # versions where doxygen emitted them natively (convergence)
                    fixups.sort_inner_refs(compounddef)
                    xml_utils.write(root, xml_file)

        # back-fill <includes> onto concepts that lost it (doxygen 1.9.7/1.9.8 dropped it for concepts
        # nested in a sub-namespace), mirroring a sibling compound from the same file
        for location, concept_list in concepts_by_file_location.items():
            template = includes_by_file_location.get(location)
            if template is None:
                continue
            for cid, _ in concept_list:
                f = Path(context.temp_xml_dir, rf'{cid}.xml')
                if not path_exists(f):
                    continue
                root = xml_utils.read(f)
                compounddef = root.find(r'compounddef')
                if compounddef is None:
                    continue
                if fixups.add_concept_includes(compounddef, template):
                    xml_utils.write(root, f)

        # back-fill <innerconcept> into file compounds: newer doxygen lists a file's concepts in its
        # compound (m.css then renders a "Concepts" section on the file page), older doxygen does not.
        # synthesise the missing entries from each concept's <location> so the concept-rich form is
        # produced regardless of doxygen version.
        if 1:
            for location, concepts in concepts_by_file_location.items():
                file_id = file_id_by_location.get(location)
                if not file_id:
                    continue
                xml_file = Path(context.temp_xml_dir, rf'{file_id}.xml')
                if not path_exists(xml_file):
                    continue
                root = xml_utils.read(xml_file)
                compounddef = root.find(r'compounddef')
                if compounddef is None:
                    continue
                existing_ids = {str(e.get(r'refid')) for e in compounddef.findall(r'innerconcept')}
                changed = False
                for cid, cname in concepts:
                    if cid not in existing_ids:
                        elem = xml_utils.make_child(compounddef, r'innerconcept')
                        elem.text = cname
                        elem.set(r'refid', cid)
                        elem.set(r'prot', r'public')
                        existing_ids.add(cid)
                        changed = True
                # normalise prot + ordering whether the concepts were just synthesised or doxygen emitted
                # them natively, so every version lands on the same sorted, public form
                changed |= fixups.set_innerconcept_prot(compounddef)
                changed |= fixups.sort_inner_refs(compounddef)
                if changed:
                    xml_utils.write(root, xml_file)

        # merge extracted implementations
        if extracted_implementation:
            assert implementation_header_data is not None  # only set when impl data was populated
            for hp, hfn, hid, impl in implementation_header_data:
                xml_file = Path(context.temp_xml_dir, rf'{hid}.xml')
                context.verbose(rf'Merging implementation nodes into {xml_file}')
                root = xml_utils.read(xml_file)
                compounddef = require(root.find(r'compounddef'))
                changed = False

                innernamespaces = compounddef.findall(r'innernamespace')
                for new_tag in implementation_header_innernamespaces[hid]:
                    matched = False
                    for existing_tag in innernamespaces:
                        if existing_tag.get(r'refid') == new_tag.get(r'refid'):
                            matched = True
                            break
                    if not matched:
                        compounddef.append(new_tag)
                        innernamespaces.append(new_tag)
                        changed = True

                sectiondefs = compounddef.findall(r'sectiondef')
                for new_section in implementation_header_sectiondefs[hid]:
                    matched_section = False
                    for existing_section in sectiondefs:
                        if existing_section.get(r'kind') == new_section.get(r'kind'):
                            matched_section = True

                            memberdefs = existing_section.findall(r'memberdef')
                            new_memberdefs = new_section.findall(r'memberdef')
                            for new_memberdef in new_memberdefs:
                                matched = False
                                for existing_memberdef in memberdefs:
                                    if existing_memberdef.get(r'id') == new_memberdef.get(r'id'):
                                        matched = True
                                        break

                                if not matched:
                                    new_section.remove(new_memberdef)
                                    existing_section.append(new_memberdef)
                                    memberdefs.append(new_memberdef)
                                    changed = True
                            break

                    if not matched_section:
                        compounddef.append(new_section)
                        sectiondefs.append(new_section)
                        changed = True

                if changed:
                    implementation_header_unused_keys.remove(hp)
                    xml_utils.write(root, xml_file)

        # sanity-check implementation header state
        if implementation_header_unused_keys:
            for key in implementation_header_unused_keys:
                context.warning(rf"implementation_header: nothing extracted for '{key}'")
        if implementation_header_unused_values:
            for iid, idata in implementation_header_unused_values.items():
                context.warning(rf"implementation_header: nothing extracted from '{idata[0]}' for '{idata[1]}'")

    # delete the impl header xml files
    if implementation_header_data:
        for hdata in implementation_header_data:
            for ip, ifn, iid in hdata[3]:
                delete_file(Path(context.temp_xml_dir, rf'{iid}.xml'), logger=context.verbose_logger)

    # scan through the files and substitute impl header ids and paths as appropriate
    if implementation_header_data:
        xml_files = get_all_files(context.temp_xml_dir, any=('*.xml'))
        for xml_file in xml_files:
            context.verbose(rf"Re-linking implementation headers in '{xml_file}'")
            xml_text = read_all_text_from_file(xml_file, logger=context.verbose_logger)
            for hp, hfn, hid, impl in implementation_header_data:
                for ip, ifn, iid in impl:
                    xml_text = relink_implementation_header_refs(xml_text, iid, hid, ip, hp)
            xml_utils.write(xml_text, xml_file)

    # normalise the generated tagfile (always) and fold implementation headers into it (when present),
    # so downstream consumers get version-independent output that reads as if everything lived in the
    # public header
    if context.generate_tagfile and context.tagfile_path and context.tagfile_path.exists():
        tagfile_root = xml_utils.read(context.tagfile_path)
        changed = normalize_tagfile(tagfile_root)
        if implementation_header_data:
            context.verbose(rf"Folding implementation headers in '{context.tagfile_path}'")
            changed |= fold_implementation_headers_in_tagfile(tagfile_root, implementation_header_data)
        if changed:
            xml_utils.write(tagfile_root, context.tagfile_path)


def preprocess_xml_v2(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    log_func = lambda m: context.verbose(m)

    g = doxygen.read_graph_from_xml(context.temp_xml_dir, log_func=log_func)

    # delete 'file' nodes for markdown and dox files
    g.remove(filter=lambda n: n.type is graph.File and re.search(r'[.](?:md|dox)$', n.local_name, flags=re.I))

    # delete empty 'dir' nodes
    g.remove(filter=lambda n: n.type is graph.Directory and not len(list(n(graph.File, graph.Directory))))

    # todo:
    # - extract namespaces, types and enum values for syntax highlighting
    # - enumerate all compound pages and their types for later (e.g. HTML post-process)
    # - merge user-defined sections with the same name
    # - sort user-defined sections based on their name
    # - implementation headers

    for f in enumerate_files(context.temp_xml_dir, any=r'*.xml'):
        delete_file(f, logger=log_func)
    doxygen.write_graph_to_xml(g, context.temp_xml_dir, log_func=log_func)


def parse_xml(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    xml_files = get_all_files(context.temp_xml_dir, any=(r'*.xml'))
    xml_files += [coerce_path(f) for _, (f, _) in context.tagfiles.items()]
    if context.generate_tagfile and context.tagfile_path:
        xml_files.append(context.tagfile_path)
    if not xml_files:
        return

    class Trie:
        def __init__(self):
            self.__trie = TrieRegEx()
            self.__count = 0

        def add(self, s: typing.Optional[str]):
            if not s:
                return
            self.__trie.add(s)
            self.__count += 1

        def __bool__(self) -> bool:
            return self.__count > 0

        def __str__(self) -> str:
            return self.__trie.regex()

    class Tries:
        def __init__(self):
            self.namespaces = Trie()
            self.types = Trie()
            self.enum_values = Trie()
            self.macros = Trie()
            self.functions = Trie()

    tries = Tries()

    def name_ok(s: typing.Optional[str]) -> bool:
        return bool(s is not None and s and not re.search(r'[^a-zA-Z0-9_:]', s))

    def extract_all_members_from_compound_node(compound):
        nonlocal tries
        compound_name = compound.find(r'name')
        if compound_name is None or not name_ok(compound_name.text):
            return
        compound_kind = compound.get(r'kind')
        if compound_kind is None or compound_kind not in (
            r'namespace',
            r'class',
            r'struct',
            r'union',
            r'concept',
            r'group',
            r'file',
        ):
            return
        # for files and groups we can only extract #defines because they need the full::namespace::context
        # otherwise we get all the C++ types
        member_kinds = (
            r'namespace',
            r'class',
            r'struct',
            r'union',
            r'concept',
            r'typedef',
            r'enum',
            r'enumvalue',
            r'function',
        )
        if compound_kind in (r'group', r'file'):
            member_kinds = (r'define',)
        members = [(m, m.find(r'name')) for m in compound.findall(r'member') if m.get(r'kind') in member_kinds]
        members = [(m, n) for m, n in members if n is not None and name_ok(n.text)]
        # first we do everything _except_ enumvalues because they require special handling
        enums = dict()
        for member, member_name in members:
            member_kind = member.get(r'kind')
            if member_kind == r'define':
                tries.macros.add(compound_name.text)
            else:
                member_qualified_name = rf'{compound_name.text}::{member_name.text}'
                if member_kind == r'namespace':
                    tries.namespaces.add(member_qualified_name)
                elif member_kind == r'function':
                    if member_name.text.startswith(r'operator'):
                        continue
                    tries.functions.add(member_qualified_name)
                elif member_kind != r'enumvalue':
                    tries.types.add(member_qualified_name)
                    if member_kind == r'enum':
                        refid = member.get(r'refid')
                        if refid:
                            enums[refid] = member_qualified_name
        # then we do enumvaleus
        for member, member_name in members:
            if member.get(r'kind') != r'enumvalue':
                continue
            refid = member.get(r'refid')
            if not refid:
                continue
            for enum_refid, enum_qualified_name in enums.items():
                if refid.startswith(enum_refid):
                    tries.enum_values.add(rf'{enum_qualified_name}::{member_name.text}')

    for xml_file in xml_files:
        if xml_file.name == r'Doxyfile.xml' or not xml_file.exists() or not xml_file.is_file():
            continue

        root = xml_utils.read(xml_file)
        if root.tag not in (r'doxygenindex', r'tagfile'):
            continue

        context.verbose(rf'Extracting type information from {xml_file}')

        # tag files
        if root.tag == r'tagfile':

            def extract_types_from_tagfile_node(node):
                nonlocal tries
                namespaces = [(ns, ns.find(r'name')) for ns in node.findall(r'namespace')]
                namespaces = [(ns, n) for ns, n in namespaces if n is not None and name_ok(n.text)]
                for namespace, n in namespaces:
                    tries.namespaces.add(n.text)

                classes = [
                    (c, c.find(r'name'))
                    for c in node.findall(r'class')
                    if c.get(r'kind') in (r'class', r'struct', r'union')
                ]
                classes = [(c, n) for c, n in classes if n is not None and name_ok(n.text)]
                for class_, n in classes:
                    tries.types.add(n.text)

                compounds = [
                    (c, c.find(r'name'))
                    for c in node.findall(r'compound')
                    if c.get(r'kind') in (r'namespace', r'class', r'struct', r'union', r'concept')
                ]
                compounds = [(c, n) for c, n in compounds if n is not None and name_ok(n.text)]
                for compound, n in compounds:
                    if compound.get(r'kind') == r'namespace':
                        tries.namespaces.add(n.text)
                    else:
                        tries.types.add(n.text)
                    extract_types_from_tagfile_node(compound)
                    extract_all_members_from_compound_node(compound)

            extract_types_from_tagfile_node(root)

        # the doxygen index
        elif root.tag == r'doxygenindex':
            compounds = [
                (c, c.find(r'name'))
                for c in root.findall(r'compound')
                if c.get(r'kind') in (r'namespace', r'class', r'struct', r'union', r'concept')
            ]
            compounds = [(c, n) for c, n in compounds if n is not None and name_ok(n.text)]
            for compound, n in compounds:
                if compound.get(r'kind') == r'namespace':
                    tries.namespaces.add(n.text)
                else:
                    tries.types.add(n.text)
                extract_all_members_from_compound_node(compound)

    # add to syntax highlighter
    if tries.namespaces:
        context.code_blocks.namespaces.add(str(tries.namespaces))
    if tries.types:
        context.code_blocks.types.add(str(tries.types))
    if tries.enum_values:
        context.code_blocks.enums.add(str(tries.enum_values))
    if tries.macros:
        context.code_blocks.macros.add(str(tries.macros))
    if tries.functions:
        context.code_blocks.functions.add(str(tries.functions))
    context.verbose_object(r'Context.code_blocks', context.code_blocks)


def clean_xml(context: Context, dir=None):
    assert context is not None
    assert isinstance(context, Context)
    if dir is None:
        dir = context.temp_xml_dir

    xml_files = get_all_files(dir, any=(r'*.xml'))
    for xml_file in xml_files:
        root = xml_utils.read(
            xml_file,
            parser=xml_utils.create_parser(remove_blank_text=True),
            logger=context.verbose_logger,  #
        )

        # some description nodes end up with just whitespace; I guess lxml gets a bit confused here
        for elem in root.iter(r'briefdescription', r'detaileddescription', r'inbodydescription'):
            if len(elem) or not elem.text:
                continue
            if elem.text.strip() == r'':
                elem.text = r''

        # indent() will fuck up the formatting of some 'document-style' elements so we need to find and
        # extract those elements before prettifying the overall document
        sacred_elements = []
        sacred_element_ids = set()
        for elem in root.iter(r'programlisting', r'initializer', r'formula', r'computeroutput'):
            already_processed = False
            for parent in elem.iterancestors():
                if id(parent) in sacred_element_ids:
                    already_processed = True
                    break
            if already_processed:
                continue
            parent = require(elem.getparent())
            sacred_elements.append((elem, parent, parent.index(elem)))
            sacred_element_ids.add(id(elem))
        for elem, parent, _ in reversed(sacred_elements):
            parent.remove(elem)

        etree.indent(root, space='\t')

        # re-insert the extracted elements in their original positions
        for elem, parent, index in sacred_elements:
            parent.insert(index, elem)

        xml_utils.write(root, xml_file, logger=context.verbose_logger)  #


def compile_regexes(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    # the code_blocks sets are collected as set[str] then replaced in-place with compiled patterns;
    # likewise autolinks goes from (str, str) pairs to (Pattern, str). the slots change type, so write
    # through an untyped view (CodeBlocks/Context declare the collected, pre-compile, types)
    cb = context.code_blocks
    cb_out = typing.cast(typing.Any, cb)
    cb_out.namespaces = regex_or(cb.namespaces, pattern_prefix=r'(?:::)?', pattern_suffix=r'(?:::)?')
    cb_out.types = regex_or(cb.types, pattern_prefix=r'(?:::)?', pattern_suffix=r'(?:::)?')
    cb_out.enums = regex_or(cb.enums, pattern_prefix=r'(?:::)?')
    cb_out.functions = regex_or(cb.functions, pattern_prefix=r'(?:::)?')
    cb_out.macros = regex_or(cb.macros)
    typing.cast(typing.Any, context).autolinks = tuple(
        [(re.compile(r'(?<![a-zA-Z_])' + expr + r'(?![a-zA-Z_])'), uri) for expr, uri in context.autolinks]
    )
