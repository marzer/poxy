#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
The various entry-point methods used when poxy is invoked from the command line.
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import typing
import zipfile
from pathlib import Path

import colorama
from colorama import Fore, Style

from . import css, doxygen, emoji, graph, mcss, paths
from .run import run
from .schemas import SchemaError
from .utils import *
from .version import *


def _invoker(func, **kwargs):
    colorama.init()
    try:
        func(**kwargs)
    except WarningTreatedAsError as err:
        print(rf'{Style.BRIGHT}{Fore.RED}error:{Style.RESET_ALL} {err} (warning treated as error)', file=sys.stderr)
        sys.exit(1)
    except graph.GraphError as err:
        print_exception(err, include_type=True, include_traceback=True, skip_frames=1)
        sys.exit(1)
    except SchemaError as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    except Error as err:
        print(rf'{Style.BRIGHT}{Fore.RED}error:{Style.RESET_ALL} {err}', file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f'\n{Fore.RED}*************{Style.RESET_ALL}\n', file=sys.stderr)
        print_exception(err, include_type=True, include_traceback=True, skip_frames=1)
        print(
            f'{Fore.RED}*************\n'
            '\nYou appear to have triggered an internal bug!'
            '\nPlease re-run poxy with --bug-report and file an issue at github.com/marzer/poxy/issues'
            '\nMany thanks!'
            f'\n\n*************{Style.RESET_ALL}',
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(0)


def make_boolean_optional_arg(args: argparse.ArgumentParser, name: str, default, help='', **kwargs):
    name = name.strip().lstrip('-')
    if sys.version_info >= (3, 9):
        args.add_argument(rf'--{name}', default=default, help=help, action=argparse.BooleanOptionalAction, **kwargs)
    else:
        dest = name.replace(r'-', r'_')
        args.add_argument(rf'--{name}', action=r'store_true', help=help, dest=dest, default=default, **kwargs)
        args.add_argument(
            rf'--no-{name}',
            action=r'store_false',
            help=(help if help == argparse.SUPPRESS else None),
            dest=dest,
            default=default,
            **kwargs,
        )


def git(git_args: str, cwd=None) -> typing.Tuple[int, str, str]:
    assert git_args is not None
    proc = subprocess.run(
        ['git'] + str(git_args).strip().split(),
        capture_output=True,
        cwd=str(Path.cwd() if cwd is None else cwd),
        encoding='utf-8',
    )
    return (proc.returncode, proc.stdout.strip() if proc.stdout else "", proc.stderr.strip() if proc.stderr else "")


def git_failed(git_output: typing.Tuple[int, str, str], desc=''):
    assert git_output is not None
    message = rf"git command failed"
    if desc:
        message += rf': {desc}'
    if git_output[0] != 0:  # return code
        message += f'\n  {Style.BRIGHT}exit code:{Style.RESET_ALL}\n    {git_output[0]}'
    if git_output[1]:  # stdout
        message += f'\n  {Style.BRIGHT}stdout:{Style.RESET_ALL}\n'
        message += "\n".join([rf'    {i.strip()}' for i in git_output[1].split('\n') if i.strip()])
    if git_output[2]:  # stderr
        message += f'\n  {Style.BRIGHT}stderr:{Style.RESET_ALL}\n'
        message += "\n".join([rf'    {i.strip()}' for i in git_output[2].split('\n') if i.strip()])
    raise Error(message)


def git_failed_if_nonzero(git_output: typing.Tuple[int, str, str], desc=''):
    if git_output[0] != 0:
        git_failed(git_output, desc)
    return git_output


def multi_version_git_tags(args: argparse.Namespace):
    print('Running in git-tags mode')

    input_dir = args.config.resolve()
    if input_dir.is_file():
        input_dir = input_dir.parent

    if git('diff-files --quiet', cwd=input_dir)[0] or git('diff --no-ext-diff --cached --quiet', cwd=input_dir)[0]:
        raise Error(rf'repository has uncommitted changes')

    print('Fetching...')
    git_failed_if_nonzero(git('fetch --tags', cwd=input_dir))

    current_branch = git_failed_if_nonzero(git('rev-parse --abbrev-ref HEAD', cwd=input_dir))[1]
    print(rf'Current branch: {current_branch}')
    original_branch = current_branch

    default_branch = git_failed_if_nonzero(git('rev-parse --abbrev-ref origin/HEAD', cwd=input_dir))[1]
    if default_branch.startswith(r'origin/'):
        default_branch = default_branch[len(r'origin/') :]
    print(rf'Default branch: {default_branch}')

    tags = git_failed_if_nonzero(git('tag', cwd=input_dir))[1].splitlines()
    tags = [(t, t.strip().upper().lstrip('V').lstrip()) for t in tags]
    tags = [(t, v) for t, v in tags if v]
    tags = [(t, re.sub(r'\s+', '', v)) for t, v in tags]
    tags = [(t, re.fullmatch(r'[0-9]+([.][0-9]+([.][0-9]+([.][0-9]+)?)?)?', v)) for t, v in tags]
    tags = [(t, v) for t, v in tags if v]
    tags = [(t, v[0].split('.')) for t, v in tags]
    tags = [
        (t, (int(v[0]), int(v[1]) if len(v) > 1 else 0, int(v[2]) if len(v) > 2 else 0, int(v[3]) if len(v) > 3 else 0))
        for t, v in tags
    ]
    tags = sorted(tags, key=lambda t: t[1], reverse=True)
    tags.insert(0, (default_branch, (999999, 999999, 999999, 999999)))

    if args.squash_patches:
        # squash patch/rev differences
        seen_versions = set()
        for i in range(len(tags)):
            normalized_version = (tags[i][1][0], tags[i][1][1])
            if normalized_version in seen_versions:
                tags[i] = None
                continue
            seen_versions.add(normalized_version)
        tags = [t for t in tags if t]

    if args.min_version is not None:
        args.min_version = re.sub(r'[ \t]+', '', str(args.min_version).strip())
        m = re.fullmatch(r'^[vV]?([0-9]+)(?:[.]([0-9]+)(?:[.]([0-9]+)(?:[.]([0-9]+))?)?)?$', args.min_version)
        if m:
            min_ver = (
                (int(m[1] if m[1] else 0)),
                (int(m[2] if m[2] else 0)),
                (int(m[3] if m[3] else 0)),
                (int(m[4] if m[4] else 0)),
            )
            tags = [t for t in tags if t[1] >= min_ver]
        else:
            try:
                max_vers = int(args.min_version)
                assert max_vers < 0
                tags = tags[:-max_vers]
            except:
                raise Error(rf'min-version: expected semver tag or negative integer')

    tags = [t for t, _ in tags]
    print("Versions:")
    print("\n".join([rf'    {t}' for t in tags]))

    worker_args = [
        arg
        for arg in sys.argv[1:]
        if arg
        not in (
            r'--bug-report',
            r'--git-tags',
            r'--worker',
            r'--versions-in-navbar',
            r'--verbose',
            r'-v',
            r'--higest-patch-only',
        )
    ]
    for key in (r'--output-dir', r'--temp-dir', r'--copy-config-to'):
        pos = -1
        try:
            pos = worker_args.index(key)
        except:
            pass
        if pos != -1:
            worker_args.pop(pos)
            worker_args.pop(pos)

    tags_temp_dir = paths.TEMP / 'tags' / temp_dir_name_for(str(Path.cwd()))
    delete_directory(tags_temp_dir)
    tags_temp_dir.mkdir(exist_ok=True, parents=True)

    def cleanup():
        nonlocal current_branch
        nonlocal original_branch
        nonlocal tags_temp_dir
        nonlocal args
        if not args.nocleanup:
            delete_directory(tags_temp_dir)
        if current_branch != original_branch:
            print(rf'Switching back to {Style.BRIGHT}{original_branch}{Style.RESET_ALL}')
            git_failed_if_nonzero(git(rf'checkout {original_branch}', cwd=input_dir))
            current_branch = original_branch

    emitted_tags = set()
    with Defer(cleanup):
        for tag in tags:
            if current_branch != tag:
                print(rf'Checking out {Style.BRIGHT}{tag}{Style.RESET_ALL}')
                git_failed_if_nonzero(git(rf'checkout {tag}', cwd=input_dir))
                current_branch = tag

            if current_branch == default_branch:
                git_failed_if_nonzero(git(rf'pull', cwd=input_dir))

            output_dir = args.output_dir.resolve()
            if tag != default_branch:
                output_dir = tags_temp_dir / tag
                output_dir.mkdir(exist_ok=True, parents=True)

            try:
                print(rf'Generating documentation for {Style.BRIGHT}{tag}{Style.RESET_ALL}')
                result = subprocess.run(
                    args=[
                        r'poxy',
                        r'--worker',
                        r'--versions-in-navbar',
                        r'--output-dir',
                        str(output_dir),
                        *worker_args,
                    ],
                    cwd=str(Path.cwd()),
                    capture_output=not args.verbose,
                    encoding='utf-8',
                )
                if result.returncode != 0:
                    raise Error(
                        rf'Poxy exited with code {result.returncode}{"" if args.verbose else " (re-run with --verbose to see worker output)"}'
                    )
            except Exception as exc:
                msg = rf'documentation generation failed for {Style.BRIGHT}{tag}{Style.RESET_ALL}: {exc}'
                if args.werror:
                    raise WarningTreatedAsError(msg)
                else:
                    print(rf'{Style.BRIGHT}{Fore.YELLOW}warning:{Style.RESET_ALL} {msg}', file=sys.stderr)
                    continue

            if tag != default_branch:
                source_dir = output_dir
                output_dir = args.output_dir.resolve()
                for src in ('html' if args.html else None, 'xml' if args.xml else None):
                    if src is None:
                        continue
                    src = source_dir / src
                    if not src.is_dir():
                        continue
                    dest = output_dir / src.name / tag
                    dest.mkdir(exist_ok=True, parents=True)
                    delete_directory(src / 'poxy')
                    delete_file(src / 'poxy_changelog.html')
                    delete_file(src / 'md_poxy_changelog.html')
                    shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
                    if not args.nocleanup:
                        delete_directory(src)

            emitted_tags.add(tag)

    if not args.html:
        return

    print("Linking versions in HTML output")
    tags = [t for t in tags if t in emitted_tags]
    html_root = args.output_dir.resolve() / 'html'
    for tag in tags:
        html_dir = html_root
        if tag != default_branch:
            html_dir /= tag
        assert_existing_directory(html_dir)
        for fp in get_all_files(html_dir, any=('*.css', '*.html', '*.js'), recursive=False):
            text = read_all_text_from_file(fp)
            if tag != default_branch:
                text = text.replace('href="poxy/', 'href="../poxy/')
                text = text.replace('href="poxy_changelog.html', 'href="../poxy_changelog.html')
                text = text.replace('href="md_poxy_changelog.html', 'href="../md_poxy_changelog.html')
                text = text.replace('src="poxy/', 'src="../poxy/')
            versions = rf'<li class="poxy-navbar-version-selector"><a href="{fp.name}">Version: {"HEAD" if tag == default_branch else tag}</a><ol>'
            for dest_tag in tags:
                target = html_root
                if dest_tag != default_branch:
                    target /= dest_tag
                assert target.is_dir()
                target /= fp.name
                if not target.is_file():
                    target = target.parent / 'index.html'
                assert target.is_file()
                if tag == default_branch and dest_tag != default_branch:
                    target = rf'{dest_tag}/{target.name}'
                elif tag != default_branch and dest_tag == default_branch:
                    target = rf'../{target.name}'
                elif tag != dest_tag:
                    target = rf'../{dest_tag}/{target.name}'
                else:
                    target = target.name
                versions += (
                    rf'<li><a href="{str(target)}">{"HEAD" if dest_tag == default_branch else dest_tag}</a></li>'
                )
            versions += rf'</ol></li>'
            text = re.sub(
                r'<li>\s*<span\s+class="poxy-navbar-version-selector"\s*>\s*FIXME\s*</span>\s*</li>',
                versions,
                text,
                flags=re.I,
            )
            with open(fp, r'w', newline='\n', encoding=r'utf-8') as f:
                f.write(text)


def bug_report(args: argparse.Namespace):
    bug_report_args = [
        arg
        for arg in sys.argv[1:]
        if arg not in (r'--bug-report', r'--worker', r'-v', r'--verbose', r'--keep-original-xml')
    ]
    for key in (r'--output-dir', r'--temp-dir', r'--copy-config-to'):
        pos = -1
        try:
            pos = bug_report_args.index(key)
        except:
            pass
        if pos != -1:
            bug_report_args.pop(pos)
            bug_report_args.pop(pos)

    if '--git-tags' in bug_report_args:
        raise Error(r'--git-tags is currently incompatible with --bug-report. This will be fixed in a later version!')

    bug_report_zip = (Path.cwd() / r'poxy_bug_report.zip').resolve()

    print(r'Preparing output paths')
    delete_directory(paths.BUG_REPORT_DIR)
    delete_file(bug_report_zip)
    paths.BUG_REPORT_DIR.mkdir(exist_ok=True, parents=True)

    print(r'Invoking poxy')
    result = subprocess.run(
        args=[
            r'poxy',
            r'--worker',
            r'--verbose',
            r'--nocleanup',
            r'--keep-original-xml',
            r'--output-dir',
            str(paths.BUG_REPORT_DIR),
            r'--temp-dir',
            str(paths.BUG_REPORT_DIR / r'temp'),
            r'--copy-config-to',
            str(paths.BUG_REPORT_DIR),
            *bug_report_args,
        ],
        cwd=str(Path.cwd()),
        capture_output=True,
        encoding='utf-8',
    )

    if result.stdout:
        print(r'Writing stdout')
        with open(paths.BUG_REPORT_DIR / r'stdout.txt', r'w', newline='\n', encoding=r'utf-8') as f:
            f.write(result.stdout)

    if result.stderr:
        print(r'Writing stderr')
        with open(paths.BUG_REPORT_DIR / r'stderr.txt', r'w', newline='\n', encoding=r'utf-8') as f:
            f.write(result.stderr)

    print(r'Writing metadata')
    with open(paths.BUG_REPORT_DIR / r'metadata.txt', r'w', newline='\n', encoding=r'utf-8') as f:
        f.write(f'version: {VERSION_STRING}\n')
        f.write(f'args: {bug_report_args}\n')
        f.write(f'returncode: {result.returncode}\n')
        try:
            f.write(f'doxygen: {doxygen.raw_version_string()}\n')
        except:
            f.write(f'doxygen: --version failed\n')

    # zip file
    print(r'Zipping files')
    with zipfile.ZipFile(str(bug_report_zip), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip:
        file_prefix_len = len(str(paths.BUG_REPORT_DIR))
        for file in get_all_files(paths.BUG_REPORT_DIR, recursive=True):
            if file.suffix is not None and file.suffix.lower() in (r'.pyc',):
                continue
            relative_file = str(file)[file_prefix_len:].replace('\\', '/').strip('/')
            zip.write(file, arcname=rf'poxy_bug_report/{relative_file}')

    print(r'Cleaning up')
    delete_directory(paths.BUG_REPORT_DIR)

    print(
        f'Zip generated: {Style.BRIGHT}{bug_report_zip}{Style.RESET_ALL}\n'
        rf'{Fore.CYAN}{Style.BRIGHT}Please attach this file when you make a report at https://github.com/marzer/poxy/issues, thanks!{Style.RESET_ALL}'
    )


def main(invoker=True):
    """
    The entry point when the library is invoked as `poxy`.
    """
    if invoker:
        _invoker(main, invoker=False)
        return

    # yapf: disable
    args = argparse.ArgumentParser(
        description=
        rf'{Fore.CYAN}{Style.BRIGHT}'
        r'''  _ __   _____  ___   _ ''' '\n'
        r''' | '_ \ / _ \ \/ / | | |''' '\n'
        r''' | |_) | (_) >  <| |_| |''' '\n'
        r''' | .__/ \___/_/\_\\__, |''' '\n'
        r''' | |               __/ |''' '\n'
        r''' |_|              |___/ ''' rf'{Style.RESET_ALL} v{VERSION_STRING} - github.com/marzer/poxy'
        '\n\n'
        r'Generate fancy C++ documentation.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    # yapf: enable

    # --------------------------------------------------------------
    # public user-facing arguments
    # --------------------------------------------------------------

    args.add_argument(
        r'config',
        type=Path,
        nargs='?',
        default=Path.cwd(),
        help=r'path to poxy.toml or a directory containing it (default: .)',
    )
    args.add_argument(r'-v', r'--verbose', action=r'store_true', help=r"enable very noisy diagnostic output")  #
    make_boolean_optional_arg(args, r'html', default=True, help=r'specify whether HTML output is required')  #
    args.add_argument(
        r'--ppinclude',  #
        type=str,
        default=None,
        metavar=r'<regex>',
        help=r"pattern matching HTML file names to post-process (default: all)",
    )
    args.add_argument(
        r'--ppexclude',  #
        type=str,
        default=None,
        metavar=r'<regex>',
        help=r"pattern matching HTML file names to exclude from post-processing (default: %(default)s)",
    )
    args.add_argument(
        r'--theme',  #
        choices=[r'light', r'dark', r'custom'],
        default=None,
        help=r'sets the default visual theme (default: read from config)',
    )
    args.add_argument(
        r'--threads',
        type=int,
        default=0,
        metavar=r'N',
        help=r"set the number of threads to use (default: automatic)",  #
    )
    args.add_argument(r'--version', action=r'store_true', help=r"print the version and exit", dest=r'print_version')  #
    make_boolean_optional_arg(args, r'xml', default=False, help=r'specify whether XML output is required')  #
    make_boolean_optional_arg(
        args, r'werror', default=None, help=r'treat warnings as errors (default: read from config)'
    )  #
    args.add_argument(
        r'--bug-report', action=r'store_true', help=r"captures all output in a zip file for easier bug reporting."  #
    )
    args.add_argument(
        r'--git-tags', action=r'store_true', help=r"add git-tag-based semver version switcher to the generated HTML"  #
    )
    make_boolean_optional_arg(
        args,
        r'squash-patches',
        default=True,
        help='when using --git-tags and two version tags differ by a patch number,\ngenerate docs for the highest one only (default: %(default)s)',
    )
    args.add_argument(
        r'--min-version',
        type=str,
        default=None,
        metavar='<version>',
        help='sets the minimum version number to emit when using --git-tags,\nor a negative integer to mean "the last N versions". (default: %(default)s)',
    )

    # --------------------------------------------------------------
    # hidden/developer-only/deprecated/diagnostic arguments
    # --------------------------------------------------------------

    args.add_argument(r'--where', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--nocleanup', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--noassets', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--update-styles', action=r'store_true', help=argparse.SUPPRESS)  #
    make_boolean_optional_arg(args, r'update-fonts', default=None, help=argparse.SUPPRESS)
    args.add_argument(r'--update-emoji', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--update-tests', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--doxygen-version', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--update-mcss', type=Path, default=None, help=argparse.SUPPRESS)  #
    args.add_argument(  # --xml and --html are the replacements for --xmlonly
        r'--xmlonly', action=r'store_true', help=argparse.SUPPRESS  #
    )
    args.add_argument(r'--xml-v2', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--worker', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--output-dir', type=Path, default=Path.cwd(), help=argparse.SUPPRESS)  #
    args.add_argument(r'--temp-dir', type=Path, default=None, help=argparse.SUPPRESS)  #
    args.add_argument(r'--copy-config-to', type=Path, default=None, help=argparse.SUPPRESS)  #
    args.add_argument(r'--versions-in-navbar', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--keep-original-xml', action=r'store_true', help=argparse.SUPPRESS)  #
    args = args.parse_args()

    # --------------------------------------------------------------
    # --version
    # --------------------------------------------------------------

    if args.print_version:
        print(VERSION_STRING)
        return

    # --------------------------------------------------------------
    # --doxygen-version
    # --------------------------------------------------------------

    if args.doxygen_version:
        print(doxygen.version_string())
        return

    # --------------------------------------------------------------
    # --where
    # --------------------------------------------------------------

    if args.where:
        print(paths.PACKAGE)
        return

    # --------------------------------------------------------------
    # developer-only subcommands
    # --------------------------------------------------------------

    if args.update_mcss is not None:
        args.update_styles = True
        if args.update_fonts is None:
            args.update_fonts = True
        mcss.update_bundled_install(args.update_mcss)
    assert_existing_directory(paths.MCSS)
    assert_existing_file(Path(paths.MCSS, r'documentation/doxygen.py'))

    if args.update_fonts:
        args.update_styles = True
    if args.update_styles:
        css.regenerate_builtin_styles(use_cached_fonts=not args.update_fonts)

    if args.update_emoji:
        emoji.update_database_file()

    if args.update_tests:
        if not paths.TESTS.exists() or not paths.TESTS.is_dir():
            raise Exception(
                f'{paths.TESTS} did not exist or was not a directory (--update-tests is only for editable installations)'
            )
        run_python_script(
            Path(paths.TESTS, r'regenerate_tests.py'),  #
            *[a for a in (r'--verbose' if args.verbose else None, r'--nocleanup' if args.nocleanup else None) if a],
        )

    if (
        args.update_styles
        or args.update_fonts
        or args.update_emoji
        or args.update_tests
        or args.update_mcss is not None
    ):
        return

    if not args.worker:
        print(rf'{Fore.CYAN}{Style.BRIGHT}poxy{Style.RESET_ALL} v{VERSION_STRING}')

    # --------------------------------------------------------------
    # bug report invocation
    # --------------------------------------------------------------

    if args.bug_report:
        bug_report(args)
        return

    # --------------------------------------------------------------
    # multi-version invocation
    # --------------------------------------------------------------

    if args.git_tags:
        with ScopeTimer(r'All tasks', print_start=False, print_end=True) as timer:
            multi_version_git_tags(args)
        return

    # --------------------------------------------------------------
    # regular invocation
    # --------------------------------------------------------------

    if args.xmlonly:
        args.html = False
        args.xml = True

    with ScopeTimer(r'All tasks', print_start=False, print_end=not args.worker) as timer:
        run(
            # named args:
            config_path=args.config,
            output_dir=args.output_dir,
            output_html=args.html,
            output_xml=args.xml,
            threads=args.threads,
            cleanup=not args.nocleanup,
            verbose=args.verbose,
            logger=True,  # stderr + stdout
            html_include=args.ppinclude,
            html_exclude=args.ppexclude,
            treat_warnings_as_errors=args.werror,
            theme=args.theme,
            copy_assets=not args.noassets,
            temp_dir=args.temp_dir,
            copy_config_to=args.copy_config_to,
            versions_in_navbar=args.versions_in_navbar,
            keep_original_xml=args.keep_original_xml,
            # kwargs:
            xml_v2=args.xml_v2,
        )


def main_blog_post(invoker=True):
    """
    The entry point when the library is invoked as `poxyblog`.
    """
    if invoker:
        _invoker(main_blog_post, invoker=False)
        return

    args = argparse.ArgumentParser(
        description=r'Initializes a new blog post for Poxy sites.', formatter_class=argparse.RawTextHelpFormatter
    )
    args.add_argument(r'title', type=str, help=r'the title of the new blog post')  #
    args.add_argument(r'-v', r'--verbose', action=r'store_true', help=r"enable very noisy diagnostic output")  #
    args.add_argument(r'--version', action=r'store_true', help=r"print the version and exit", dest=r'print_version')  #
    args = args.parse_args()

    if args.print_version:
        print(VERSION_STRING)
        return

    print(rf'{Fore.CYAN}{Style.BRIGHT}poxy{Style.RESET_ALL} v{VERSION_STRING}')

    date = datetime.datetime.now().date()

    title = args.title.strip()
    if not title:
        raise Error(r'title cannot be blank.')
    if re.search(r''''[\n\v\f\r]''', title) is not None:
        raise Error(r'title cannot contain newline characters.')
    file = re.sub(r'''[!@#$%^&*;:'"<>?/\\\s|+]+''', '_', title)
    file = rf'{date}_{file.lower()}.md'

    blog_dir = Path(r'blog')
    if blog_dir.exists() and not blog_dir.is_dir():
        raise Error(rf'{blog_dir.resolve()} already exists and is not a directory')
    blog_dir.mkdir(exist_ok=True)

    file = Path(blog_dir, file)
    if file.exists():
        if not file.is_file():
            raise Error(rf'{file.resolve()} already exist and is not a file')
        raise Error(rf'{file.resolve()} already exists')

    with open(file, r'w', encoding=r'utf-8', newline='\n') as f:
        write = lambda s='', end='\n': print(s, end=end, file=f)
        write(rf'# {title}')
        write()
        write()
        write()
        write()
        write()
        write(r'<!--[poxy_metadata[')
        write(rf'tags = []')
        write(r']]-->')
    print(rf'Blog post file initialized: {file.resolve()}')


if __name__ == '__main__':
    main()
