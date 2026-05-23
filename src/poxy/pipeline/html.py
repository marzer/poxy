#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
m.css configuration + HTML post-processing stage. Generates the m.css conf.py and runs the
parallel HTML fixers over m.css's output. Extracted verbatim from run.py.
"""

import concurrent.futures as futures
from io import StringIO

from .. import fixers, paths, soup
from ..project import Context
from ..svg import SVG
from ..utils import *
from ..version import *


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
                conf(f'LINKS_NAVBAR{i + 1} = [\n\t', end='')
                conf(',\n\t'.join([rf'{b}' for b in navbar[i]]))
                conf(r']')
            else:
                conf(rf'LINKS_NAVBAR{i + 1} = []')

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


def postprocess_html_file(path, context: typing.Optional[Context] = None):
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
        assert text is not None
        assert context is not None
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
                assert html is not None
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
