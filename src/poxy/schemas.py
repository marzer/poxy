#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

import datetime

from schema import And, Optional, Or, Schema, SchemaError, Use

py2toml = {
    str: r'string',
    list: r'array',
    dict: r'table',
    int: r'integer',
    float: r'float',
    bool: r'boolean',
    datetime.date: r'date',
    datetime.time: r'time',
    datetime.datetime: r'date-time',
}


def FixedArrayOf(typ, length, name=''):
    global py2toml
    return And(
        [typ],
        lambda v: len(v) == length,
        error=rf'{name + ": " if name else ""}expected array of {length} {py2toml[typ]}{"s" if length != 1 else ""}',
    )


def ValueOrArray(typ, name='', length=None):
    global py2toml
    inner = None
    if length is None:
        inner = Or(typ, [typ], error=rf'{name + ": " if name else ""}expected {py2toml[typ]} or array of {py2toml[typ]}s')
    else:
        err = rf'{name + ": " if name else ""}expected {py2toml[typ]} or array of {length} {py2toml[typ]}{"s" if length != 1 else ""}'
        inner = And(Or(typ, [typ], error=err), lambda v: not isinstance(v, list) or len(v) == length, error=err)
    return And(inner, Use(lambda x: x if isinstance(x, list) else [x]))


def Stripped(typ, allow_empty=True, name=''):
    if not name:
        name = 'value'
    return And(
        And(typ, Use(lambda x: x.strip())),
        (lambda x: True) if allow_empty else (lambda x: len(x) > 0),
        error=rf'{name} cannot be blank',
    )


context_stack = list()


class SchemaContext(object):
    def __init__(self, val: str):
        self.__val = str(val) if val is not None else None

    def __enter__(self):
        global context_stack
        if self.__val:
            context_stack.append(self.__val)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.__val and exc_type is None:
            global context_stack
            context_stack.pop()


def current_schema_context() -> str:
    global context_stack
    ctx = ''
    for val in context_stack:
        ctx += rf'{val}: '
    return ctx


__all__ = [
    'And',
    'Optional',
    'Or',
    'Schema',
    'Use',
    'FixedArrayOf',
    'ValueOrArray',
    'Stripped',
    'SchemaContext',
    'current_schema_context',
    'SchemaError',
]
