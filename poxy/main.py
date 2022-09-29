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
import shutil
from schema import SchemaError
from .utils import *
from .run import run
from . import dirs
from . import css
from . import emoji



def _invoker(func, **kwargs):
	try:
		func(**kwargs)
	except WarningTreatedAsError as err:
		print(rf'Error: {err} (warning treated as error)', file=sys.stderr)
		sys.exit(1)
	except SchemaError as err:
		print(err, file=sys.stderr)
		sys.exit(1)
	except Error as err:
		print(rf'Error: {err}', file=sys.stderr)
		sys.exit(1)
	except Exception as err:
		print_exception(err, include_type=True, include_traceback=True, skip_frames=1)
		sys.exit(-1)
	sys.exit(0)



def main(invoker=True):
	"""
	The entry point when the library is invoked as `poxy`.
	"""
	if invoker:
		_invoker(main, invoker=False)
		return

	args = argparse.ArgumentParser(
		description=r'Generate fancy C++ documentation.', formatter_class=argparse.RawTextHelpFormatter
	)
	#--------------------------------------------------------------
	# public user-facing arguments
	#--------------------------------------------------------------
	args.add_argument(
		r'config',
		type=Path,
		nargs='?',
		default=None,
		help=r'path to poxy.toml or a directory containing it (default: %(default)s)'
	)
	args.add_argument(
		r'-v',  #
		r'--verbose',
		action=r'store_true',
		help=r"enable very noisy diagnostic output"
	)
	args.add_argument(
		r'--doxygen',  #
		type=Path,
		default=None,
		metavar=r'<path>',
		help=r"specify the Doxygen executable to use (default: find on system path)"
	)
	args.add_argument(
		r'--dry',  #
		action=r'store_true',
		help=r"do a 'dry run' only, stopping after emitting the effective Doxyfile"
	)
	args.add_argument(
		r'--threads',  #
		type=int,
		default=0,
		metavar=r'N',
		help=r"set the number of threads to use (default: automatic)"
	)
	args.add_argument(
		r'--version',  #
		action=r'store_true',
		help=r"print the version and exit",
		dest=r'print_version'
	)
	args.add_argument(
		r'--werror',  #
		action=r'store_true',
		help=r"always treat warnings as errors regardless of config file settings"
	)
	args.add_argument(
		r'--xmlonly',  #
		action=r'store_true',
		help=r"stop after generating and preprocessing the Doxygen xml"
	)
	args.add_argument(
		r'--ppinclude',  #
		type=str,
		default=None,
		metavar=r'<regex>',
		help=r"pattern matching HTML file names to post-process (default: all)"
	)
	args.add_argument(
		r'--ppexclude',  #
		type=str,
		default=None,
		metavar=r'<regex>',
		help=r"pattern matching HTML file names to exclude from post-processing (default: none)"
	)
	args.add_argument(
		r'--nocleanup',  #
		action=r'store_true',
		help=r"does not clean up after itself, leaving the XML and other temp files intact"
	)
	args.add_argument(
		r'--theme',  #
		choices=[r'auto', r'light', r'dark', r'custom'],
		default=r'auto',
		help=r'the CSS theme to use (default: %(default)s)'
	)
	#--------------------------------------------------------------
	# hidden developer-only arguments
	#--------------------------------------------------------------
	args.add_argument(
		r'--update-styles',  #
		action=r'store_true',
		help=argparse.SUPPRESS
	)
	args.add_argument(
		r'--update-fonts',  #
		action=r'store_true',
		help=argparse.SUPPRESS
	)
	args.add_argument(
		r'--update-emoji',  #
		action=r'store_true',
		help=argparse.SUPPRESS
	)
	args.add_argument(
		r'--update-mcss',  #
		type=Path,
		default=None,
		metavar=r'<path>',
		help=argparse.SUPPRESS,
		dest=r'mcss'
	)
	args = args.parse_args()

	if args.print_version:
		print(r'.'.join([str(v) for v in lib_version()]))
		return

	if args.mcss is not None:
		args.update_styles = True
		args.update_fonts = True
		args.mcss = coerce_path(args.mcss).resolve()
		assert_existing_directory(args.mcss)
		assert_existing_file(Path(args.mcss, r'documentation/doxygen.py'))
		if dirs.MCSS == args.mcss:
			raise Exception(r'm.css source path may not be the same as the internal destination.')
		if dirs.MCSS.exists():
			delete_directory(dirs.MCSS, logger=True)
		print(rf'Updating bundled m.css from {args.mcss}')
		shutil.copytree(
			args.mcss,
			dirs.MCSS,
			symlinks=False,
			dirs_exist_ok=True,
			ignore=shutil.ignore_patterns(
			r'.git*',  #
			r'.editor*',
			r'.circleci*',
			r'.coverage*',
			r'.istanbul*',
			r'*.idx',
			r'*.pyc',
			r'*.compiled.css',
			r'__pycache__*',
			r'artwork*',
			r'circleci*',
			r'test_doxygen*',
			r'test_python*',
			r'pelican-theme*',
			r'pygments-*.py',
			r'postprocess.sh',
			r'postprocess.py',
			r'm-*dark.css',  # the m.css themes have local copies in data/ for *reasons*
			r'm-*light.css'
			)
		)
		for folder in (
			r'doc',  #
			r'documentation/test',
			r'documentation/templates/python',
			r'package',
			r'plugins/m/test',
			r'site',
		):
			delete_directory(Path(dirs.MCSS, folder), logger=True)
	assert_existing_directory(dirs.MCSS)
	assert_existing_file(Path(dirs.MCSS, r'documentation/doxygen.py'))

	if args.update_fonts:
		args.update_styles = True
	if args.update_styles:
		css.regenerate_builtin_styles(use_cached_fonts=not args.update_fonts)

	if args.update_emoji:
		emoji.update_database_file()

	if args.update_styles or args.update_emoji:
		return

	with ScopeTimer(r'All tasks', print_start=False, print_end=not args.dry) as timer:
		run(
			config_path=args.config,
			output_dir=Path.cwd(),
			threads=args.threads,
			cleanup=not args.nocleanup,
			verbose=args.verbose,
			doxygen_path=args.doxygen,
			logger=True,  # stderr + stdout
			dry_run=args.dry,
			xml_only=args.xmlonly,
			html_include=args.ppinclude,
			html_exclude=args.ppexclude,
			treat_warnings_as_errors=True if args.werror else None,
			theme=None if args.theme == r'auto' else args.theme
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
	args.add_argument(
		r'title',  #
		type=str,
		help=r'the title of the new blog post'
	)
	args.add_argument(
		r'-v',  #
		r'--verbose',
		action=r'store_true',
		help=r"enable very noisy diagnostic output"
	)
	args.add_argument(
		r'--version',  #
		action=r'store_true',
		help=r"print the version and exit",
		dest=r'print_version'
	)
	args = args.parse_args()

	if args.print_version:
		print(r'.'.join([str(v) for v in lib_version()]))
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
