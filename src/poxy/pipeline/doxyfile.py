#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Input-preparation stage: builds the locked-down Doxyfile and pre-processes markdown + tagfile inputs
before Doxygen runs. Extracted verbatim from run.py.
"""

import sys
from urllib.parse import quote

from lxml import etree

from .. import doxygen, mdfilter, paths
from ..project import Context
from ..utils import *

# AI-assistant instruction files: never documentation, but commonly sat at a repo root alongside README.md
# where doxygen's input scan picks them up (and chokes on their '@'-prefixed words). auto-excluded by name.
AI_INSTRUCTION_FILES = (
    r'AGENTS.md',
    r'AGENT.md',
    r'CLAUDE.md',
    r'CLAUDE.local.md',
    r'GEMINI.md',
    r'BUGBOT.md',
    r'COPILOT.md',
    r'.cursorrules',
    r'.windsurfrules',
)

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
    (r'IMPLICIT_DIR_DOCS', False),
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

        df.set_value(r'CLANG_OPTIONS', rf'-std=c++{context.cpp % 100}')
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

        # run every markdown file through poxy's standalone filter (uniform preprocessing for all .md, not
        # just the special main_page/changelog temp copies). quoting survives format_for_doxyfile's own
        # quoting (it escapes inner ") so paths with spaces are handled.
        md_filter = rf'"{sys.executable}" "{Path(paths.PACKAGE, r"mdfilter.py")}"'
        df.set_value(r'FILTER_PATTERNS', [rf'*.md={md_filter}', rf'*.markdown={md_filter}'])

        df.set_value(r'EXCLUDE', context.html_dir)
        if context.source_excludes:
            df.add_value(r'EXCLUDE', context.source_excludes)

        # keep AI-assistant instruction files out of the docs wherever they turn up in the input tree
        df.set_value(r'EXCLUDE_PATTERNS', [rf'*/{name}' for name in AI_INSTRUCTION_FILES])

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
        # NB entity (&amp; / &#x..;) protection now lives in mdfilter.py so it applies to every markdown
        # file uniformly, not just these temp copies

        if attr_name == 'changelog':
            if context.repo:
                repo = context.repo
                text = re.sub(r'#([0-9]+)', lambda m: rf'[#{m[1]}]({repo.make_issue_uri(m[1])})', text)
                text = re.sub(r'!([0-9]+)', lambda m: rf'[!{m[1]}]({repo.make_pull_request_uri(m[1])})', text)
                text = re.sub(r'@([a-zA-Z0-9_-]+)', lambda m: rf'[@{m[1]}]({repo.make_user_uri(m[1])})', text)

            text = text.replace(r'@', mdfilter.SENTINEL_AT)
            text = f'\n{text}\n'
            text = re.sub('\n#[^#].+?\n', '\n', text)
            text = f'@page poxy_changelog Changelog\n\n@tableofcontents\n\n{text}'
            text = text.rstrip()
            text += '\n\n'

        context.verbose(rf'Writing {path}')
        with open(path, r'w', encoding=r'utf-8', newline='\n') as f:
            f.write(text)


def tagfile_text_is_valid(text: str) -> bool:
    """
    True if text is an actual Doxygen tagfile (XML with a <tagfile> root), not something else.

    Downloaded tagfile URLs sometimes return an error page instead of the tagfile (e.g. a site is
    reorganized and the old URL now 404s to an HTML page). Doxygen then tries to parse that HTML as a
    tagfile and emits a flood of confusing warnings, so we sanity-check the content before using it.
    """
    if not text or not text.strip():
        return False
    try:
        root = etree.fromstring(text.encode('utf-8'))
    except Exception:
        return False
    return etree.QName(root.tag).localname == 'tagfile'


def preprocess_tagfiles(context: Context):
    assert context is not None
    assert isinstance(context, Context)
    if not context.unresolved_tagfiles:
        return
    invalid_sources = []
    token = None
    token_checked = False
    with ScopeTimer(r'Resolving remote tagfiles', print_start=True, print_end=context.verbose_logger):
        for source, (file, dest) in list(context.tagfiles.items()):
            is_github = is_github_uri(source)
            if not is_github and not is_uri(source):
                continue
            try:
                if is_github:
                    if not token_checked:
                        token = github_token()
                        token_checked = True
                        if not token:
                            context.warning(
                                rf"no GitHub token available (set $GH_TOKEN/$GITHUB_TOKEN or run 'gh auth login'); "
                                rf"trying unauthenticated"
                            )
                    # always resolve the dest (it isn't cached), but only fetch the tagfile when it's missing
                    text, dest = _resolve_github_tagfile(context, str(source), dest, token, fetch=not file.exists())
                    context.tagfiles[source] = (file, dest)
                    if text is None:  # dest resolved above; tagfile content already cached
                        continue
                else:
                    if file.exists():
                        continue
                    context.verbose(rf'Downloading {source}')
                    text = download_text(str(source), timeout=30)
            except Exception as ex:
                context.warning(rf"could not download tagfile from '{source}': {ex}; skipping it")
                invalid_sources.append(source)
                continue
            if not tagfile_text_is_valid(text):
                context.warning(
                    rf"the file downloaded from '{source}' was not a valid Doxygen tagfile "
                    rf"(the server may have returned an error page); skipping it"
                )
                invalid_sources.append(source)
                continue
            context.verbose(rf'Writing {file}')
            with open(file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
    # drop the bad ones so they're not written into the Doxyfile's TAGFILES
    for source in invalid_sources:
        del context.tagfiles[source]


def _resolve_github_tagfile(context: Context, source: str, dest: str, token, fetch: bool):
    """Resolve a 'github://owner/repo/path[@ref]' tagfile. Always resolves the link base (dest) - from the
    repo's Pages URL when not configured - since that isn't cached between runs. Fetches the tagfile content
    only when `fetch` is set (i.e. it isn't already cached on disk). `@release` / `@release:<tag>` pulls a
    release asset; any other `@ref` (or none, defaulting to the Pages deploy branch) reads repo contents.
    Returns (tagfile_text_or_None, dest)."""
    m = GITHUB_TAGFILE_URI.fullmatch(source)
    assert m is not None
    owner, repo, path, ref = m.group(r'owner'), m.group(r'repo'), m.group(r'path'), m.group(r'ref')
    is_release = ref == r'release' or (ref is not None and ref.startswith(r'release:'))

    # the Pages API gives the public-facing link base (when no dest is configured) and the deploy branch
    # (when reading contents without an explicit @ref); only call it when something is actually needed
    pages = None
    if not dest or (fetch and not is_release and ref is None):
        try:
            pages = github_api_get(rf'https://api.github.com/repos/{owner}/{repo}/pages', token).json()
        except Exception as ex:
            context.verbose(rf"could not query Pages info for {owner}/{repo}: {ex}")

    if not dest:
        dest = (pages or {}).get(r'html_url') or r''
        if not dest:
            raise Error(
                rf"could not resolve a Pages URL for {owner}/{repo}; specify the link base explicitly as the "
                rf"value for this tagfile in [tagfiles]"
            )
    if not dest.endswith(r'/'):
        dest += r'/'

    if not fetch:
        return None, dest

    if is_release:
        tag = ref[len(r'release:') :] if ref and ref.startswith(r'release:') else None
        return _fetch_github_release_asset(owner, repo, path, tag, token), dest

    if ref is None:
        ref = (pages or {}).get(r'source', {}).get(r'branch') or r'gh-pages'
    return _fetch_github_contents(owner, repo, path, ref, token), dest


def _fetch_github_contents(owner, repo, path, ref, token) -> str:
    url = rf'https://api.github.com/repos/{owner}/{repo}/contents/{quote(path, safe="/")}?ref={quote(ref, safe="")}'
    try:
        return github_api_get(url, token, accept=r'application/vnd.github.raw').content.decode(r'utf-8')
    except Exception as ex:
        if _github_status(ex) == 404:
            hint = _github_tagfile_candidates_hint(owner, repo, path, ref, token)
            raise Error(
                rf"'{path}' was not found in branch '{ref}' of {owner}/{repo} - has the documentation been "
                rf"published there yet?{hint}"
            ) from None
        raise


def _fetch_github_release_asset(owner, repo, asset_name, tag, token) -> str:
    if tag:
        rel_url = rf'https://api.github.com/repos/{owner}/{repo}/releases/tags/{quote(tag, safe="")}'
    else:
        rel_url = rf'https://api.github.com/repos/{owner}/{repo}/releases/latest'
    try:
        release = github_api_get(rel_url, token).json()
    except Exception as ex:
        if _github_status(ex) == 404:
            which = rf'release tagged {tag}' if tag else r'published (non-draft, non-prerelease) release'
            raise Error(rf"no {which} found for {owner}/{repo}") from None
        raise
    assets = release.get(r'assets') or []
    asset = next((a for a in assets if a.get(r'name') == asset_name), None)
    if asset is None:
        names = r', '.join(sorted(a.get(r'name', r'') for a in assets)) or r'(none)'
        raise Error(
            rf"release '{release.get(r'tag_name', r'?')}' of {owner}/{repo} has no asset named '{asset_name}'; "
            rf"available assets: {names}"
        )
    # the asset's API url 302-redirects to storage; requests drops the auth header on the cross-host hop
    return github_api_get(asset[r'url'], token, accept=r'application/octet-stream').content.decode(r'utf-8')


def _github_status(ex):
    response = getattr(ex, r'response', None)
    return getattr(response, r'status_code', None) if response is not None else None


def _github_tagfile_candidates_hint(owner, repo, path, ref, token) -> str:
    """Best-effort: list the *.tagfile.xml / *.xml files actually present alongside the requested path, so a
    404 from a wrong filename is self-diagnosing. Returns '' if the listing can't be obtained."""
    import posixpath

    directory = posixpath.dirname(path)
    url = (
        rf'https://api.github.com/repos/{owner}/{repo}/contents/{quote(directory, safe="/")}?ref={quote(ref, safe="")}'
    )
    try:
        entries = github_api_get(url, token).json()
        names = [e[r'name'] for e in entries if isinstance(e, dict) and e.get(r'type') == r'file']
    except Exception:
        return r''
    candidates = [n for n in names if n.endswith(r'.tagfile.xml')] or [n for n in names if n.endswith(r'.xml')]
    if not candidates:
        return r''
    listing = posixpath.join(directory, r'') if directory else r''
    return rf" available there: {', '.join(sorted(listing + c for c in candidates))}"
