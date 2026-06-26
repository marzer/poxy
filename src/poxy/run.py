#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
The 'actually do the thing' module.
"""

import os
import platform
import shutil
import subprocess
import tempfile

from . import doxygen
from .pipeline.doxyfile import preprocess_doxyfile, preprocess_tagfiles, preprocess_temp_markdown_files
from .pipeline.html import postprocess_html, preprocess_mcss_config
from .pipeline.xml import clean_xml, compile_regexes, parse_xml, preprocess_xml, preprocess_xml_v2
from .project import Context
from .utils import *
from .version import *


def copy_tree(src, dest):
    shutil.copytree(str(src), str(dest), dirs_exist_ok=True)


# =======================================================================================================================
# HELPERS
# =======================================================================================================================


def make_temp_file():
    return tempfile.SpooledTemporaryFile(mode='w+', newline='\n', encoding='utf-8')


# =======================================================================================================================
# PRE/POST PROCESSORS
# =======================================================================================================================


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


# m.css dies on a bare AssertionError when malformed markup nests a block element inside an inline span;
# match that one assert (others fall through to the generic bug path, more likely a poxy normalisation gap)
_mcss_block_in_inline_assert = r"element.tag in ['para'"


def diagnose_mcss_failure(stderr: str) -> typing.Optional[str]:
    if not stderr:
        return None
    if r'AssertionError' not in stderr or _mcss_block_in_inline_assert not in stderr:
        return None
    # m.css names the parsed file only at debug level; best normal-run hint is the last WARNING:root: line
    # (the crashing file, or one parsed just before it)
    current = None
    for m in re.finditer(r'^WARNING:root:(?P<file>[^\s:]+\.xml):', stderr, re.M | re.I):
        current = m[r'file']
    hint = rf" (m.css was last working on '{current}')" if current else r''
    return (
        r"m.css crashed: Doxygen produced structurally invalid XML in which a block-level element (a"
        rf" list, code block, blockquote or table) is nested inside an inline span.{hint}"
        "\nThis is almost always malformed markup. Check the Doxygen warnings printed above for the"
        r' source file and line; the tell-tale signs are "found </em> at different nesting level" or'
        r' "end of comment block while expecting command </...>". A common trigger is a markdown block'
        r" marker (> - * or a digit) sitting inside an emphasis/bold span - e.g. *Advanced > Proceed* -"
        r" or an unclosed * / _ marker."
        "\nIf the markup is genuinely correct this may instead be a poxy normalisation gap - please"
        r" re-run with --bug-report and file an issue at github.com/marzer/poxy/issues."
    )


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
        # .*? (not .+?) so the empty <path></path> newer doxygen emits is stripped too, not just
        # older doxygen's machine-specific path; otherwise the two diverge after the empty one folds to <path/>
        text = re.sub(r'\n\s*?<path>.*?</path>\s*?\n', '\n', text)
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

                def try_set_libgs(p: typing.Union[Path, str]) -> bool:
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
            outputs = read_output_streams(stdout, stderr)
            dump_output_streams(context, outputs, source=r'm.css')
            diagnosis = diagnose_mcss_failure(outputs[r'stderr'])
            if diagnosis:
                raise Error(diagnosis) from None
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
    config_path: typing.Optional[Path] = None,
    output_dir: typing.Union[Path, str] = '.',
    output_html: bool = True,
    output_xml: bool = False,
    threads: int = -1,
    cleanup: bool = True,
    verbose: bool = False,
    logger=None,
    html_include: typing.Optional[str] = None,
    html_exclude: typing.Optional[str] = None,
    treat_warnings_as_errors: typing.Optional[bool] = None,
    theme: typing.Optional[str] = None,
    copy_assets: bool = True,
    temp_dir: typing.Optional[Path] = None,
    copy_config_to: typing.Optional[Path] = None,
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
        # fail fast on doxygen versions poxy can't normalise correctly (warns on untested-new ones)
        doxygen.check_supported(context)

        # resolve (download + validate) remote tagfiles first, so invalid ones are pruned before the
        # Doxyfile's TAGFILES is written
        preprocess_tagfiles(context)
        preprocess_doxyfile(context)
        preprocess_temp_markdown_files(context)

        if not context.output_html and not context.output_xml:
            return

        # generate + postprocess XML in temp_xml_dir
        # (we always do this even when output_xml is false because it is required by the html)
        with timer(rf'Generating XML files with Doxygen {doxygen.version_string()}'):
            delete_directory(context.temp_original_xml_dir)
            run_doxygen(context)
            if keep_original_xml:
                copy_tree(context.temp_xml_dir, context.temp_original_xml_dir)
                clean_xml(context, dir=context.temp_original_xml_dir)
        with timer(r'Post-processing XML files'):
            if context.xml_v2:
                preprocess_xml_v2(context)
            else:
                preprocess_xml(context)
            parse_xml(context)
            clean_xml(context)

        with timer(r'Compiling regexes'):
            compile_regexes(context)

        # XML (the user-requested copy)
        if context.output_xml:
            with ScopeTimer(r'Copying XML', print_start=True, print_end=context.verbose_logger):
                copy_tree(context.temp_xml_dir, context.xml_dir)

            # copy tagfile
            if context.generate_tagfile and context.tagfile_path:
                copy_file(context.tagfile_path, context.xml_dir, logger=context.verbose_logger)

        # HTML
        if context.output_html:
            # generate HTML with mcss
            preprocess_mcss_config(context)
            with timer(r'Generating HTML files with m.css'):
                run_mcss(context)

            # copy extra_files
            with ScopeTimer(r'Copying extra_files', print_start=True, print_end=context.verbose_logger):
                for dest_name, source_path in context.extra_files.items():
                    dest_path = Path(context.html_dir, dest_name).resolve()
                    dest_path.parent.mkdir(exist_ok=True)
                    copy_file(source_path, dest_path, logger=context.verbose_logger)

            # bundle custom-page iframe content into html/<id>/
            if context.custom_pages:
                with ScopeTimer(r'Copying custom page content', print_start=True, print_end=context.verbose_logger):
                    for page in context.custom_pages:
                        source_path = page[r'content_src']
                        if source_path is None:
                            continue
                        dest_dir = Path(context.html_dir, page[r'id']).resolve()
                        if source_path.is_dir():
                            copy_tree(source_path, dest_dir)
                        else:
                            dest_dir.mkdir(exist_ok=True, parents=True)
                            copy_file(source_path, Path(dest_dir, source_path.name), logger=context.verbose_logger)

            # copy fonts
            if context.copy_assets:
                with ScopeTimer(r'Copying fonts', print_start=True, print_end=context.verbose_logger):
                    copy_tree(paths.FONTS, Path(context.assets_dir, r'fonts'))

            # copy tagfile
            if context.generate_tagfile and context.tagfile_path:
                copy_file(context.tagfile_path, context.html_dir, logger=context.verbose_logger)

            # post-process html files
            with timer(r'Post-processing HTML files'):
                postprocess_html(context)
