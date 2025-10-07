#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
The 'actually do the thing' module.
"""

import concurrent.futures as futures
import os
import subprocess
import tempfile
import copy
import sys
import platform

from io import StringIO
from lxml import etree
from trieregex import TrieRegEx

from . import doxygen, fixers, graph, soup, xml_utils
from .project import Context
from .svg import SVG
from .utils import *
from .version import *

if sys.version_info >= (3, 8):
    import shutil

    def copy_tree(src, dest):
        shutil.copytree(str(src), str(dest), dirs_exist_ok=True)

else:
    import distutils.dir_util

    def copy_tree(src, dest):
        distutils.dir_util.copy_tree(str(src), str(dest))


# =======================================================================================================================
# HELPERS
# =======================================================================================================================


def make_temp_file():
    return tempfile.SpooledTemporaryFile(mode='w+', newline='\n', encoding='utf-8')


# =======================================================================================================================
# PRE/POST PROCESSORS
# =======================================================================================================================

DOXYGEN_DEFAULTS = (
    (r'ALLEXTERNALS', False),
    (r'ALLOW_UNICODE_NAMES', False),
    (r'ALWAYS_DETAILED_SEC', False),
    (r'AUTOLINK_SUPPORT', True),
    (r'BUILTIN_STL_SUPPORT', False),
    (r'CASE_SENSE_NAMES', False),
    (r'CLASS_DIAGRAMS', False),
    (r'CPP_CLI_SUPPORT', False),
    (r'CREATE_SUBDIRS', False),
    (r'DISTRIBUTE_GROUP_DOC', False),
    (r'DOXYFILE_ENCODING', r'UTF-8'),
    (r'DOT_FONTNAME', r'Source Sans Pro'),
    (r'DOT_FONTSIZE', 16),
    (r'ENABLE_PREPROCESSING', True),
    (r'EXAMPLE_RECURSIVE', False),
    (r'EXCLUDE_SYMLINKS', False),
    (r'EXPAND_ONLY_PREDEF', False),
    (r'EXTERNAL_GROUPS', False),
    (r'EXTERNAL_PAGES', False),
    (r'EXTRACT_ANON_NSPACES', False),
    (r'EXTRACT_LOCAL_CLASSES', False),
    (r'EXTRACT_LOCAL_METHODS', False),
    (r'EXTRACT_PACKAGE', False),
    (r'EXTRACT_PRIV_VIRTUAL', True),
    (r'EXTRACT_PRIVATE', False),
    (r'EXTRACT_STATIC', False),
    (r'FILTER_PATTERNS', None),
    (r'FILTER_SOURCE_FILES', False),
    (r'FILTER_SOURCE_PATTERNS', None),
    (r'FORCE_LOCAL_INCLUDES', False),
    (r'FULL_PATH_NAMES', True),
    (r'GENERATE_AUTOGEN_DEF', False),
    (r'GENERATE_BUGLIST', False),
    (r'GENERATE_CHI', False),
    (r'GENERATE_DEPRECATEDLIST', False),
    (r'GENERATE_DOCBOOK', False),
    (r'GENERATE_DOCSET', False),
    (r'GENERATE_ECLIPSEHELP', False),
    (r'GENERATE_HTML', False),
    (r'GENERATE_HTMLHELP', False),
    (r'GENERATE_LATEX', False),
    (r'GENERATE_LEGEND', False),
    (r'GENERATE_MAN', False),
    (r'GENERATE_PERLMOD', False),
    (r'GENERATE_QHP', False),
    (r'GENERATE_RTF', False),
    (r'GENERATE_SQLITE3', False),
    (r'GENERATE_TESTLIST', False),
    (r'GENERATE_TODOLIST', False),
    (r'GENERATE_TREEVIEW', False),
    (r'GENERATE_XML', True),
    (r'HIDE_COMPOUND_REFERENCE', False),
    (r'HIDE_FRIEND_COMPOUNDS', False),
    (r'HIDE_IN_BODY_DOCS', False),
    (r'HIDE_SCOPE_NAMES', False),
    (r'HIDE_UNDOC_CLASSES', True),
    (r'HIDE_UNDOC_MEMBERS', True),
    (r'HTML_EXTRA_STYLESHEET', None),
    (r'HTML_FILE_EXTENSION', r'.html'),
    (r'HTML_OUTPUT', r'html'),
    (r'IDL_PROPERTY_SUPPORT', False),
    (r'INHERIT_DOCS', True),
    (r'INLINE_GROUPED_CLASSES', False),
    (r'INLINE_INFO', True),
    (r'INLINE_INHERITED_MEMB', True),
    (r'INLINE_SIMPLE_STRUCTS', False),
    (r'INLINE_SOURCES', False),
    (r'INPUT_ENCODING', r'UTF-8'),
    (r'INPUT_FILTER', None),
    (r'LOOKUP_CACHE_SIZE', 2),
    (r'MACRO_EXPANSION', True),
    (r'MARKDOWN_SUPPORT', True),
    (r'OPTIMIZE_FOR_FORTRAN', False),
    (r'OPTIMIZE_OUTPUT_FOR_C', False),
    (r'OPTIMIZE_OUTPUT_JAVA', False),
    (r'OPTIMIZE_OUTPUT_SLICE', False),
    (r'OPTIMIZE_OUTPUT_VHDL', False),
    (r'PYTHON_DOCSTRING', True),
    (r'QUIET', False),
    (r'RECURSIVE', False),
    (r'REFERENCES_LINK_SOURCE', False),
    (r'RESOLVE_UNNAMED_PARAMS', True),
    (r'SEARCH_INCLUDES', False),
    (r'SEPARATE_MEMBER_PAGES', False),
    (r'SHORT_NAMES', False),
    (r'SHOW_GROUPED_MEMB_INC', False),
    (r'SHOW_USED_FILES', False),
    (r'SIP_SUPPORT', False),
    (r'SKIP_FUNCTION_MACROS', False),
    (r'SORT_BRIEF_DOCS', False),
    (r'SORT_BY_SCOPE_NAME', False),
    (r'SORT_GROUP_NAMES', True),
    (r'SORT_MEMBER_DOCS', False),
    (r'SORT_MEMBERS_CTORS_1ST', True),
    (r'SOURCE_BROWSER', False),
    (r'STRICT_PROTO_MATCHING', False),
    (r'STRIP_FROM_INC_PATH', None),  # we handle this
    (r'SUBGROUPING', True),
    (r'TAB_SIZE', 4),
    (r'TOC_INCLUDE_HEADINGS', 3),
    (r'TYPEDEF_HIDES_STRUCT', False),
    (r'UML_LOOK', False),
    (r'USE_HTAGS', False),
    (r'USE_MDFILE_AS_MAINPAGE', None),
    (r'VERBATIM_HEADERS', False),
    (r'WARN_AS_ERROR', False),  # we handle this
    (r'WARN_IF_DOC_ERROR', True),
    (r'WARN_IF_INCOMPLETE_DOC', True),
    (r'WARN_LOGFILE', None),
    (r'XML_NS_MEMB_FILE_SCOPE', True),
    (r'XML_PROGRAMLISTING', False),
)


def preprocess_doxyfile(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    with doxygen.Doxyfile(
        input_path=None, output_path=context.doxyfile_path, cwd=context.input_dir, logger=context.verbose_logger
    ) as df:
        df.append()
        df.append(r'#---------------------------------------------------------------------------')
        df.append(r'# marzer/poxy')
        df.append(r'#---------------------------------------------------------------------------', end='\n\n')

        df.append(r'# doxygen defaults', end='\n\n')  # ----------------------------------------

        for k, v in DOXYGEN_DEFAULTS:
            df.set_value(k, v)

        df.append()
        df.append(r'# general config', end='\n\n')  # ---------------------------------------------------

        df.set_value(r'OUTPUT_DIRECTORY', context.output_dir)
        df.set_value(r'XML_OUTPUT', context.temp_xml_dir)
        df.set_value(r'PROJECT_NAME', context.name)
        df.set_value(r'PROJECT_BRIEF', context.description)
        df.set_value(r'PROJECT_LOGO', context.logo)
        df.set_value(r'SHOW_INCLUDE_FILES', context.show_includes)
        df.set_value(r'INTERNAL_DOCS', context.internal_docs)

        df.set_value(
            r'ENABLED_SECTIONS', (r'private', r'internal') if context.internal_docs else (r'public', r'external')
        )
        df.add_value(r'ENABLED_SECTIONS', r'poxy_supports_concepts')

        if context.xml_v2:
            df.set_value(r'INLINE_INHERITED_MEMB', False)

        if context.generate_tagfile:
            df.set_value(r'GENERATE_TAGFILE', context.tagfile_path)
        else:
            df.set_value(r'GENERATE_TAGFILE', None)

        df.set_value(r'NUM_PROC_THREADS', min(context.threads, 32))

        df.set_value(r'CLANG_OPTIONS', rf'-std=c++{context.cpp%100}')
        df.add_value(r'CLANG_OPTIONS', r'-Wno-everything')

        if context.main_page:
            df.set_value(r'USE_MDFILE_AS_MAINPAGE', context.main_page)

        if context.excluded_symbols:
            df.set_value(r'EXCLUDE_SYMBOLS', context.excluded_symbols)

        df.set_value(r'HAVE_DOT', bool(context.dot))

        df.append()
        df.append(r'# context.warnings', end='\n\n')  # ---------------------------------------------------

        df.set_value(r'WARNINGS', context.warnings.enabled)
        df.set_value(r'WARN_IF_UNDOCUMENTED', context.warnings.undocumented)

        df.append()
        df.append(r'# context.sources', end='\n\n')  # ----------------------------------------------------

        df.set_value(r'INPUT', context.sources.paths)
        df.set_value(r'FILE_PATTERNS', context.sources.patterns)
        df.set_value(r'STRIP_FROM_PATH', context.sources.strip_paths)
        df.set_value(r'EXTRACT_ALL', context.sources.extract_all)

        df.set_value(r'EXCLUDE', context.html_dir)
        if context.source_excludes:
            df.add_value(r'EXCLUDE', context.source_excludes)

        df.append()
        df.append(r'# context.examples', end='\n\n')  # ----------------------------------------------------

        df.set_value(r'EXAMPLE_PATH', context.examples.paths)
        df.set_value(r'EXAMPLE_PATTERNS', context.examples.patterns)

        if context.images.paths:  # ----------------------------------------------------
            df.append()
            df.append(r'# context.images', end='\n\n')
            df.set_value(r'IMAGE_PATH', context.images.paths)

        if context.tagfiles:  # ----------------------------------------------------
            df.append()
            df.append(r'# context.tagfiles', end='\n\n')
            df.set_value(r'TAGFILES', [rf'{file}={dest}' for _, (file, dest) in context.tagfiles.items()])

        if context.aliases:  # ----------------------------------------------------
            df.append()
            df.append(r'# context.aliases', end='\n\n')
            df.set_value(r'ALIASES', [rf'{k}={v}' for k, v in context.aliases.items()])

        if context.macros:  # ----------------------------------------------------
            df.append()
            df.append(r'# context.macros', end='\n\n')
            df.set_value(r'PREDEFINED', [rf'{k}={v}' for k, v in context.macros.items()])

        df.cleanup()
        context.verbose(r'Doxyfile:')
        context.verbose(df.get_text(), indent=r'    ')


def preprocess_temp_markdown_files(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    for attr_name in 'main_page', 'changelog':
        if not hasattr(context, attr_name):
            continue

        path = getattr(context, attr_name)
        if not path:
            continue

        # make sure we're working with a temp copy, not the user's actual files
        # (the actual copying should already be done in the context's initialization)
        assert path.parent == context.temp_pages_dir
        assert_existing_file(path)

        text = read_all_text_from_file(path, logger=context.verbose_logger).strip()
        text = text.replace('\r\n', '\n')
        text = re.sub(r'\n<br[ \t]*/?><br[ \t]*/?>\n', r'', text)
        text = text.replace(r'&amp;', r'__poxy_this_was_amp')
        text = re.sub(r'&#x([a-fA-F0-9]{2,4});', r'__poxy_this_was_hex\1', text)

        if attr_name == 'changelog':

            if context.repo:
                text = re.sub(r'#([0-9]+)', lambda m: rf'[#{m[1]}]({context.repo.make_issue_uri(m[1])})', text)
                text = re.sub(r'!([0-9]+)', lambda m: rf'[!{m[1]}]({context.repo.make_pull_request_uri(m[1])})', text)
                text = re.sub(r'@([a-zA-Z0-9_-]+)', lambda m: rf'[@{m[1]}]({context.repo.make_user_uri(m[1])})', text)

            text = text.replace(r'@', r'__poxy_this_was_at')
            text = f'\n{text}\n'
            text = re.sub('\n#[^#].+?\n', '\n', text)
            text = f'@page poxy_changelog Changelog\n\n@tableofcontents\n\n{text}'
            text = text.rstrip()
            text += '\n\n'

        context.verbose(rf'Writing {path}')
        with open(path, r'w', encoding=r'utf-8', newline='\n') as f:
            f.write(text)


def preprocess_tagfiles(context: Context):
    assert context is not None
    assert isinstance(context, Context)
    if not context.unresolved_tagfiles:
        return
    with ScopeTimer(r'Resolving remote tagfiles', print_start=True, print_end=context.verbose_logger) as t:
        for source, (file, _) in context.tagfiles.items():
            if file.exists() or not is_uri(source):
                continue
            context.verbose(rf'Downloading {source}')
            text = download_text(source, timeout=30)
            context.verbose(rf'Writing {file}')
            with open(file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)


def preprocess_xml(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    xml_files = [f for f in get_all_files(context.temp_xml_dir, any=(r'*.xml')) if f.name.lower() != r'doxyfile.xml']
    if not xml_files:
        return

    context.verbose(rf'Post-processing {len(xml_files) + len(context.tagfiles)} XML files...')

    # pre-pass to resolve wildcards in implementation headers
    implementation_headers_with_wildcards = []
    for i in range(len(context.implementation_headers)):
        for impl in context.implementation_headers[i][1]:
            impl: str
            if impl.find('*') == -1:
                continue
            impl = re.sub(r'[*][*]+', r'*', impl)
            impl = impl.replace(r'*', r'_____poxy_wildcard_____')
            impl = re.escape(impl)
            impl = impl.replace(r'_____poxy_wildcard_____', r'''[^<>:"'|?*\^]*''')
            implementation_headers_with_wildcards.append((i, impl))
    if implementation_headers_with_wildcards:
        for xml_file in xml_files:
            root = xml_utils.read(xml_file)
            if root.tag != r'doxygen':
                continue
            compounddef = root.find(r'compounddef')
            if compounddef is None:
                continue
            if compounddef.get(r'kind') != r'file':
                continue
            location = compounddef.find(r'location')
            if location is None:
                continue
            location = location.get(r'file')
            if not location:
                continue
            for header_index, impl in implementation_headers_with_wildcards:
                if re.fullmatch(impl, location):
                    context.implementation_headers[header_index][1].append(location)

    # remove any wildcards, duplicates and sanity-check the implementation headers
    seen_implementation_headers = set()
    for header, _ in context.implementation_headers:
        if header in seen_implementation_headers:
            raise Error(rf"implementation_headers: '{header}' seen more than once")
        seen_implementation_headers.add(header)
    for i in range(len(context.implementation_headers)):
        impls = sorted(remove_duplicates(context.implementation_headers[i][1]))
        impls = [impl for impl in impls if impl.find('*') == -1]
        for impl in impls:
            if impl in seen_implementation_headers:
                raise Error(rf"implementation_headers: '{impl}' seen more than once")
            seen_implementation_headers.add(impl)
        context.implementation_headers[i][1] = impls
    context.implementation_headers = [h for h in context.implementation_headers if (h[0] and h[1])]
    context.verbose_value(r'Context.implementation_headers', context.implementation_headers)

    implementation_header_data = None
    implementation_header_mappings = None
    implementation_header_innernamespaces = None
    implementation_header_sectiondefs = None
    implementation_header_unused_keys = None
    implementation_header_unused_values = None
    if context.implementation_headers:
        implementation_header_data = [
            (
                hp,
                os.path.basename(hp),
                doxygen.mangle_name(os.path.basename(hp)),
                [(i, os.path.basename(i), doxygen.mangle_name(os.path.basename(i))) for i in impl],
            )
            for hp, impl in context.implementation_headers
        ]
        implementation_header_unused_keys = set()
        for hp, impl in context.implementation_headers:
            implementation_header_unused_keys.add(hp)
        implementation_header_unused_values = dict()
        for hdata in implementation_header_data:
            for ip, ifn, iid in hdata[3]:
                implementation_header_unused_values[iid] = (ip, hdata[0])
        implementation_header_mappings = dict()
        implementation_header_innernamespaces = dict()
        implementation_header_sectiondefs = dict()
        for hdata in implementation_header_data:
            implementation_header_innernamespaces[hdata[2]] = []
            implementation_header_sectiondefs[hdata[2]] = []
            for ip, ifn, iid in hdata[3]:
                implementation_header_mappings[iid] = hdata

    context.compounds = dict()
    context.compound_pages = dict()
    context.compound_kinds = set()

    inline_namespace_ids = None
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
                            if ref_file.exists():
                                existing_inners = existing_inners + 1
                    if not existing_inners:
                        delete_file(xml_file, logger=context.verbose_logger)
                        deleted = True

        extracted_implementation = False
        xml_files = [
            f for f in get_all_files(context.temp_xml_dir, any=(r'*.xml')) if f.name.lower() != r'doxyfile.xml'
        ]
        all_inners_by_type = {r'namespace': set(), r'class': set(), r'concept': set()}

        # do '<doxygenindex>' first
        for xml_file in xml_files:
            root = xml_utils.read(xml_file)
            if root.tag != r'doxygenindex':
                continue

            context.verbose(rf'Post-processing {xml_file}')
            changed = False

            # remove entries for files we might have explicitly deleted above
            for compound in [
                tag for tag in root.findall(r'compound') if tag.get(r'kind') in (r'file', r'dir', r'concept')
            ]:
                ref_file = Path(context.temp_xml_dir, rf'{compound.get(r"refid")}.xml')
                if not ref_file.exists():
                    root.remove(compound)
                    changed = True

            # enumerate all compound pages and their types for later (e.g. HTML post-process)
            for tag in root.findall(r'compound'):
                refid = tag.get(r'refid').strip()
                assert refid
                filename = refid
                if refid == r'indexpage':
                    filename = r'index'
                filename = filename + r'.html'
                context.compounds[refid] = {
                    r'refid': refid,
                    r'filename': filename,
                    r'kind': tag.get(r'kind'),
                    r'name': tag.find(r'name').text,
                    r'title': tag.find(r'title').text.strip() if tag.find(r'title') is not None else r'',
                }
                context.compound_pages[filename] = context.compounds[refid]
                context.compound_kinds.add(tag.get(r'kind'))

            if changed:
                xml_utils.write(root, xml_file)

        # doxygen >= 1.9.7 needs some special handling to play nice with m.css
        # see: https://github.com/mosra/m.css/issues/239
        if doxygen.version() >= (1, 9, 7):

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
                if compound_kind is None or not compound_kind or not compound_kind in (r'file', r'namespace'):
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
                    if compound_kind is None or not compound_kind or not compound_kind in (r'file', r'namespace'):
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

            # do a bit of cleanup of <programlisting>
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
                if (
                    not programlisting.get(r'filename')
                    and len(programlisting) >= 2
                    and programlisting[0].tag == 'codeline'
                ):
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

            # add entry to compounds etc
            if compound_id not in context.compounds:
                context.compounds[compound_id] = {
                    r'refid': compound_id,
                    r'filename': compound_filename,
                    r'kind': compound_kind,
                    r'name': compound_name,
                    r'title': compound_title,
                }
                context.compound_pages[compound_filename] = context.compounds[compound_id]
            compound_page = context.compound_pages[compound_filename]
            if r'title' not in compound_page or not compound_page[r'title']:
                compound_page[r'title'] = compound_title

            if compound_kind != r'page':

                # merge user-defined sections with the same header name
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

                # sort user-defined sections based on their name
                sectiondefs = [s for s in compounddef.findall(r'sectiondef') if s.get(r'kind') == r'user-defined']
                sectiondefs = [s for s in sectiondefs if s.find(r'header') is not None]
                for section in sectiondefs:
                    compounddef.remove(section)
                sectiondefs.sort(key=lambda s: s.find(r'header').text)
                for section in sectiondefs:
                    compounddef.append(section)
                    changed = True

                # per-section stuff
                for section in compounddef.findall(r'sectiondef'):
                    # remove members which are listed multiple times because doxygen is idiotic:
                    members = [tag for tag in section.findall(r'memberdef')]
                    for i in range(len(members) - 1, 0, -1):
                        for j in range(i):
                            if members[i].get(r'id') == members[j].get(r'id'):
                                section.remove(members[i])
                                changed = True
                                break

                    # fix keywords like 'friend' erroneously included in the type
                    if 1:
                        members = [
                            m
                            for m in section.findall(r'memberdef')
                            if m.get(r'kind') in (r'friend', r'function', r'variable')
                        ]

                        # leaked keywords
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

                    # fix issues with trailing return types
                    if 1:
                        members = [
                            m for m in section.findall(r'memberdef') if m.get(r'kind') in (r'friend', r'function')
                        ]

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
                                changed = True
                                continue

                            # fix "auto foo() -> auto" redundancy (https://github.com/marzer/poxy/issues/26)
                            if args_elem.text == r'()':
                                type_elem.text = r'__poxy_deduced_auto_return_type'
                                changed = True
                                continue

                    # re-sort members to override Doxygen's weird and stupid sorting 'rules'
                    if 1:
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
                if context.implementation_headers:
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
                if context.implementation_headers:
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
                # fix inner(class|namespace|group|concept) sorting
                inners = [tag for tag in compounddef.iterchildren() if tag.tag.startswith(r'inner')]
                if inners:
                    changed = True
                    for tag in inners:
                        compounddef.remove(tag)
                    inners.sort(key=lambda tag: tag.text)
                    for tag in inners:
                        compounddef.append(tag)

            # all namespace 'innerXXXXXX'
            if compound_kind in (r'namespace', r'struct', r'class', r'union', r'concept'):
                if compound_name.rfind(r'::') != -1:
                    all_inners_by_type[r'class' if compound_kind in (r'struct', r'union') else compound_kind].add(
                        (compound_id, compound_name)
                    )

            # pages
            if compound_kind == r'page':

                # fix <tableofcontents><tableofcontents></tableofcontents></tableofcontents>
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

            if changed:
                xml_utils.write(root, xml_file)

        context.verbose_value(r'Context.compounds', context.compounds)
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
                    if f.exists():
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
                    xml_utils.write(root, xml_file)

        # merge extracted implementations
        if extracted_implementation:
            for hp, hfn, hid, impl in implementation_header_data:
                xml_file = Path(context.temp_xml_dir, rf'{hid}.xml')
                context.verbose(rf'Merging implementation nodes into {xml_file}')
                root = xml_utils.read(xml_file)
                compounddef = root.find(r'compounddef')
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
    if 1 and context.implementation_headers:
        for hdata in implementation_header_data:
            for ip, ifn, iid in hdata[3]:
                delete_file(Path(context.temp_xml_dir, rf'{iid}.xml'), logger=context.verbose_logger)

    # scan through the files and substitute impl header ids and paths as appropriate
    if 1 and context.implementation_headers:
        xml_files = get_all_files(context.temp_xml_dir, any=('*.xml'))
        for xml_file in xml_files:
            context.verbose(rf"Re-linking implementation headers in '{xml_file}'")
            xml_text = read_all_text_from_file(xml_file, logger=context.verbose_logger)
            for hp, hfn, hid, impl in implementation_header_data:
                for ip, ifn, iid in impl:
                    # xml_text = xml_text.replace(f'refid="{iid}"',f'refid="{hid}"')
                    xml_text = xml_text.replace(rf'compoundref="{iid}"', f'compoundref="{hid}"')
                    xml_text = xml_text.replace(ip, hp)
            xml_utils.write(xml_text, xml_file)


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

    class Trie(object):
        def __init__(self):
            self.__trie = TrieRegEx()
            self.__count = 0

        def add(self, s: str):
            if not s:
                return
            self.__trie.add(s)
            self.__count += 1

        def __bool__(self) -> bool:
            return self.__count > 0

        def __str__(self) -> str:
            return self.__trie.regex()

    class Tries(object):
        def __init__(self):
            self.namespaces = Trie()
            self.types = Trie()
            self.enum_values = Trie()
            self.macros = Trie()
            self.functions = Trie()

    tries = Tries()

    def name_ok(s: str) -> bool:
        return s is not None and s and not re.search(r'[^a-zA-Z0-9_:]', s)

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
            xml_file, parser=xml_utils.create_parser(remove_blank_text=True), logger=context.verbose_logger  #
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
            parent = elem.getparent()
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

    context.code_blocks.namespaces = regex_or(
        context.code_blocks.namespaces, pattern_prefix=r'(?:::)?', pattern_suffix=r'(?:::)?'
    )
    context.code_blocks.types = regex_or(
        context.code_blocks.types, pattern_prefix=r'(?:::)?', pattern_suffix=r'(?:::)?'
    )
    context.code_blocks.enums = regex_or(context.code_blocks.enums, pattern_prefix=r'(?:::)?')
    context.code_blocks.functions = regex_or(context.code_blocks.functions, pattern_prefix=r'(?:::)?')
    context.code_blocks.macros = regex_or(context.code_blocks.macros)
    context.autolinks = tuple(
        [(re.compile(r'(?<![a-zA-Z_])' + expr + r'(?![a-zA-Z_])'), uri) for expr, uri in context.autolinks]
    )


def preprocess_mcss_config(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    # build HTML_HEADER
    html_header = ''
    if 1:
        # stylesheets
        for stylesheet in context.stylesheets:
            assert stylesheet is not None
            html_header += f'<link href="{stylesheet}" rel="stylesheet" referrerpolicy="no-referrer" />\n'
        # scripts
        for script in context.scripts:
            assert script is not None
            html_header += f'<script src="{script}"></script>\n'
        if context.theme != r'custom':
            assert context.theme is not None
            html_header += f'<script>initialize_theme("{context.theme}");</script>\n'

        # metadata
        def add_meta_kvp(key_name, key, content):
            nonlocal html_header
            html_header += f'<meta {key_name}="{key}" content="{content}">\n'

        add_meta = lambda key, content: add_meta_kvp(r'name', key, content)
        add_property = lambda key, content: add_meta_kvp(r'property', key, content)
        add_itemprop = lambda key, content: add_meta_kvp(r'itemprop', key, content)
        # metadata - project name
        if context.name:
            if r'twitter:title' not in context.meta_tags:
                add_meta(r'twitter:title', context.name)
            add_property(r'og:title', context.name)
            add_itemprop(r'name', context.name)
        # metadata - project author
        if context.author:
            if r'author' not in context.meta_tags:
                add_meta(r'author', context.author)
            add_property(r'article:author', context.author)
        # metadata - project description
        if context.description:
            if r'description' not in context.meta_tags:
                add_meta(r'description', context.description)
            if r'twitter:description' not in context.meta_tags:
                add_meta(r'twitter:description', context.description)
            add_property(r'og:description', context.description)
            add_itemprop(r'description', context.description)
        # metadata - robots
        if not context.robots:
            if r'robots' not in context.meta_tags:
                add_meta(r'robots', r'noindex, nofollow')
            if r'googlebot' not in context.meta_tags:
                add_meta(r'googlebot', r'noindex, nofollow')
        # metadata - misc
        if r'format-detection' not in context.meta_tags:
            add_meta(r'format-detection', r'telephone=no')
        if r'generator' not in context.meta_tags:
            add_meta(r'generator', rf'Poxy v{VERSION_STRING}')
        if r'referrer' not in context.meta_tags:
            add_meta(r'referrer', r'strict-origin-when-cross-origin')
        # metadata - additional user-specified tags
        for name, content in context.meta_tags.items():
            add_meta(name, content)
        # html_header
        if context.html_header:
            html_header += f'{context.html_header}\n'
        html_header = html_header.rstrip()

    # build + write conf.py
    with StringIO(newline='\n') as conf_py:
        conf = lambda s='', end='\n': print(reindent(s, indent=''), file=conf_py, end=end)

        # basic properties
        conf(rf"DOXYFILE = r'{context.doxyfile_path}'")
        conf(r"STYLESHEETS = []")  # suppress the default behaviour
        conf(rf'HTML_HEADER = """{html_header}"""')
        if context.theme == r'dark':
            conf(r"THEME_COLOR = '#22272e'")
        elif context.theme == r'light':
            conf(r"THEME_COLOR = '#cb4b16'")
        if context.favicon:
            conf(rf"FAVICON = r'{context.favicon}'")
        elif context.theme == r'dark':
            conf(rf"FAVICON = 'favicon-dark.png'")
        elif context.theme == r'light':
            conf(rf"FAVICON = 'favicon-light.png'")
        conf(rf'SHOW_UNDOCUMENTED = {context.sources.extract_all}')
        conf(r'CLASS_INDEX_EXPAND_LEVELS = 3')
        conf(r'FILE_INDEX_EXPAND_LEVELS = 3')
        conf(r'CLASS_INDEX_EXPAND_INNER = True')
        conf(r'SEARCH_DOWNLOAD_BINARY = False')
        conf(r'SEARCH_DISABLED = False')

        # navbar
        NAVBAR_ALIASES = {
            # poxy -> doxygen
            r'classes': r'annotated',
            r'groups': r'modules',
        }
        NAVBAR_TO_KIND = {
            r'annotated': (r'class', r'struct', r'union'),
            r'concepts': (r'concept',),
            r'namespaces': (r'namespace',),
            r'pages': (r'page',),
            r'modules': (r'group',),
            r'files': (r'file', r'dir'),
        }
        navbar = ([], [])
        if context.navbar:
            # populate the navbar
            bar = [(NAVBAR_ALIASES[b] if b in NAVBAR_ALIASES else b) for b in context.navbar]
            # remove links to index pages that will have no entries
            for i in range(len(bar)):
                if bar[i] not in NAVBAR_TO_KIND:
                    continue
                found = False
                for kind in NAVBAR_TO_KIND[bar[i]]:
                    if kind in context.compound_kinds:
                        found = True
                        break
                if not found:
                    bar[i] = None
            bar = [b for b in bar if b is not None]
            # handle theme, repo, sponsor, twitter, version
            for i in range(len(bar)):
                bar[i] = bar[i].strip()
                if bar[i] == r'repo':
                    if not context.repo:
                        bar[i] = None
                        continue
                    icon_path = Path(paths.IMG, context.repo.icon_filename)
                    if icon_path.exists():
                        svg = SVG(icon_path, logger=context.verbose_logger, root_id=r'poxy-icon-repo')
                        bar[i] = (
                            rf'<a title="View on {type(context.repo).__name__}" '
                            + rf'target="_blank" href="{context.repo.uri}" '
                            + rf'class="poxy-icon repo {context.repo.KEY}">{svg}</a>',
                            [],
                        )
                    else:
                        bar[i] = None
                elif bar[i] == r'theme':
                    svg = SVG(
                        Path(paths.IMG, r'poxy-icon-theme.svg'),
                        logger=context.verbose_logger,
                        root_id=r'poxy-theme-switch-img',
                    )
                    bar[i] = (
                        r'<a title="Toggle dark and light themes" '
                        + r'id="poxy-theme-switch" href="javascript:void(null);" role="button" '
                        + rf'class="poxy-icon theme" onClick="toggle_theme(); return false;">{svg}</a>',
                        [],
                    )
                elif bar[i] == r'twitter':
                    svg = SVG(
                        Path(paths.IMG, r'poxy-icon-twitter.svg'),
                        logger=context.verbose_logger,
                        root_id=r'poxy-icon-twitter',
                    )
                    bar[i] = (
                        rf'<a title="Twitter" '
                        + rf'target="_blank" href="https://twitter.com/{context.twitter}" '
                        + rf'class="poxy-icon twitter">{svg}</a>',
                        [],
                    )
                elif bar[i] == r'sponsor':
                    svg = SVG(
                        Path(paths.IMG, r'poxy-icon-sponsor.svg'),
                        logger=context.verbose_logger,
                        root_id=r'poxy-icon-sponsor',
                    )
                    bar[i] = (
                        rf'<a title="Become a sponsor" '
                        + rf'target="_blank" href="{context.sponsorship_uri}" '
                        + rf'class="poxy-icon sponsor">{svg}</a>',
                        [],
                    )
                elif bar[i] == r'version':
                    bar[i] = (rf'<span class="poxy-navbar-version-selector">FIXME</span>', [])
                elif bar[i] in context.compounds:
                    bar[i] = (
                        rf'<a href="{context.compounds[bar[i]]["filename"]}">{context.compounds[bar[i]]["title"]}</a>',
                        [],
                    )
                elif re.search(r'^\s*<\s*[aA]\s+', bar[i]):
                    bar[i] = (bar[i], [])
                elif re.search(r'[.]html?\s*$', bar[i], flags=re.I) and not is_uri(bar[i]):
                    if bar[i] in context.compound_pages:
                        bar[i] = (rf'<a href="{bar[i]}">{context.compound_pages[bar[i]]["title"]}</a>', [])
                    else:
                        bar[i] = (rf'<a href="{bar[i]}">{bar[i]}</a>', [])
            bar = [b for b in bar if b is not None]
            # automatically overflow onto the second row
            split = min(max(int(len(bar) / 2) + len(bar) % 2, 2), len(bar))
            for b, i in ((bar[:split], 0), (bar[split:], 1)):
                for j in range(len(b)):
                    if isinstance(b[j], tuple):
                        navbar[i].append(b[j])
                    else:
                        navbar[i].append((None, b[j], []))
        for i in (0, 1):
            if navbar[i]:
                conf(f'LINKS_NAVBAR{i+1} = [\n\t', end='')
                conf(',\n\t'.join([rf'{b}' for b in navbar[i]]))
                conf(r']')
            else:
                conf(rf'LINKS_NAVBAR{i+1} = []')

        # footer
        conf(r"FINE_PRINT = r'''")
        footer = []
        if context.repo:
            footer.append(rf'<a href="{context.repo.uri}" target="_blank">{type(context.repo).__name__}</a>')
            footer.append(rf'<a href="{context.repo.issues_uri}" target="_blank">Report an issue</a>')
        if context.sponsorship_uri:
            footer.append(rf'<a href="{context.sponsorship_uri}" class="sponsor" target="_blank">Become a sponsor</a>')
        if context.changelog:
            footer.append(rf'<a href="md_poxy_changelog.html">Changelog</a>')
        if context.license and context.license[r'uri']:
            footer.append(rf'<a href="{context.license["uri"]}" target="_blank">License</a>')
        if context.generate_tagfile:
            footer.append(
                rf'<a href="{context.tagfile_path.name}" target="_blank" type="text/xml" download>Doxygen tagfile</a>'
            )
        if footer:
            for i in range(1, len(footer)):
                footer[i] = r' &bull; ' + footer[i]
            footer.append(r'<br><br>')
        footer.append(r'Site generated using <a href="https://github.com/marzer/poxy/">Poxy</a>')
        for i in range(len(footer)):
            conf(rf"    {footer[i]}")
        conf(r"'''")

        conf_py_text = conf_py.getvalue()
        context.verbose(r'm.css conf.py:')
        context.verbose(conf_py_text, indent=r'   ')

        # write conf.py
        context.verbose(rf'Writing {context.mcss_conf_path}')
        with open(context.mcss_conf_path, r'w', encoding=r'utf-8', newline='\n') as f:
            f.write(conf_py_text)


_worker_context = None


def _initialize_worker(context):
    global _worker_context
    _worker_context = context


def postprocess_html_file(path, context: Context = None):
    assert path is not None
    assert isinstance(path, Path)
    assert path.is_absolute()
    assert path.exists()

    if context is None:
        global _worker_context
        context = _worker_context
    assert context is not None
    assert isinstance(context, Context)

    context.info(rf'Post-processing {path}')
    text = None
    html = None

    def switch_to_html():
        nonlocal context
        nonlocal text
        nonlocal html
        if html is not None:
            return
        html = soup.HTMLDocument(text, logger=context.verbose_logger)

    def switch_to_text():
        nonlocal context
        nonlocal text
        nonlocal html
        if html is None:
            return
        html.smooth()
        text = str(html)
        html = None

    try:
        text = read_all_text_from_file(path, logger=context.verbose_logger)
        changed = False

        for fix in context.fixers:
            if isinstance(fix, fixers.HTMLFixer):
                switch_to_html()
                if fix(context, html, path):
                    changed = True
                    html.smooth()
            elif isinstance(fix, fixers.PlainTextFixer):
                switch_to_text()
                new_text = fix(context, text, path)
                if new_text is not None and new_text != text:
                    text = new_text
                    changed = True

        if changed:
            switch_to_text()
            context.verbose(rf'Writing {path}')
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)

    except Exception as e:
        context.info(rf'{type(e).__name__} raised while post-processing {path}')
        raise
    except:
        context.info(rf'Error occurred while post-processing {path}')
        raise


def postprocess_html(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    files = filter_filenames(
        get_all_files(context.html_dir, any=('*.html', '*.htm')), context.html_include, context.html_exclude
    )
    if not files:
        return

    context.fixers = fixers.create_all()

    threads = min(len(files), context.threads, 16)
    context.info(rf'Post-processing {len(files)} HTML files on {threads} thread{"s" if threads > 1 else ""}...')
    if threads > 1:
        with futures.ProcessPoolExecutor(
            max_workers=threads, initializer=_initialize_worker, initargs=(context,)
        ) as executor:
            jobs = [executor.submit(postprocess_html_file, file) for file in files]
            for future in futures.as_completed(jobs):
                try:
                    future.result()
                except:
                    try:
                        executor.shutdown(wait=False, cancel_futures=True)
                    except TypeError:
                        executor.shutdown(wait=False)
                    raise

    else:
        for file in files:
            postprocess_html_file(file, context)


# ======================================================================================================================
# RUN
# ======================================================================================================================


def read_output_streams(stdout, stderr):
    stdout.seek(0)
    stderr.seek(0)
    return {r'stdout': stdout.read().strip(), r'stderr': stderr.read().strip()}


def dump_output_streams(context, outputs, source=''):
    if source:
        source = rf'{source} '
    if outputs[r'stdout']:
        context.info(rf'{source}stdout:')
        context.info(outputs[r'stdout'], indent=r'    ')
    if outputs[r'stderr']:
        context.info(rf'{source}stderr:')
        context.info(outputs[r'stderr'], indent=r'    ')


_warnings_regexes = (
    # doxygen
    re.compile(r'^(?P<file>.+?):(?P<line>[0-9]+): warning:\s*(?P<text>.+?)\s*$', re.I),
    # m.css
    re.compile(r'^WARNING:root:(?P<file>.+[.]xml):\s*(?P<text>.+?)\s*$', re.I),
    re.compile(r'^WARNING:root:\s*(?P<text>.+?)\s*$', re.I),
    # catch-all
    re.compile(r'^(?:Warning|Error):\s*(?P<text>.+?)\s*$', re.I),
)
_warnings_trim_suffixes = (r'Skipping it...',)
_warnings_substitutions = ((r'does not exist or is not a file', r'did not exist or was not a file'),)
_warnings_ignored = (r'inline code has multiple lines, fallback to a code block', r'libgs not found')


def extract_warnings(outputs):
    if not outputs:
        return []

    global _warnings_regexes
    global _warnings_ignored
    global _warnings_trim_suffixes
    global _warnings_substitutions

    warnings = []
    for k, v in outputs.items():
        if not v:
            continue
        output = v.split('\n')
        for o in output:
            for regex in _warnings_regexes:
                m = regex.fullmatch(o)
                if m:
                    text = m[r'text'].strip()
                    for suffix in _warnings_trim_suffixes:
                        if text.endswith(suffix):
                            text = text[: -len(suffix)].strip()
                            break
                    for old, new in _warnings_substitutions:
                        text = text.replace(old, new)
                    if not text or text in _warnings_ignored:
                        break
                    groups = m.groupdict()
                    if r'file' in groups:
                        if r'line' in groups:
                            warnings.append(rf"{m[r'file']}:{m[r'line']}: {text}")
                        else:
                            warnings.append(rf"{m[r'file']}: {text}")
                    else:
                        warnings.append(text)
                    break
    return warnings


def run_doxygen(context: Context):
    assert context is not None
    assert isinstance(context, Context)
    with make_temp_file() as stdout, make_temp_file() as stderr:
        try:
            subprocess.run(
                [str(doxygen.path()), str(context.doxyfile_path)],
                check=True,
                stdout=stdout,
                stderr=stderr,
                cwd=context.input_dir,
            )
        except:
            context.info(r'Doxygen failed!')
            dump_output_streams(context, read_output_streams(stdout, stderr), source=r'Doxygen')
            raise
        if context.is_verbose() or context.warnings.enabled:
            outputs = read_output_streams(stdout, stderr)
            if context.is_verbose():
                dump_output_streams(context, outputs, source=r'Doxygen')
            if context.warnings.enabled:
                warnings = extract_warnings(outputs)
                for w in warnings:
                    context.warning(w)

    # remove the local paths from the tagfile since they're meaningless (and a privacy breach)
    if context.generate_tagfile and context.tagfile_path:
        text = read_all_text_from_file(context.tagfile_path, logger=context.verbose_logger)
        text = re.sub(r'\n\s*?<path>.+?</path>\s*?\n', '\n', text, re.S)
        context.verbose(rf'Writing {context.tagfile_path}')
        with open(context.tagfile_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)


def run_mcss(context: Context):
    assert context is not None
    assert isinstance(context, Context)

    if platform.system().lower() == 'linux':
        if not shutil.which(r'dvisvgm'):
            context.warning(
                r'could not find dvisvgm, or it was not executable; '
                r'm.css may fail with an error about libgs.so (hint: install dvisvgm with APT or similar)'
            )

    with make_temp_file() as stdout, make_temp_file() as stderr:
        doxy_args = [str(context.mcss_conf_path), r'--no-doxygen', r'--sort-globbed-files']
        if context.is_verbose():
            doxy_args.append(r'--debug')
        try:

            env = {k: v for k, v in os.environ.items()}

            if 'LIBGS' not in env and platform.system().lower() == 'linux':
                libgs_set = False

                def try_set_libgs(p: Path) -> bool:
                    nonlocal libgs_set
                    nonlocal env
                    if libgs_set:
                        return True
                    p = coerce_path(p)
                    if not p:
                        return False
                    p = p.resolve()
                    if not p.is_file():
                        return False
                    env['LIBGS'] = str(p)
                    libgs_set = True
                    return True

                machine = platform.machine()
                if machine:
                    for prefix in ('/local/', '/'):
                        for i in range(20, 9, -1):
                            for j in range(20, -1, -1):
                                if try_set_libgs(rf"/usr{prefix}lib/{machine}-linux-gnu/libgs.so.{i}.{j:02}"):
                                    break
                            if libgs_set or try_set_libgs(rf"/usr{prefix}lib/{machine}-linux-gnu/libgs.so.{i}"):
                                break
                        if libgs_set:
                            break

            run_python_script(
                Path(paths.MCSS, r'documentation/doxygen.py'),
                *doxy_args,
                stdout=stdout,
                stderr=stderr,
                cwd=context.input_dir,
                env=env,
            )

        except:
            context.info(r'm.css failed!')
            dump_output_streams(context, read_output_streams(stdout, stderr), source=r'm.css')
            raise
        if context.is_verbose() or context.warnings.enabled:
            outputs = read_output_streams(stdout, stderr)
            if context.is_verbose():
                dump_output_streams(context, outputs, source=r'm.css')
            if context.warnings.enabled:
                warnings = extract_warnings(outputs)
                for w in warnings:
                    context.warning(w)


def run(
    config_path: Path = None,
    output_dir: Path = '.',
    output_html: bool = True,
    output_xml: bool = False,
    threads: int = -1,
    cleanup: bool = True,
    verbose: bool = False,
    logger=None,
    html_include: str = None,
    html_exclude: str = None,
    treat_warnings_as_errors: bool = None,
    theme: str = None,
    copy_assets: bool = True,
    temp_dir: Path = None,
    copy_config_to: Path = None,
    versions_in_navbar: bool = False,
    keep_original_xml: bool = False,
    **kwargs,
):
    timer = lambda desc: ScopeTimer(desc, print_start=True, print_end=context.verbose_logger)

    with Context(
        config_path=config_path,
        output_dir=output_dir,
        output_html=output_html,
        output_xml=output_xml,
        threads=threads,
        cleanup=cleanup,
        verbose=verbose,
        logger=logger,
        html_include=html_include,
        html_exclude=html_exclude,
        treat_warnings_as_errors=treat_warnings_as_errors,
        theme=theme,
        copy_assets=copy_assets,
        temp_dir=temp_dir,
        copy_config_to=copy_config_to,
        versions_in_navbar=versions_in_navbar,
        **kwargs,
    ) as context:
        preprocess_doxyfile(context)
        preprocess_tagfiles(context)
        preprocess_temp_markdown_files(context)

        if not context.output_html and not context.output_xml:
            return

        # generate + postprocess XML in temp_xml_dir
        # (we always do this even when output_xml is false because it is required by the html)
        with timer(rf'Generating XML files with Doxygen {doxygen.version_string()}') as t:
            delete_directory(context.temp_original_xml_dir)
            run_doxygen(context)
            if keep_original_xml:
                copy_tree(context.temp_xml_dir, context.temp_original_xml_dir)
                clean_xml(context, dir=context.temp_original_xml_dir)
        with timer(r'Post-processing XML files') as t:
            if context.xml_v2:
                preprocess_xml_v2(context)
            else:
                preprocess_xml(context)
            parse_xml(context)
            clean_xml(context)

        with timer(r'Compiling regexes') as t:
            compile_regexes(context)

        # XML (the user-requested copy)
        if context.output_xml:
            with ScopeTimer(r'Copying XML', print_start=True, print_end=context.verbose_logger) as t:
                copy_tree(context.temp_xml_dir, context.xml_dir)

            # copy tagfile
            if context.generate_tagfile and context.tagfile_path:
                copy_file(context.tagfile_path, context.xml_dir, logger=context.verbose_logger)

        # HTML
        if context.output_html:
            # generate HTML with mcss
            preprocess_mcss_config(context)
            with timer(r'Generating HTML files with m.css') as t:
                run_mcss(context)

            # copy extra_files
            with ScopeTimer(r'Copying extra_files', print_start=True, print_end=context.verbose_logger) as t:
                for dest_name, source_path in context.extra_files.items():
                    dest_path = Path(context.html_dir, dest_name).resolve()
                    dest_path.parent.mkdir(exist_ok=True)
                    copy_file(source_path, dest_path, logger=context.verbose_logger)

            # copy fonts
            if context.copy_assets:
                with ScopeTimer(r'Copying fonts', print_start=True, print_end=context.verbose_logger) as t:
                    copy_tree(paths.FONTS, Path(context.assets_dir, r'fonts'))

            # copy tagfile
            if context.generate_tagfile and context.tagfile_path:
                copy_file(context.tagfile_path, context.html_dir, logger=context.verbose_logger)

            # post-process html files
            with timer(r'Post-processing HTML files') as t:
                postprocess_html(context)
