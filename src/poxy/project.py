#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Everything relating to the 'project context' object that describes the project for which the documentation is being generated.
"""

import copy
import html
import os
import shutil
import sys

try:
    import pytomlpp as toml  # fast; based on toml++ (C++)  # pyright: ignore[reportMissingImports]
except ImportError:
    try:
        import tomllib as toml  # PEP 680
    except ImportError:
        import tomli as toml  # pyright: ignore[reportMissingImports]  # only installed on <3.11

import datetime
import itertools

from colorama import Fore, Style

from . import doxygen, emoji, paths, repos
from .config import (
    CodeBlocks,
    FilteredInputs,
    Inputs,
    PostBuild,
    Sources,
    Warnings,
    assert_no_unexpected_keys,
    extract_kvps,
)
from .defaults import Defaults
from .schemas import *
from .utils import *
from .version import *

# =======================================================================================================================
# project context
# =======================================================================================================================


class Context:
    """
    The context object passed around during one invocation.
    """

    __config_schema = Schema(
        {
            Optional(r'aliases'): {str: str},
            Optional(r'author'): Stripped(str),
            Optional(r'autolinks'): {str: str},
            Optional(r'badges'): {str: ValueOrArray(str, name=r'badges', length=2)},
            Optional(r'changelog'): Or(str, bool),
            Optional(r'main_page'): Or(str, bool),
            Optional(r'code_blocks'): CodeBlocks.schema,
            Optional(r'cpp'): Or(str, int, error=r'cpp: expected string or integer'),
            Optional(r'defines'): {str: Or(str, int, bool)},  # legacy
            Optional(r'description'): Stripped(str),
            Optional(r'examples'): FilteredInputs.schema,
            Optional(r'extra_files'): ValueOrArray(str, name=r'extra_files'),
            Optional(r'excluded_symbols'): ValueOrArray(str, name=r'excluded_symbols'),
            Optional(r'favicon'): Stripped(str),
            Optional(r'generate_tagfile'): bool,
            Optional(r'github'): Stripped(str),
            Optional(r'gitlab'): Stripped(str),
            Optional(r'twitter'): Stripped(str),
            Optional(r'sponsor'): Stripped(str),
            Optional(r'html_header'): Stripped(str),
            Optional(r'images'): Inputs.schema,
            Optional(r'implementation_headers'): {str: ValueOrArray(str)},
            Optional(r'inline_namespaces'): ValueOrArray(str, name=r'inline_namespaces'),
            Optional(r'internal_docs'): bool,
            Optional(r'jquery'): bool,
            Optional(r'license'): ValueOrArray(str, length=2, name=r'license'),
            Optional(r'logo'): Stripped(str),
            Optional(r'macros'): {str: Or(str, int, bool)},
            Optional(r'meta_tags'): {str: Or(str, int)},
            Optional(r'name'): Stripped(str),
            Optional(r'navbar'): ValueOrArray(str, name=r'navbar'),
            Optional(r'pages'): {
                str: {
                    Optional(r'title'): Stripped(str),
                    Optional(r'content'): Stripped(str),
                    Optional(r'url'): Stripped(str),
                    Optional(r'navbar'): bool,
                    Optional(r'required'): bool,
                    Optional(r'layout'): Or(r'full', r'inline'),  # pyright: ignore[reportArgumentType]
                    Optional(r'height'): Stripped(str),
                }
            },
            Optional(r'post'): PostBuild.schema,
            Optional(r'private_repo'): bool,
            Optional(r'robots'): bool,
            Optional(r'scripts'): ValueOrArray(str, name=r'scripts'),
            Optional(r'show_includes'): bool,
            Optional(r'sources'): Sources.schema,
            Optional(r'stylesheets'): ValueOrArray(str, name=r'stylesheets'),
            Optional(r'tagfiles'): {str: str},
            Optional(r'theme'): Or(r'dark', r'light', r'custom'),  # pyright: ignore[reportArgumentType]
            Optional(r'warnings'): Warnings.schema,
            Optional(r'dot'): bool,
        },
        ignore_extra_keys=True,
    )
    __namespace_qualified = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*::.+$")

    def is_verbose(self):
        return self.__verbose

    def __log(self, level, msg, indent=None):
        if msg is None:
            return
        msg = str(msg).strip('\r\n\v\f')
        if not msg:
            return
        if indent is not None:
            indent = str(indent)
        if indent:
            with io.StringIO() as buf:
                for line in msg.splitlines():
                    print(rf'{indent}{line}', file=buf, end='\n')
                log(self.logger, buf.getvalue(), level=level)
        else:
            log(self.logger, msg, level=level)

    def verbose(self, msg, indent=None):
        if self.__verbose:
            self.__log(logging.DEBUG, msg, indent=indent)

    def info(self, msg, indent=None):
        self.__log(logging.INFO, msg, indent=indent)

    def warning(self, msg, indent=None, fatal=True):
        # fatal=False suppresses --werror escalation, for warnings about deliberately-optional conditions
        if fatal and self.warnings.treat_as_errors:
            raise WarningTreatedAsError(msg)
        else:
            self.__log(logging.WARNING, rf'{Style.BRIGHT}{Fore.YELLOW}warning:{Style.RESET_ALL} {msg}', indent=indent)

    def verbose_value(self, name, val):
        if not self.__verbose:
            return
        with io.StringIO() as buf:
            print(rf'{name + ": ":<35}', file=buf, end='')
            if val is not None:
                if isinstance(val, dict):
                    if val:
                        rpad = 0
                        for k in val:
                            rpad = max(rpad, len(str(k)))
                        first = True
                        for k, v in val.items():
                            if not first:
                                print(f'\n{" ":<35}', file=buf, end='')
                            first = False
                            print(rf'{str(k):<{rpad}} => {v}', file=buf, end='')
                elif is_collection(val):
                    if val:
                        first = True
                        for v in val:
                            if not first:
                                print(f'\n{" ":<35}', file=buf, end='')
                            first = False
                            print(v, file=buf, end='')
                else:
                    print(val, file=buf, end='')
            self.verbose(buf.getvalue())

    def verbose_object(self, name, obj):
        if not self.__verbose:
            return
        if isinstance(obj, (tuple, list, dict)):
            self.verbose_value(name, obj)
        else:
            for k, v in obj.__dict__.items():
                self.verbose_value(rf'{name}.{k}', v)

    def __init__(
        self,  #
        config_path: typing.Optional[Path],
        output_dir: typing.Union[Path, str],
        output_html: bool,
        output_xml: bool,
        threads: int,
        cleanup: bool,
        verbose: bool,
        logger,
        html_include: typing.Optional[str],
        html_exclude: typing.Optional[str],
        treat_warnings_as_errors: typing.Optional[bool],
        theme: typing.Optional[str],
        copy_assets: bool,
        temp_dir: typing.Optional[Path] = None,
        copy_config_to: typing.Optional[Path] = None,
        versions_in_navbar: bool = False,
        reset_output: bool = True,
        **kwargs,
    ):
        self.logger = logger
        self.__verbose = bool(verbose)
        self.output_html = bool(output_html)
        self.output_xml = bool(output_xml)
        self.cleanup = bool(cleanup)
        self.copy_assets = bool(copy_assets)
        self.verbose_logger = logger if self.__verbose else None
        self.versions_in_navbar = bool(versions_in_navbar)

        self.verbose_value(r'Context.output_html', self.output_html)
        self.verbose_value(r'Context.output_xml', self.output_xml)
        self.verbose_value(r'Context.cleanup', self.cleanup)

        threads = int(threads) if threads is not None else 0
        if threads <= 0:
            threads = typing.cast(int, os.cpu_count())
        self.threads = max(1, min(typing.cast(int, os.cpu_count()), threads))
        self.verbose_value(r'Context.threads', self.threads)

        # additional kwargs (experimental stuff etc)
        self.xml_v2 = bool(kwargs[r'xml_v2']) if r'xml_v2' in kwargs else False
        self.verbose_value(r'Context.xml_v2', self.xml_v2)

        # these are overridden/initialized elsewhere; they're here so duck-typing still quacks
        self.fixers: typing.Sequence = []
        self.compounds: dict = dict()
        self.compound_pages = dict()
        self.compound_kinds = set()
        self.has_macros = False

        # initial warning state; overwritten after the config is read.
        # set here first so 'treat_as_errors' behaves correctly for any pre-config warnings
        self.warnings = Warnings(None)
        if treat_warnings_as_errors is not None:
            self.warnings.treat_as_errors = bool(treat_warnings_as_errors)

        self.html_include = re.compile(str(html_include)) if html_include is not None else None
        self.html_exclude = re.compile(str(html_exclude)) if html_exclude is not None else None

        if sys.version_info >= (3, 11):
            self.now = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
        else:
            self.now = datetime.datetime.utcnow().replace(microsecond=0, tzinfo=datetime.timezone.utc)

        self.verbose_value(r'dirs.PACKAGE', paths.PACKAGE)
        self.verbose_value(r'dirs.CSS', paths.CSS)
        self.verbose_value(r'dirs.GENERATED', paths.GENERATED)
        self.verbose_value(r'dirs.FONTS', paths.FONTS)
        self.verbose_value(r'dirs.IMG', paths.IMG)
        self.verbose_value(r'dirs.JS', paths.JS)
        self.verbose_value(r'dirs.MCSS', paths.MCSS)
        self.verbose_value(r'dirs.TEMP', paths.TEMP)
        self.verbose_value(r'doxygen.path()', doxygen.path())

        # resolve paths
        if 1:
            # output
            if output_dir is None:
                output_dir = Path.cwd()
            self.output_dir = coerce_path(output_dir).resolve()
            self.verbose_value(r'Context.output_dir', self.output_dir)
            assert self.output_dir.is_absolute()

            # config path
            self.config_path = Path(r'poxy.toml').resolve()
            if config_path is not None:
                self.config_path = coerce_path(config_path).resolve()
                if self.config_path.is_dir():
                    for candidate in (r'poxy.toml', r'docs/poxy.toml', r'doc/poxy.toml', r'doxygen/poxy.toml'):
                        candidate_path = self.config_path / candidate
                        if candidate_path and candidate_path.is_file():
                            self.config_path = candidate_path
                            break
                if not self.config_path.is_file():
                    raise Error(rf"Config '{self.config_path}' did not exist or was not a file")
            if copy_config_to is not None and self.config_path.is_file():
                copy_file(self.config_path, copy_config_to)
            assert self.config_path.is_absolute()
            self.verbose_value(r'Context.config_path', self.config_path)

            # input dir
            self.input_dir = self.config_path.parent
            self.verbose_value(r'Context.input_dir', self.input_dir)
            assert_existing_directory(self.input_dir)
            assert self.input_dir.is_absolute()

            # root temp dir for this run
            if temp_dir is not None:
                self.temp_dir = Path(temp_dir).absolute()
            else:
                self.temp_dir = paths.TEMP / 'contexts' / temp_dir_name_for(self.input_dir)
            self.verbose_value(r'Context.temp_dir', self.temp_dir)
            assert self.temp_dir.is_absolute()

            # temp pages dir
            self.temp_pages_dir = Path(self.temp_dir, r'pages')
            self.verbose_value(r'Context.pages_dir', self.temp_pages_dir)
            assert self.temp_pages_dir.is_absolute()

            # temp xml output path used by doxygen
            self.temp_xml_dir = Path(self.temp_dir, r'xml')
            self.temp_original_xml_dir = Path(self.temp_dir, r'xml_original')
            self.verbose_value(r'Context.temp_xml_dir', self.temp_xml_dir)
            self.verbose_value(r'Context.temp_original_xml_dir', self.temp_original_xml_dir)
            assert self.temp_xml_dir.is_absolute()
            assert self.temp_original_xml_dir.is_absolute()

            # xml output path (--xml)
            self.xml_dir = Path(self.output_dir, r'xml')
            self.verbose_value(r'Context.xml_dir', self.xml_dir)
            assert self.xml_dir.is_absolute()

            # html output path (--html)
            self.html_dir = Path(self.output_dir, r'html')
            self.verbose_value(r'Context.html_dir', self.html_dir)
            assert self.html_dir.is_absolute()

            # assets subdir in html output
            self.assets_dir = Path(self.html_dir, r'poxy')
            self.verbose_value(r'Context.assets_dir', self.assets_dir)
            assert self.assets_dir.is_absolute()

            # blog dir
            self.blog_dir = Path(self.input_dir, r'blog')
            self.verbose_value(r'Context.blog_dir', self.blog_dir)
            assert self.blog_dir.is_absolute()

            # delete leftovers from previous run and initialize temp dirs
            delete_directory(self.temp_dir, logger=self.verbose_logger)
            # --post-build-only keeps existing output (it runs against it)
            if reset_output:
                delete_directory(self.xml_dir, logger=self.verbose_logger)
                delete_directory(self.html_dir, logger=self.verbose_logger)
            self.temp_dir.mkdir(exist_ok=True, parents=True)
            self.temp_pages_dir.mkdir(exist_ok=True, parents=True)

            # temp doxyfile path
            self.doxyfile_path = Path(self.temp_dir, rf'Doxyfile')
            self.verbose_value(r'Context.doxyfile_path', self.doxyfile_path)
            assert self.doxyfile_path.is_absolute()

            # temp m.css config path
            self.mcss_conf_path = Path(self.temp_dir, r'conf.py')
            self.verbose_value(r'Context.mcss_conf_path', self.mcss_conf_path)
            assert self.mcss_conf_path.is_absolute()

            # misc
            self.cppref_tagfile = coerce_path(paths.PACKAGE, r'cppreference-doxygen-web.tag.xml').resolve()
            self.verbose_value(r'Context.cppref_tagfile', self.cppref_tagfile)
            assert_existing_file(self.cppref_tagfile)
            assert self.cppref_tagfile.is_absolute()

        # read + check config
        self.__read_config(theme, treat_warnings_as_errors)
        # init emoji db
        self.emoji = emoji.Database()

    def __read_config(self, theme, treat_warnings_as_errors):
        extra_files = []
        badges = []
        self.scripts = []
        self.stylesheets = []

        def add_internal_asset(p) -> str:
            nonlocal extra_files
            nonlocal self
            assert p is not None
            p = coerce_path(p)
            if self.copy_assets:
                if not p.is_absolute():
                    for dir in (paths.FONTS, paths.GENERATED, paths.JS, paths.IMG):
                        new_p = dir / p
                        if new_p.exists():
                            p = new_p
                            break
                assert_existing_file(p)
                extra_files.append((p, rf'poxy/{p.name}'))
            return rf'poxy/{p.name}'

        config = dict()
        if self.config_path.exists():
            assert_existing_file(self.config_path)
            config = toml.loads(read_all_text_from_file(self.config_path, logger=self.logger))
        config = assert_no_unexpected_keys(config, self.__config_schema.validate(config))

        self.warnings = Warnings(config)
        if treat_warnings_as_errors is not None:
            self.warnings.treat_as_errors = bool(treat_warnings_as_errors)
        self.verbose_value(r'Context.warnings', self.warnings)

        self.post_build = PostBuild(config)
        self.verbose_object(r'Context.post_build', self.post_build)

        # project name (PROJECT_NAME)
        self.name = ''
        if 'name' in config:
            self.name = config['name'].strip()
        self.verbose_value(r'Context.name', self.name)

        # project author
        self.author = ''
        if 'author' in config:
            self.author = config['author'].strip()
        self.verbose_value(r'Context.author', self.author)

        # project description (PROJECT_BRIEF)
        self.description = ''
        if 'description' in config:
            self.description = config['description'].strip()
        self.verbose_value(r'Context.description', self.description)

        # project license
        self.license = None
        if 'license' in config:
            config['license'] = coerce_collection(config['license'])
            spdx = config['license'][0].strip(" \t-._:")
            uri = config['license'][1].strip() if len(config['license']) == 2 else ''
            if spdx:
                self.license = {r'spdx': spdx, r'uri': uri}
            if self.license:
                badge = re.sub(r'(?:[.]0+)+$', '', spdx.lower())  # trailing .0, .0.0 etc
                badge = badge.strip(' \t-._:')  # leading + trailing junk
                badge = re.sub(r'[:;!@#$%^&*\\|/,.<>?`~\[\]{}()_+\-= \t]+', '_', badge)  # internal junk
                badge = Path(paths.IMG, rf'poxy-badge-license-{badge}.svg')
                self.verbose(rf"Finding badge SVG for license '{spdx}'...")
                if badge.exists():
                    self.verbose(rf'Badge file found at {badge}')
                    badges.append((spdx, add_internal_asset(badge), uri))
        self.verbose_value(r'Context.license', self.license)

        # project repo access level
        self.private_repo = False
        if 'private_repo' in config:
            self.private_repo = bool(config['private_repo'])

        # project repository (github, gitlab, etc)
        self.repo = None
        for TYPE in repos.TYPES:
            if TYPE.KEY not in config:
                continue
            self.verbose_value(rf'Context.{TYPE.KEY}', config[TYPE.KEY])
            try:
                self.repo = TYPE(config[TYPE.KEY])
            except Error as err:
                raise Error(rf'{TYPE.KEY}: {err}') from err
            self.verbose_value(rf'Context.repo', self.repo)
            if not self.private_repo and self.repo.release_badge_uri:
                badges.append((r'Releases', self.repo.release_badge_uri, self.repo.releases_uri))

        # twitter
        self.twitter = None
        if r'twitter' in config and config[r'twitter']:
            self.twitter = config[r'twitter']
        self.verbose_value(r'Context.twitter', self.twitter)

        # sponsor
        self.sponsorship_uri = None
        if r'sponsor' in config and config[r'sponsor']:
            self.sponsorship_uri = config[r'sponsor']
        self.verbose_value(r'Context.sponsorship_uri', self.twitter)

        # project C++ version
        # defaults to 'current' cpp year version based on (current year - 2)
        # 1998, 2003, *range(2011, 2300, 3)
        default_cpp_year = max(int(self.now.year) - 2, 2011)
        default_cpp_year = default_cpp_year - ((default_cpp_year - 2011) % 3)
        self.cpp = default_cpp_year
        if r'cpp' in config:
            self.cpp = str(config['cpp']).lstrip('0 \t').rstrip()
            if not self.cpp:
                self.cpp = default_cpp_year
            self.cpp = int(self.cpp)
            if self.cpp in (1998, 98):
                self.cpp = 1998
            else:
                if self.cpp > 2000:
                    self.cpp -= 2000
                if self.cpp in [3, *range(11, 300, 3)]:
                    self.cpp += 2000
                else:
                    raise Error(rf"cpp: '{config['cpp']}' is not a valid cpp standard version")
        self.verbose_value(r'Context.cpp', self.cpp)
        badge = rf'poxy-badge-c++{str(self.cpp)[2:]}.svg'
        badges.append(
            (rf'C++{str(self.cpp)[2:]}', rf'poxy/{badge}', r'https://en.cppreference.com/w/cpp/compiler_support')
        )
        add_internal_asset(badge)

        # project logo
        self.logo = None
        if r'logo' in config:
            if config['logo']:
                file = config['logo'].strip()
                if file:
                    file = Path(config['logo'])
                    if not file.is_absolute():
                        file = Path(self.input_dir, file)
                    self.logo = file.resolve()
        self.verbose_value(r'Context.logo', self.logo)

        # theme (HTML_EXTRA_STYLESHEETS, M_THEME_COLOR)
        self.theme = r'dark'
        if theme is not None:
            self.theme = theme
        elif r'theme' in config:
            self.theme = str(config[r'theme'])
        if self.theme != r'custom':
            self.stylesheets.append(add_internal_asset(paths.GENERATED / r'poxy.css'))
        self.verbose_value(r'Context.theme', self.theme)

        # stylesheets (HTML_EXTRA_STYLESHEETS)
        if r'stylesheets' in config:
            for f in typing.cast(typing.Iterable[str], coerce_collection(config[r'stylesheets'])):
                file = f.strip()
                if file:
                    if is_uri(file):
                        self.stylesheets.append(file)
                    else:
                        file = Path(file)
                        self.stylesheets.append(file.name)
                        extra_files.append(file)
        self.verbose_value(r'Context.stylesheets', self.stylesheets)

        # jquery
        if r'jquery' in config and config[r'jquery']:
            jquery = enumerate_files(paths.JS, any=r'jquery*.js')[0]
            if jquery is not None:
                self.scripts.append(add_internal_asset(jquery))

        # scripts
        self.scripts.append(add_internal_asset(paths.JS / r'poxy.js'))
        if r'scripts' in config:
            for f in typing.cast(typing.Iterable[str], coerce_collection(config[r'scripts'])):
                file = f.strip()
                if file:
                    if is_uri(file):
                        self.scripts.append(file)
                    else:
                        file = Path(file)
                        self.scripts.append(file.name)
                        extra_files.append(file)
        self.verbose_value(r'Context.scripts', self.scripts)

        self.__read_pages(config)
        self.__read_custom_pages(config)
        self.__read_inputs(config)
        # dot tool (HAVE_DOT)
        self.dot = bool(config['dot']) if 'dot' in config else None
        if self.dot is None or self.dot:
            dot_exe = shutil.which('dot')
            if dot_exe:
                self.info(rf'Found dot: {dot_exe}')
                self.dot = True
            elif self.dot:  # user explicitly requested it
                self.dot = False
                self.warning('dot: set to true, but no dot executable could be found on the PATH')

        self.__read_navbar(config)
        self.__read_misc_options(config)
        # favicon (M_FAVICON)
        self.favicon = None
        if 'favicon' in config:
            if config['favicon']:
                file = Path(config['favicon'])
                if not file.is_absolute():
                    file = Path(self.input_dir, file)
                self.favicon = file.resolve()
                extra_files.append(self.favicon)
        else:
            favicon = Path(self.input_dir, 'favicon.ico')
            if favicon.exists() and favicon.is_file():
                self.favicon = favicon
                extra_files.append(favicon)
        self.verbose_value(r'Context.favicon', self.favicon)

        # macros (PREDEFINED)
        self.macros = copy.deepcopy(Defaults.macros)
        for s in (r'defines', r'macros'):
            for k, v in extract_kvps(
                config,
                s,
                value_getter=lambda v: (r'true' if v else r'false') if isinstance(v, bool) else str(v),
                allow_blank_values=True,
            ).items():
                self.macros[k] = v
        non_cpp_def_macros = copy.deepcopy(self.macros)
        cpp_defs = dict()
        for ver in [1998, 2003, *range(2011, 2300, 3)]:
            if ver > self.cpp:
                break
            if ver not in Defaults.cpp_builtin_macros:
                continue
            for k, v in Defaults.cpp_builtin_macros[ver].items():
                cpp_defs[k] = v
        cpp_defs = [(k, v) for k, v in cpp_defs.items()]
        cpp_defs.sort(key=lambda kvp: kvp[0])
        for k, v in cpp_defs:
            self.macros[k] = v
        self.verbose_value(r'Context.macros', self.macros)

        # autolinks
        self.autolinks = [(k, v) for k, v in Defaults.autolinks.items()]
        if 'autolinks' in config:
            for pattern, u in config['autolinks'].items():
                uri = u.strip()
                if pattern.strip() and uri:
                    self.autolinks.append((pattern, uri))
        self.autolinks.sort(
            key=lambda v: (
                self.__namespace_qualified.fullmatch(v[0]) is None,
                v[0].find(r'std::') == -1,
                -len(v[0]),
                v[0],
            )
        )
        self.autolinks = tuple(self.autolinks)
        self.verbose_value(r'Context.autolinks', self.autolinks)

        # aliases (ALIASES)
        self.aliases = copy.deepcopy(Defaults.aliases)
        if 'aliases' in config:
            for k, v in config['aliases'].items():
                alias = k.strip()
                if not alias:
                    continue
                if alias in self.aliases:
                    raise Error(rf'aliases.{k}: cannot override a built-in alias')
                self.aliases[alias] = v
        self.verbose_value(r'Context.aliases', self.aliases)

        # badges for index.html banner
        user_badges = []
        if 'badges' in config:
            for k, v in config['badges'].items():
                text = k.strip()
                v = typing.cast(typing.Sequence[str], coerce_collection(v))
                image_uri = v[0].strip()
                anchor_uri = v[1].strip() if len(v) > 1 else r''
                if text and image_uri:
                    user_badges.append((text, image_uri, anchor_uri))
        user_badges.sort(key=lambda b: b[0])
        self.badges = tuple(badges + user_badges)
        self.verbose_value(r'Context.badges', self.badges)

        # user-specified extra_files (HTML_EXTRA_FILES)
        if r'extra_files' in config:
            for f in typing.cast(typing.Iterable[str], coerce_collection(config['extra_files'])):
                file = f.strip()
                if file:
                    extra_files.append(Path(file))

        # add all the 'icon' svgs as internal assets so they can be used by users if they wish
        for f in enumerate_files(paths.IMG, all='poxy-icon-*.svg', recursive=False):
            add_internal_asset(f)

        # finalize extra_files
        extra_files = remove_duplicates(extra_files)
        self.extra_files = {}
        for i in range(len(extra_files)):
            file = extra_files[i]
            if not isinstance(file, tuple):
                path = coerce_path(file)
                file = (path, path.name)
            else:
                assert len(file) == 2
                file = (coerce_path(file[0]), file[1])
            if not file[0].is_absolute():
                file = (Path(self.input_dir, file[0]).resolve(), file[1])
            if not file[0].exists() or not file[0].is_file():
                raise Error(rf'extra_files: {file[0]} did not exist or was not a file')
            if file[1] in self.extra_files:
                raise Error(rf'extra_files: Multiple files with the name {file[1]}')
            self.extra_files[file[1]] = file[0]
        self.verbose_value(r'Context.extra_files', self.extra_files)

        # code_blocks
        self.code_blocks = CodeBlocks(config, non_cpp_def_macros)  # printed in run.py post-xml

        # html_header (HTML_HEADER in m.css)
        self.html_header = ''
        if r'html_header' in config:
            self.html_header = str(config[r'html_header']).strip()
        self.verbose_value(r'Context.html_header', self.html_header)

    def __read_pages(self, config):
        # enumerate blog files (need to add them to the doxygen sources)
        # entries start as plain paths then get replaced in-place with (path, date) tuples below
        self.blog_files: typing.List[typing.Any] = []
        if self.blog_dir.exists() and self.blog_dir.is_dir():
            self.blog_files = enumerate_files(self.blog_dir, any=(r'*.md', r'*.markdown'), recursive=True)
            sep = re.compile(r'[-֊‐‑‒–—―−_ ,;.]+')
            expr = re.compile(
                rf'^(?:blog{sep.pattern})?((?:[0-9]{{4}}){sep.pattern}(?:[0-9]{{2}}){sep.pattern}(?:[0-9]{{2}})){sep.pattern}[a-zA-Z0-9_ -]+$'
            )
            for i in range(len(self.blog_files)):
                f = self.blog_files[i]
                m = expr.fullmatch(f.stem)
                if not m:
                    raise Error(
                        rf"blog post filename '{f.name}' was not formatted correctly; "
                        + r"it should be of the form 'YYYY-MM-DD_this_is_a_post.md'."
                    )
                try:
                    d = datetime.datetime.strptime(sep.sub('-', m[1]), r'%Y-%m-%d').date()
                    self.blog_files[i] = (f, d)
                except Exception as exc:
                    raise Error(rf"failed to parse date from blog post filename '{f.name}': {str(exc)}") from exc
        self.verbose_value(r'Context.blog_files', self.blog_files)

        self.source_excludes = set()

        # changelog
        self.changelog = ''
        if r'changelog' in config:
            if isinstance(config['changelog'], bool):
                if config['changelog']:
                    candidate_names = (r'CHANGELOG', r'CHANGES', r'HISTORY')
                    candidate_extensions = (r'.md', r'.txt', r'')
                    as_lowercase = (False, True)
                    candidate_dir = self.input_dir
                    while True:
                        for name, ext, lower in itertools.product(candidate_names, candidate_extensions, as_lowercase):
                            candidate_file = Path(candidate_dir, rf'{name.lower() if lower else name}{ext}')
                            if (
                                candidate_file.exists()
                                and candidate_file.is_file()
                                and candidate_file.stat().st_size <= 1024 * 1024 * 2
                            ):
                                self.changelog = candidate_file
                                break
                        if self.changelog or candidate_dir.parent == candidate_dir or (candidate_dir / '.git').exists():
                            break
                        candidate_dir = candidate_dir.parent
                    if not self.changelog:
                        self.warning(
                            rf'changelog: Option was set to true but no file with a known changelog file name could be found! Consider using an explicit path.'
                        )

            else:
                self.changelog = coerce_path(config['changelog'])
                if not self.changelog.is_absolute():
                    self.changelog = Path(self.input_dir, self.changelog)
                if not self.changelog.exists() or not self.changelog.is_file():
                    raise Error(rf'changelog: {config["changelog"]} did not exist or was not a file')
        if self.changelog:
            self.source_excludes.add(self.changelog)
            temp_changelog_path = Path(self.temp_pages_dir, r'poxy_changelog.md')
            copy_file(self.changelog, temp_changelog_path, logger=self.verbose_logger)
            self.changelog = temp_changelog_path
        self.verbose_value(r'Context.changelog', self.changelog)

        # main_page (USE_MDFILE_AS_MAINPAGE)
        self.main_page = ''
        if r'main_page' in config:
            if isinstance(config['main_page'], bool):
                if config['main_page']:
                    candidate_names = (r'README', r'HOME', r'MAINPAGE', r'INDEX')
                    candidate_extensions = (r'.md', r'.txt', r'')
                    as_lowercase = (False, True)
                    candidate_dir = self.input_dir
                    while True:
                        for name, ext, lower in itertools.product(candidate_names, candidate_extensions, as_lowercase):
                            candidate_file = Path(candidate_dir, rf'{name.lower() if lower else name}{ext}')
                            if (
                                candidate_file.exists()
                                and candidate_file.is_file()
                                and candidate_file.stat().st_size <= 1024 * 1024 * 2
                            ):
                                self.main_page = candidate_file
                                break
                        if self.main_page or candidate_dir.parent == candidate_dir or (candidate_dir / '.git').exists():
                            break
                        candidate_dir = candidate_dir.parent
                    if not self.main_page:
                        self.warning(
                            rf'main_page: Option was set to true but no file with a known main_page file name could be found! Consider using an explicit path.'
                        )

            else:
                self.main_page = coerce_path(config['main_page'])
                if not self.main_page.is_absolute():
                    self.main_page = Path(self.input_dir, self.main_page)
                if not self.main_page.exists() or not self.main_page.is_file():
                    raise Error(rf'main_page: {config["main_page"]} did not exist or was not a file')
        if self.main_page:
            self.source_excludes.add(self.main_page)
            temp_main_page_path = Path(self.temp_pages_dir, r'poxy_main_page.md')
            copy_file(self.main_page, temp_main_page_path, logger=self.verbose_logger)
            self.main_page = temp_main_page_path
        self.verbose_value(r'Context.main_page', self.main_page)

    def __read_custom_pages(self, config):
        # custom iframe-hosting pages (config option 'pages'). each becomes a synthetic @page whose body
        # is an <iframe> embedding either a bundled local file/directory or an external url, rendered
        # inside the normal poxy chrome. content is bundled into html/<id>/ by run.py.
        self.custom_pages = []
        if r'pages' not in config or not isinstance(config[r'pages'], dict):
            return
        for key in config[r'pages']:
            page = config[r'pages'][key] or {}
            page_id = re.sub(r'[^a-zA-Z0-9_]+', r'_', str(key)).strip(r'_').lower()
            if not page_id:
                raise Error(rf'pages: invalid page name {key!r}')
            if re.match(r'^[0-9]', page_id):
                page_id = rf'page_{page_id}'
            title = str(page.get(r'title') or key).strip()
            content = str(page.get(r'content') or '').strip()
            url = str(page.get(r'url') or '').strip()
            if bool(content) == bool(url):
                raise Error(rf'pages.{key}: exactly one of "content" or "url" must be set')
            layout = str(page.get(r'layout') or r'full').strip()
            height = str(page.get(r'height') or '').strip()
            navbar = bool(page.get(r'navbar', True))
            required = bool(page.get(r'required', True))

            content_src = None
            if url:
                src = url
            else:
                content_src = coerce_path(content)
                if not content_src.is_absolute():
                    content_src = Path(self.input_dir, content_src)
                content_src = content_src.resolve()
                if not content_src.exists():
                    if required:
                        raise Error(rf'pages.{key}: content path {content!r} did not exist')
                    # optional page whose content is missing (e.g. a report not generated this build): skip it
                    self.warning(rf'pages.{key}: skipping, content path {content!r} does not exist', fatal=False)
                    continue
                src = rf'{page_id}/index.html' if content_src.is_dir() else rf'{page_id}/{content_src.name}'

            classes = rf'poxy-iframe poxy-iframe-{layout}'
            style = rf' style="height: {html.escape(height, quote=True)}"' if (layout == r'inline' and height) else ''
            iframe = (
                rf'<iframe class="{classes}" src="{html.escape(src, quote=True)}"'
                rf' title="{html.escape(title, quote=True)}"{style}></iframe>'
            )
            # emit a .dox (not .md) page: markdown pages get a version-dependent 'md_<file>' id prefix,
            # whereas '@page <id>' in a .dox reliably names the output <id>.html on every doxygen version
            dox = f'/** @page {page_id} {title}\n\n@htmlonly\n{iframe}\n@endhtmlonly\n*/\n'
            with open(
                Path(self.temp_pages_dir, rf'poxy_page_{page_id}.dox'), r'w', encoding=r'utf-8', newline='\n'
            ) as f:
                f.write(dox)

            self.custom_pages.append({r'id': page_id, r'title': title, r'navbar': navbar, r'content_src': content_src})
        self.verbose_value(r'Context.custom_pages', self.custom_pages)

    def __read_inputs(self, config):
        # sources (INPUT, FILE_PATTERNS, STRIP_FROM_PATH, STRIP_FROM_INC_PATH, EXTRACT_ALL)
        self.sources = Sources(
            config,
            r'sources',
            self.input_dir,
            additional_inputs=(
                self.temp_pages_dir,  #
                self.changelog if self.changelog else None,
                self.main_page if self.main_page else None,
                *[f for f, d in self.blog_files],
            ),
            additional_strip_paths=(self.temp_pages_dir,),
        )
        self.verbose_object(r'Context.sources', self.sources)

        # images (IMAGE_PATH)
        self.images = Inputs(
            config, r'images', self.input_dir, additional_recursive_inputs=[self.blog_dir if self.blog_files else None]
        )
        self.verbose_object(r'Context.images', self.images)

        # examples (EXAMPLES_PATH, EXAMPLE_PATTERNS)
        self.examples = FilteredInputs(
            config,
            r'examples',
            self.input_dir,
            additional_recursive_inputs=[self.blog_dir if self.blog_files else None],
        )
        self.verbose_object(r'Context.examples', self.examples)

        # tagfiles (TAGFILES)
        self.tagfiles: typing.Dict[typing.Union[Path, str], typing.Tuple[Path, str]] = {
            self.cppref_tagfile: (self.cppref_tagfile, r'http://en.cppreference.com/w/')
        }
        self.unresolved_tagfiles = False
        # blank values are allowed: a github:// source may omit its dest to auto-resolve the Pages URL
        for k, v in extract_kvps(config, 'tagfiles', allow_blank_values=True).items():
            source = str(k)
            dest = str(v)
            if not source:
                continue
            # a non-github source with a blank dest is still an error (it has no way to resolve one)
            if not dest and not is_github_uri(source):
                raise Error(rf'tagfiles.{source}: values cannot be blank')
            # github:// sources resolve via the authenticated API; an empty dest is allowed (the Pages URL
            # is auto-resolved during preprocess_tagfiles)
            if is_github_uri(source):
                file = Path(paths.TEMP, rf'tagfile_{sha1(source)}_{self.now.year}_{self.now.isocalendar()[1]}.xml')
                self.tagfiles[source] = (file, dest)
                self.unresolved_tagfiles = True
            elif source and dest:
                if is_uri(source):
                    file = Path(paths.TEMP, rf'tagfile_{sha1(source)}_{self.now.year}_{self.now.isocalendar()[1]}.xml')
                    self.tagfiles[source] = (file, dest)
                    self.unresolved_tagfiles = True
                else:
                    source = Path(source)
                    if not source.is_absolute():
                        source = Path(self.input_dir, source)
                    source = source.resolve()
                    self.tagfiles[str(source)] = (source, dest)
        for k, v in self.tagfiles.items():
            if isinstance(v, (Path, str)):
                assert_existing_file(k)
        self.verbose_value(r'Context.tagfiles', self.tagfiles)

    def __read_navbar(self, config):
        # navbar
        if 1:
            # initialize
            self.navbar = []
            if r'navbar' in config:
                for v in typing.cast(typing.Iterable[str], coerce_collection(config['navbar'])):
                    val = v.strip()
                    if val:
                        self.navbar.append(val)
            else:
                self.navbar = list(copy.deepcopy(Defaults.navbar))

            # expand 'default' and 'all'
            new_navbar = []
            for link in self.navbar:
                if link == r'all':
                    new_navbar += [*Defaults.navbar_all]
                elif link == r'default':
                    new_navbar += [*Defaults.navbar]
                else:
                    new_navbar.append(link)
            self.navbar = new_navbar

            # normalize aliases
            for i in range(len(self.navbar)):
                if self.navbar[i] == r'annotated':  # 'annotated' is doxygen-speak for 'classes'
                    self.navbar[i] = r'classes'
                elif self.navbar[i] == r'modules':  # 'modules' is doxygen-speak for 'groups'
                    self.navbar[i] = r'groups'
                elif self.navbar[i] == r'repository':
                    self.navbar[i] = r'repo'
                elif self.navbar[i] in (r'sponsorship', r'funding', r'fund'):
                    self.navbar[i] = r'sponsor'

            # custom pages with navbar=true (appended after the content links, before repo/theme)
            for page in getattr(self, r'custom_pages', []):
                if page[r'navbar']:
                    self.navbar.append(rf'<a href="{page["id"]}.html">{html.escape(page["title"])}</a>')

            # version switcher
            if self.versions_in_navbar and r'version' not in self.navbar:
                self.navbar.append(r'version')
            while not self.versions_in_navbar and r'version' in self.navbar:
                self.navbar.remove(r'version')

            # twitter
            if self.twitter and r'twitter' not in self.navbar:
                self.navbar.append(r'twitter')
            while not self.twitter and r'twitter' in self.navbar:
                self.navbar.remove(r'twitter')

            # repo logic
            if not self.repo:
                for KEY in (r'repo', *repos.KEYS):
                    while KEY in self.navbar:
                        self.navbar.remove(KEY)
            else:
                # remove repo buttons matching an uninstantiated repo type
                for TYPE in repos.TYPES:
                    if not isinstance(self.repo, TYPE) and TYPE.KEY in self.navbar:
                        self.navbar.remove(TYPE.KEY)
                # sub all remaining repo key aliases for simply 'repo'
                for i in range(len(self.navbar)):
                    if self.navbar[i] in repos.KEYS:
                        self.navbar[i] = r'repo'
                # add a repo button to the end if none was present
                if r'repo' not in self.navbar:
                    self.navbar.append(r'repo')

            # sponsor
            if self.sponsorship_uri and r'sponsor' not in self.navbar:
                self.navbar.append(r'sponsor')
            while not self.sponsorship_uri and r'sponsor' in self.navbar:
                self.navbar.remove(r'sponsor')

            # theme logic
            if self.theme != r'custom' and r'theme' not in self.navbar:
                self.navbar.append(r'theme')
            while self.theme == r'custom' and r'theme' in self.navbar:
                self.navbar.remove(r'theme')

            # remove duplicates (working right-to-left)
            self.navbar.reverse()
            self.navbar = remove_duplicates(self.navbar)
            self.navbar.reverse()
            self.navbar = tuple(self.navbar)

            self.verbose_value(r'Context.navbar', self.navbar)

    def __read_misc_options(self, config):
        # <meta> tags
        self.meta_tags = {}
        for k, v in extract_kvps(config, 'meta_tags', allow_blank_values=True).items():
            self.meta_tags[k] = v
        self.verbose_value(r'Context.meta_tags', self.meta_tags)

        # robots (<meta>)
        self.robots = True
        if 'robots' in config:
            self.robots = bool(config['robots'])
        self.verbose_value(r'Context.robots', self.robots)

        # inline namespaces for old versions of doxygen
        self.inline_namespaces = copy.deepcopy(Defaults.inline_namespaces)
        if 'inline_namespaces' in config:
            for ns in typing.cast(typing.Iterable[str], coerce_collection(config['inline_namespaces'])):
                namespace = ns.strip()
                if namespace:
                    self.inline_namespaces.add(namespace)
        self.verbose_value(r'Context.inline_namespaces', self.inline_namespaces)

        self.excluded_symbols = set()
        if 'excluded_symbols' in config:
            for symbol in typing.cast(typing.Iterable[str], coerce_collection(config['excluded_symbols'])):
                symbol = symbol.strip()
                if symbol:
                    self.excluded_symbols.add(symbol)

        # implementation headers
        self.implementation_headers = []
        if 'implementation_headers' in config:
            for k, v in config['implementation_headers'].items():
                # header
                header = k.strip().replace('\\', '/')
                if not header:
                    continue
                if header.find('*') != -1:
                    raise Error(rf"implementation_headers: target header path '{header}' may not have wildcards")
                # impls
                impls = typing.cast(typing.Iterable[str], coerce_collection(v))
                impls = [i.strip().replace('\\', '/') for i in impls]
                impls = [i for i in impls if i]
                impls = sorted(remove_duplicates(impls))
                if impls:
                    self.implementation_headers.append([header, impls])
        self.implementation_headers = tuple(self.implementation_headers)
        self.verbose_value(r'Context.implementation_headers', self.implementation_headers)

        # show_includes (SHOW_INCLUDES)
        self.show_includes = True
        if 'show_includes' in config:
            self.show_includes = bool(config['show_includes'])
        self.verbose_value(r'Context.show_includes', self.show_includes)

        # internal_docs (INTERNAL_DOCS)
        self.internal_docs = False
        if 'internal_docs' in config:
            self.internal_docs = bool(config['internal_docs'])
        self.verbose_value(r'Context.internal_docs', self.internal_docs)

        # generate_tagfile (GENERATE_TAGFILE)
        self.generate_tagfile = True
        self.tagfile_path = Path(
            self.temp_dir, rf'{self.name.replace(" ", "_")}.tagfile.xml' if self.name else r'tagfile.xml'
        )
        if r'generate_tagfile' in config:
            self.generate_tagfile = bool(config[r'generate_tagfile'])
        self.verbose_value(r'Context.generate_tagfile', self.generate_tagfile)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.cleanup:
            delete_directory(self.temp_dir, logger=self.verbose_logger)

    def __bool__(self):
        return True


__all__ = ['Context']
