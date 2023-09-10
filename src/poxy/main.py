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
import subprocess
import sys
import zipfile

from . import css, doxygen, emoji, graph, mcss, paths
from .run import run
from .schemas import SchemaError
from .utils import *
from .version import *


def _invoker(func, **kwargs):
    try:
        func(**kwargs)
    except WarningTreatedAsError as err:
        print(rf'Error: {err} (warning treated as error)', file=sys.stderr)
        sys.exit(1)
    except graph.GraphError as err:
        print_exception(err, include_type=True, include_traceback=True, skip_frames=1)
        sys.exit(1)
    except SchemaError as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    except Error as err:
        print(rf'Error: {err}', file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print('\n*************\n', file=sys.stderr)
        print_exception(err, include_type=True, include_traceback=True, skip_frames=1)
        print(
            '*************\n'
            '\nYou appear to have triggered an internal bug!'
            '\nPlease re-run poxy with --bug-report and file an issue at github.com/marzer/poxy/issues'
            '\nMany thanks!'
            '\n\n*************',
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(0)


def make_boolean_optional_arg(args, name, default, help='', **kwargs):
    if sys.version_info.minor >= 9:
        args.add_argument(rf'--{name}', default=default, help=help, action=argparse.BooleanOptionalAction, **kwargs)
    else:
        args.add_argument(rf'--{name}', action=r'store_true', help=help, **kwargs)
        args.add_argument(
            rf'--no-{name}',
            action=r'store_false',
            help=(help if help == argparse.SUPPRESS else None),
            dest=name,
            **kwargs,
        )
        args.set_defaults(**{name: default})


def bug_report():
    BUG_REPORT_STRIP_ARGS = (
        r'--bug-report',
        r'--bug-report-internal',
        r'-v',
        r'--verbose',
        r'--color',
        r'--no-color',
        r'--colour',
        r'--no-colour',
    )

    bug_report_args = [arg for arg in sys.argv[1:] if arg not in BUG_REPORT_STRIP_ARGS]
    bug_report_zip = (Path.cwd() / r'poxy_bug_report.zip').resolve()

    print(r'Preparing output paths')
    delete_directory(paths.BUG_REPORT_DIR)
    delete_file(bug_report_zip)
    os.makedirs(str(paths.BUG_REPORT_DIR), exist_ok=True)

    print(r'Invoking poxy')
    result = subprocess.run(
        args=[r'poxy', *bug_report_args, r'--bug-report-internal', r'--verbose'],
        cwd=str(Path.cwd()),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
    )

    if result.stdout is not None:
        print(r'Writing stdout')
        with open(paths.BUG_REPORT_DIR / r'stdout.txt', r'w', newline='\n', encoding=r'utf-8') as f:
            f.write(result.stdout)

    if result.stderr is not None:
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
        f'Zip generated: {bug_report_zip}\n'
        'Please attach this file when you make a report at github.com/marzer/poxy/issues, thanks!'
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
        r'''  _ __   _____  ___   _ ''' '\n'
        r''' | '_ \ / _ \ \/ / | | |''' '\n'
        r''' | |_) | (_) >  <| |_| |''' '\n'
        r''' | .__/ \___/_/\_\\__, |''' '\n'
        r''' | |               __/ |''' '\n'
        r''' |_|              |___/ ''' rf' v{VERSION_STRING} - github.com/marzer/poxy'
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
        default=Path('.'),
        help=r'path to poxy.toml or a directory containing it (default: %(default)s)',
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
        help=r"pattern matching HTML file names to exclude from post-processing (default: none)",
    )
    args.add_argument(
        r'--theme',  #
        choices=[r'light', r'dark', r'custom'],
        default=None,
        help=r'override the default visual theme (default: read from config)',
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
        args,
        r'werror',
        default=None,
        help=r'override the treating of warnings as errors (default: read from config)',  #
    )
    args.add_argument(
        r'--bug-report', action=r'store_true', help=r"captures all output in a zip file for easier bug reporting."  #
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
    args.add_argument(
        r'--update-mcss', type=Path, default=None, metavar=r'<path>', help=argparse.SUPPRESS, dest=r'mcss'
    )  #
    args.add_argument(  # --xml and --html are the replacements for --xmlonly
        r'--xmlonly', action=r'store_true', help=argparse.SUPPRESS  #
    )
    args.add_argument(r'--xml-v2', action=r'store_true', help=argparse.SUPPRESS)  #
    args.add_argument(r'--bug-report-internal', action=r'store_true', help=argparse.SUPPRESS)  #
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

    if args.mcss is not None:
        args.update_styles = True
        if args.update_fonts is None:
            args.update_fonts = True
        mcss.update_bundled_install(args.mcss)
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

    if args.update_styles or args.update_fonts or args.update_emoji or args.update_tests or args.mcss is not None:
        return

    # --------------------------------------------------------------
    # bug report invocation
    # --------------------------------------------------------------

    if args.bug_report:
        bug_report()
        return

    # --------------------------------------------------------------
    # regular invocation
    # --------------------------------------------------------------

    if args.xmlonly:
        args.html = False
        args.xml = True

    output_dir = Path.cwd()
    temp_dir = None
    if args.bug_report_internal:
        output_dir = paths.BUG_REPORT_DIR
        temp_dir = paths.BUG_REPORT_DIR / r'temp'
        args.nocleanup = True

    with ScopeTimer(r'All tasks', print_start=False, print_end=True) as timer:
        run(
            # named args:
            config_path=args.config,
            output_dir=output_dir,
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
            temp_dir=temp_dir,
            bug_report=bool(args.bug_report_internal),
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
