#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Structured config components parsed from poxy.toml (warnings, code blocks, input path sets) plus the
small config-parsing helpers. Extracted verbatim from project.py; consumed by project.Context.
"""

import copy

from .defaults import Defaults
from .schemas import *
from .utils import *


def extract_kvps(
    config,
    table,
    key_getter: typing.Callable = str,
    value_getter: typing.Callable = str,
    strip_keys=True,
    strip_values=True,
    allow_blank_keys=False,
    allow_blank_values=False,
    value_type=None,
):
    assert config is not None
    assert isinstance(config, dict)
    assert table is not None

    if table not in config:
        return {}

    out = {}
    for k, v in config[table].items():
        key = key_getter(k)
        if isinstance(key, str):
            if strip_keys:
                key = key.strip()
            if not allow_blank_keys and not key:
                raise Error(rf'{table}: keys cannot be blank')
        if key in out:
            raise Error(rf'{table}.{key}: cannot be specified more than once')

        value = value_getter(v)
        if isinstance(value, str):
            if strip_values and isinstance(value, str):
                value = value.strip()
            if not allow_blank_values and not value:
                raise Error(rf'{table}.{key}: values cannot be blank')

        if value_type is not None:
            value = value_type(value)

        out[key] = value

    return out


def assert_no_unexpected_keys(raw, validated, prefix=''):
    for key in raw:
        if key not in validated:
            raise Error(rf"Unknown config property '{prefix}{key}'")
        if isinstance(validated[key], dict):
            assert_no_unexpected_keys(raw[key], validated[key], prefix=rf'{prefix}{key}.')
    return validated


class Warnings:
    schema = {Optional(r'enabled'): bool, Optional(r'treat_as_errors'): bool, Optional(r'undocumented'): bool}

    def __init__(self, config):
        self.enabled = True
        self.treat_as_errors = False
        self.undocumented = False

        if config is None or 'warnings' not in config:
            return

        config = config['warnings']
        if r'enabled' in config:
            self.enabled = bool(config[r'enabled'])
        if r'treat_as_errors' in config:
            self.treat_as_errors = bool(config[r'treat_as_errors'])
        if r'undocumented' in config:
            self.undocumented = bool(config[r'undocumented'])


class Blog:
    schema = {
        Optional(r'enabled'): bool,
        Optional(r'dir'): Stripped(str, allow_empty=False, name=r'dir'),
        Optional(r'title'): Stripped(str, allow_empty=False, name=r'title'),
        Optional(r'id'): Stripped(str, allow_empty=False, name=r'id'),
        Optional(r'navbar'): bool,
        Optional(r'drafts'): bool,
        Optional(r'tags'): bool,
        Optional(r'feed'): bool,
        Optional(r'feed_limit'): int,
    }

    def __init__(self, config):
        self.enabled = True
        self.dir = r'blog'
        self.title = r'Blog'
        self.id = r'blog'
        self.navbar = True
        self.drafts = False
        self.tags = True
        self.feed = True
        self.feed_limit = 20

        if config is None or r'blog' not in config:
            return

        config = config[r'blog']
        for key in (r'enabled', r'navbar', r'drafts', r'tags', r'feed'):
            if key in config:
                setattr(self, key, bool(config[key]))
        for key in (r'dir', r'title', r'id'):
            if key in config:
                setattr(self, key, str(config[key]).strip())
        if r'feed_limit' in config:
            self.feed_limit = max(1, int(config[r'feed_limit']))


class PostBuild:
    # each [[post]] entry is a group of commands sharing options; a command is a string or an argv array
    _command = Or(
        Stripped(str, allow_empty=False, name=r'command'),  # pyright: ignore[reportArgumentType]
        [Stripped(str, allow_empty=False, name=r'command')],  # pyright: ignore[reportArgumentType]
    )
    # strict Schema so unknown per-entry keys are rejected (the outer schema ignores extras, and
    # assert_no_unexpected_keys doesn't recurse into list elements)
    _entry = Schema(
        {
            r'commands': [_command],
            Optional(r'shell'): bool,
            Optional(r'working_directory'): Or(r'output', r'config'),  # pyright: ignore[reportArgumentType]
            Optional(r'allow_failure'): bool,
            Optional(r'timeout'): Or(int, float),
        }
    )
    schema = [_entry]

    def __init__(self, config):
        # flattened to per-command dicts carrying the group's options (exactly one of raw/argv set)
        self.commands = []

        if config is None or r'post' not in config:
            return

        for entry in config[r'post']:
            shell = bool(entry.get(r'shell', False))
            working_directory = str(entry.get(r'working_directory', r'output'))
            allow_failure = bool(entry.get(r'allow_failure', False))
            timeout = entry.get(r'timeout', None)
            timeout = float(timeout) if timeout is not None else None
            for spec in entry[r'commands']:
                if isinstance(spec, list):
                    raw = None
                    argv = [str(s).strip() for s in spec if str(s).strip()]
                    if not argv:
                        continue
                else:
                    raw = str(spec).strip()
                    argv = None
                    if not raw:
                        continue
                self.commands.append(
                    dict(
                        raw=raw,
                        argv=argv,
                        shell=shell,
                        working_directory=working_directory,
                        allow_failure=allow_failure,
                        timeout=timeout,
                    )
                )


class CodeBlocks:
    schema = {
        Optional(r'types'): ValueOrArray(str, name=r'types'),
        Optional(r'macros'): ValueOrArray(str, name=r'macros'),
        Optional(r'string_literals'): ValueOrArray(str, name=r'string_literals'),  # deprecated
        Optional(r'numeric_literals'): ValueOrArray(str, name=r'numeric_literals'),  # deprecated
        Optional(r'enums'): ValueOrArray(str, name=r'enums'),
        Optional(r'namespaces'): ValueOrArray(str, name=r'namespaces'),
        Optional(r'functions'): ValueOrArray(str, name=r'functions'),
    }

    def __init__(self, config, macros):
        self.types = copy.deepcopy(Defaults.cb_types)
        self.macros = copy.deepcopy(Defaults.cb_macros)
        self.enums = copy.deepcopy(Defaults.cb_enums)
        self.namespaces = copy.deepcopy(Defaults.cb_namespaces)
        self.functions = copy.deepcopy(Defaults.cb_functions)

        if r'code_blocks' in config:
            config = config['code_blocks']

            if 'types' in config:
                for t in typing.cast(typing.Iterable[str], coerce_collection(config['types'])):
                    type_ = t.strip()
                    if type_:
                        self.types.add(type_)

            if 'macros' in config:
                for m in typing.cast(typing.Iterable[str], coerce_collection(config['macros'])):
                    macro = m.strip()
                    if macro:
                        self.macros.add(macro)

            if 'enums' in config:
                for e in typing.cast(typing.Iterable[str], coerce_collection(config['enums'])):
                    enum = e.strip()
                    if enum:
                        self.enums.add(enum)

            if 'namespaces' in config:
                for ns in typing.cast(typing.Iterable[str], coerce_collection(config['namespaces'])):
                    namespace = ns.strip()
                    if namespace:
                        self.namespaces.add(namespace)

            if 'functions' in config:
                for f in typing.cast(typing.Iterable[str], coerce_collection(config['functions'])):
                    function = f.strip()
                    if function:
                        self.functions.add(function)

        for k, v in macros.items():
            define = k
            bracket = define.find('(')
            if bracket != -1:
                define = define[:bracket].strip()
            if define:
                self.macros.add(define)


class Inputs:
    schema = {
        Optional(r'paths'): ValueOrArray(str, name=r'paths'),
        Optional(r'recursive_paths'): ValueOrArray(str, name=r'recursive_paths'),
        Optional(r'ignore'): ValueOrArray(str, name=r'ignore'),
    }

    def __init__(self, config, key, input_dir, additional_inputs=None, additional_recursive_inputs=None):
        self.paths = []

        if key in config:
            config = config[key]
        else:
            config = None

        all_paths = set()
        for recursive in (False, True):
            key = r'recursive_paths' if recursive else r'paths'
            paths = []
            if not recursive and additional_inputs is not None:
                paths = paths + [p for p in coerce_collection(additional_inputs) if p is not None]
            if recursive and additional_recursive_inputs is not None:
                paths = paths + [p for p in coerce_collection(additional_recursive_inputs) if p is not None]
            if config is not None and key in config:
                paths = paths + [p for p in coerce_collection(config[key]) if p is not None]
            paths = [p for p in paths if p]
            paths = [str(p).strip().replace('\\', '/') for p in paths]
            paths = [Path(p) for p in paths if p]
            paths = [Path(input_dir, p) if not p.is_absolute() else p for p in paths]
            paths = [p.resolve() for p in paths]
            for path in paths:
                if not path.exists():
                    raise Error(rf"{key}: '{path}' does not exist")
                if not (path.is_file() or path.is_dir()):
                    raise Error(rf"{key}: '{path}' was not a directory or file")
                all_paths.add(path)
                if recursive and path.is_dir():
                    for subdir in enumerate_directories(
                        path, filter=lambda p: not p.name.startswith(r'.'), recursive=True
                    ):
                        all_paths.add(subdir)

        ignores = set()
        if config is not None and r'ignore' in config:
            for s in typing.cast(typing.Iterable[str], coerce_collection(config[r'ignore'])):
                s = s.strip()
                if s:
                    ignores.add(s)
        ignore_patterns = [re.compile(i) for i in ignores]
        for ignore in ignore_patterns:
            all_paths = [p for p in all_paths if not ignore.search(str(p))]

        self.paths = list(all_paths)
        self.paths.sort()


class FilteredInputs(Inputs):
    schema = combine_dicts(Inputs.schema, {Optional(r'patterns'): ValueOrArray(str, name=r'patterns')})

    def __init__(self, config, key, input_dir, additional_inputs=None, additional_recursive_inputs=None):
        super().__init__(
            config,
            key,
            input_dir,
            additional_inputs=additional_inputs,
            additional_recursive_inputs=additional_recursive_inputs,
        )
        self.patterns = None

        if key not in config:
            return
        config = config[key]

        if r'patterns' in config:
            self.patterns = set()
            for v in typing.cast(typing.Iterable[str], coerce_collection(config[r'patterns'])):
                val = v.strip()
                if val:
                    self.patterns.add(val)


class Sources(FilteredInputs):
    schema = combine_dicts(
        FilteredInputs.schema,
        {
            Optional(r'strip_paths'): ValueOrArray(str, name=r'strip_paths'),
            Optional(r'strip_includes'): ValueOrArray(str, name=r'strip_includes'),
            Optional(r'extract_all'): bool,
        },
    )

    def __init__(
        self,
        config,
        key,
        input_dir,
        additional_inputs=None,
        additional_recursive_inputs=None,
        additional_strip_paths=None,
    ):
        super().__init__(
            config,
            key,
            input_dir,
            additional_inputs=additional_inputs,
            additional_recursive_inputs=additional_recursive_inputs,
        )

        self.strip_paths = []
        self.strip_includes = []
        self.extract_all = False
        if self.patterns is None:
            self.patterns = copy.deepcopy(Defaults.source_patterns)

        # not an early-out: additional_strip_paths must still apply when the config has no [sources] table
        config = config[key] if key in config else {}

        strip_path_sources = (
            coerce_collection(config[r'strip_paths']) if r'strip_paths' in config else None,
            coerce_collection(additional_strip_paths) if additional_strip_paths is not None else None,
        )
        for sps in strip_path_sources:
            if sps is None:
                continue
            for s in sps:
                if s is None:
                    continue
                path = str(s).strip()
                if path:
                    self.strip_paths.append(path)

        if r'strip_includes' in config:
            for s in typing.cast(typing.Iterable[str], coerce_collection(config[r'strip_includes'])):
                path = s.strip().replace('\\', '/')
                if path:
                    self.strip_includes.append(path)
            self.strip_includes.sort(key=lambda v: len(v), reverse=True)

        if r'extract_all' in config:
            self.extract_all = bool(config['extract_all'])
