#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and classes for working with Doxygen.
"""

import itertools
import os
import shutil
import subprocess

from lxml import etree

from . import graph, xml_utils
from .utils import *

# =======================================================================================================================
# functions
# =======================================================================================================================


def mangle_name(name):
    '''
    A lightweight version of doxygen's escapeCharsInString()
    (see https://github.com/doxygen/doxygen/blob/master/src/util.cpp)
    '''
    assert name is not None
    name = name.replace('_', '__')
    name = name.replace(':', '_1')
    name = name.replace('/', '_2')
    name = name.replace('<', '_3')
    name = name.replace('>', '_4')
    name = name.replace('*', '_5')
    name = name.replace('&', '_6')
    name = name.replace('|', '_7')
    name = name.replace('.', '_8')
    name = name.replace('!', '_9')
    name = name.replace(',', '_00')
    name = name.replace(' ', '_01')
    name = name.replace('{', '_02')
    name = name.replace('}', '_03')
    name = name.replace('?', '_04')
    name = name.replace('^', '_05')
    name = name.replace('%', '_06')
    name = name.replace('(', '_07')
    name = name.replace(')', '_08')
    name = name.replace('+', '_09')
    name = name.replace('=', '_0a')
    name = name.replace('$', '_0b')
    name = name.replace('\\', '_0c')
    name = name.replace('@', '_0d')
    name = name.replace(']', '_0e')
    name = name.replace('[', '_0f')
    name = name.replace('#', '_0g')
    name = re.sub(r'[A-Z]', lambda m: '_' + m[0].lower(), name)
    return name


def format_for_doxyfile(val):
    if val is None:
        return ''
    elif isinstance(val, str):
        return '"' + val.replace('"', '\\"') + '"'
    elif isinstance(val, Path):
        return format_for_doxyfile(str(val))
    elif isinstance(val, bool):
        return r'YES' if val else r'NO'
    elif isinstance(val, (int, float)):
        return str(val)
    else:
        assert False


def path() -> Path:
    if not hasattr(path, "val"):

        def test_path(p):
            if not p:
                return None
            p = Path(p)
            if not p.exists() or not p.is_file() or not os.access(str(p), os.X_OK):
                return None
            return p.resolve()

        doxygen = None
        for name in (r'doxygen.exe', r'doxygen'):
            doxygen = test_path(shutil.which(name))
            if doxygen is not None:
                break

        if doxygen is None:
            for p in (
                'C:\\Program Files\\doxygen\\bin\\doxygen.exe',  #
                'C:\\Program Files (x86)\\doxygen\\bin\\doxygen.exe',
                r'/usr/local/bin/doxygen',
            ):
                try:
                    doxygen = test_path(p)
                    if doxygen is not None:
                        break
                except:
                    pass

        if doxygen is None:
            raise Error(rf'Could not find Doxygen on system path')

        path.val = doxygen
    return path.val


def version() -> str:
    if not hasattr(version, "val"):
        proc = subprocess.run([str(path()), r'--version'], capture_output=True, encoding=r'utf-8', check=True)
        ret = proc.stdout.strip() if proc.stdout is not None else ''
        if not ret and proc.stderr.strip():
            raise Error(rf'doxygen exited with error: {proc.stderr.strip()}')
        version.val = ret
    return version.val


# =======================================================================================================================
# Doxyfile
# =======================================================================================================================


class Doxyfile(object):
    def __init__(self, input_path=None, output_path=None, cwd=None, logger=None, flush_at_exit=True):
        self.__logger = logger
        self.__dirty = True
        self.__text = ''
        self.__autoflush = bool(flush_at_exit)
        self.__cwd = Path.cwd() if cwd is None else coerce_path(cwd).resolve()
        assert_existing_directory(self.__cwd)

        # the input + output
        self.__input_path = input_path
        if self.__input_path is not None:
            self.__input_path = coerce_path(self.__input_path)
        self.__output_path = output_path
        if self.__output_path is not None:
            self.__output_path = coerce_path(self.__output_path)

        # read in doxyfile
        if self.__input_path is not None:
            if not self.__input_path.is_file():
                raise Error(rf'{self.__input_path} was not a file')
            self.__text = read_all_text_from_file(self.__input_path, logger=self.__logger).strip()
            self.cleanup()  # expands includes

        # ...or generate one
        else:
            result = subprocess.run(
                [str(path()), r'-s', r'-g', r'-'], check=True, capture_output=True, cwd=self.__cwd, encoding='utf-8'
            )
            self.__text = result.stdout.strip()

        # simplify regex searches by ensuring there's always leading and trailing newlines
        self.__text = f'\n{self.__text}\n'

    def cleanup(self):
        if not self.__dirty:
            return
        if 1:
            log(self.__logger, rf'Invoking doxygen to clean doxyfile')
            result = subprocess.run(
                [str(path()), r'-s', r'-u', r'-'],
                check=True,
                capture_output=True,
                cwd=self.__cwd,
                encoding=r'utf-8',
                input=self.__text,
            )
            self.__text = result.stdout.strip()
        self.__dirty = False

    def flush(self):
        self.cleanup()
        if self.__output_path is not None:
            log(self.__logger, rf'Writing {self.__output_path}')
            with open(self.__output_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(self.__text)

    def hash(self):
        return sha1(self.__text)

    def contains(self, text):
        assert text is not None
        return self.__text.find(text) != -1

    def get_value(self, key, fallback=None):
        pattern = re.compile(rf'\n\s*{key}\s*=(.*?)\n', flags=re.S)
        text = self.__text
        m = pattern.search(text)
        while m:
            # doxygen allows values to appear multiple times and only accepts the last one, hence the loop
            text = text[m.end() :]
            n = pattern.search(text)
            if not n:
                break
            m = n
        if m:
            val = m[1].strip(' "')
            return val if val else fallback
        return fallback

    def get_boolean(self, key, fallback=False):
        val = self.get_value(key)
        if val is None:
            return fallback
        return val.upper() == 'YES'

    def append(self, *args, end='\n', sep=' '):
        self.__text = rf'{self.__text}{sep.join(args)}{end}'
        self.__dirty = True
        return self

    def add_value(self, key, value=None):
        if value is not None:
            if isinstance(value, (list, tuple, set)):
                if value:
                    for v in value:
                        if v is not None:
                            self.append(rf'{key:<23}+= {format_for_doxyfile(v)}')
            else:
                self.append(rf'{key:<23}+= {format_for_doxyfile(value)}')
            self.__dirty = True
        return self

    def set_value(self, key, value=None):
        if value is not None and isinstance(value, (list, tuple, set)):
            if not value:
                self.append(rf'{key:<23}=')
            else:
                first = True
                for v in value:
                    if first:
                        self.append(rf'{key:<23}=  {format_for_doxyfile(v)}')
                    else:
                        self.add_value(key, v)
                    first = False
        else:
            self.append(rf'{key:<23}=  {format_for_doxyfile(value)}')
        self.__dirty = True
        return self

    def get_text(self):
        return self.__text

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if traceback is None and self.__autoflush:
            self.flush()


class Bool(object):
    def __init__(self, value: bool):
        self.__value = bool(value)

    def __str__(self) -> str:
        return r'yes' if self.__value else r'no'


class Prot(object):
    def __init__(self, value: graph.AccessLevel):
        self.__value = value

    def __str__(self) -> str:
        return self.__value.name.lower()


class Virt(object):
    def __init__(self, value: bool):
        self.__value = bool(value)

    def __str__(self) -> str:
        return r'virtual' if self.__value else r'non-virtual'


# =======================================================================================================================
# XML <=> Graph
# =======================================================================================================================

COMPOUNDS = {r'dir', r'file', r'group', r'page', r'class', r'struct', r'union', r'concept', r'namespace'}
KINDS = {*COMPOUNDS, r'typedef', r'enum', r'enumvalue', r'variable', r'function', r'define'}
KINDS_TO_NODE_TYPES = {
    r'dir': graph.Directory,
    r'file': graph.File,
    r'group': graph.Group,
    r'class': graph.Class,
    r'struct': graph.Struct,
    r'union': graph.Union,
    r'concept': graph.Concept,
    r'namespace': graph.Namespace,
    r'typedef': graph.Typedef,
    r'enum': graph.Enum,
    r'enumvalue': graph.EnumValue,
    r'variable': graph.Variable,
    r'function': graph.Function,
    r'define': graph.Define,
    r'page': graph.Page,
    r'friend': graph.Friend,
}
NODE_TYPES_TO_KINDS = {t: k for k, t in KINDS_TO_NODE_TYPES.items()}
COMPOUND_NODE_TYPES = {KINDS_TO_NODE_TYPES[c] for c in COMPOUNDS}
VERSION = r'1.9.5'


def _ordered(*types) -> list:
    assert types is not None
    assert types
    types = [*types]
    types.sort(key=lambda t: t.__name__)
    types = tuple(types)
    return types


def _parse_xml_file(g: graph.Graph, path: Path, log_func=None):
    assert g is not None
    assert path is not None

    root = xml_utils.read(path, logger=log_func)

    if root.tag not in (r'doxygenindex', r'doxygen'):
        return

    def extract_subelement_text(elem, subelem_tag: str):
        assert elem is not None
        assert subelem_tag is not None
        subelem = elem.find(subelem_tag)
        if subelem is not None:
            return subelem.text
        return None

    def extract_qualified_name(elem):
        assert elem is not None
        for tag in (r'qualifiedname', r'compoundname'):
            n = elem.find(tag)
            if n is not None:
                n = n.text.strip()
            if n:
                return n
        return None

    def parse_structured_text(node: graph.Node, elem):
        nonlocal g
        # top-level text in the tag
        if elem.text:
            text = g.get_or_create_node(type=graph.Text, parent=node)
            text.text = elem.text
        # child <tags>
        for child_elem in elem:
            if child_elem.tag == r'para':
                para = g.get_or_create_node(type=graph.Paragraph, parent=node)
                parse_structured_text(para, child_elem)
            elif child_elem.tag == r'ref':
                ref = g.get_or_create_node(type=graph.Reference, parent=node)
                ref.text = child_elem.text
                ref.kind = child_elem.get(r'kindref')
                resource = g.get_or_create_node(id=child_elem.get(r'refid'), parent=ref)
                if child_elem.get(r'external'):
                    resource.type = graph.ExternalResource
                    resource.file = child_elem.get(r'external')
            else:
                markup = g.get_or_create_node(type=graph.ExpositionMarkup, parent=node)
                markup.tag = child_elem.tag
                attrs = [(k, v) for k, v in child_elem.attrib.items()]
                attrs.sort(key=lambda kvp: kvp[0])
                markup.extra_attributes = tuple(attrs)
                parse_structured_text(markup, child_elem)
            # text that came after the child <tag>
            if child_elem.tail:
                text = g.get_or_create_node(type=graph.Text, parent=node)
                text.text = child_elem.tail

    def parse_text_subnode(node: graph.Node, subnode_type, elem, subelem_tag: str):
        assert node is not None
        assert elem is not None
        assert subelem_tag is not None
        assert subnode_type is not None
        if subnode_type in node:
            return
        subelem = elem.find(subelem_tag)
        if subelem is None:
            return
        nonlocal g
        subnode = g.get_or_create_node(type=subnode_type, parent=node)
        parse_structured_text(subnode, subelem)

    def parse_brief(node: graph.Node, elem):
        parse_text_subnode(node, graph.BriefDescription, elem, r'briefdescription')

    def parse_detail(node: graph.Node, elem):
        parse_text_subnode(node, graph.DetailedDescription, elem, r'detaileddescription')

    def parse_initializer(node: graph.Node, elem):
        parse_text_subnode(node, graph.Initializer, elem, r'initializer')

    def parse_type(node: graph.Node, elem, resolve_auto_as=None):
        assert node is not None
        assert elem is not None
        if graph.Type in node:
            return
        type_elem = elem.find(r'type')
        if type_elem is None:
            return
        # extract constexpr, constinit, static, mutable etc out of the type if doxygen has leaked it
        while type_elem.text:
            text = rf' {type_elem.text} '
            match = re.search(r'\s(?:(?:const(?:expr|init|eval)|static|mutable|explicit|virtual|inline|friend)\s)+', text)
            if match is None:
                break
            type_elem.text = (text[: match.start()] + r' ' + text[match.end() :]).strip()
            if match[0].find(r'constexpr') != -1:
                node.constexpr = True
            if match[0].find(r'constinit') != -1:
                node.constinit = True
            if match[0].find(r'consteval') != -1:
                node.consteval = True
            if match[0].find(r'static') != -1:
                node.static = True
            if match[0].find(r'mutable') != -1:
                node.mutable = True
            if match[0].find(r'explicit') != -1:
                node.explicit = True
            if match[0].find(r'virtual') != -1:
                node.virtual = True
            if match[0].find(r'inline') != -1:
                node.inline = True
        if type_elem.text == r'auto' and resolve_auto_as is not None:
            type_elem.text = resolve_auto_as
        parse_text_subnode(node, graph.Type, elem, r'type')

    def parse_location(node: graph.Node, elem):
        location = elem.find(r'location')
        if location is None:
            return
        node.file = location.get(r'file')
        try:
            node.line = location.get(r'line')
        except:
            pass
        node.column = location.get(r'column')
        attrs = []
        for k, v in location.attrib.items():
            if k not in (r'file', r'line', r'column'):
                attrs.append((k, v))
        attrs.sort(key=lambda kvp: kvp[0])
        node.extra_attributes = tuple(attrs)

    # <compound>
    # (these are doxygen's version of 'forward declarations', typically found in index.xml)
    for compound in root.findall(r'compound'):
        if not compound.get(r'kind'):
            raise Error(rf"Malformed XML: <compound> tag missing attribute 'kind'")
        if compound.get(r'kind') == r'friend':
            raise Error(rf"Malformed XML: <compound> tag attribute 'kind' had unexpected value 'friend'")

        node = g.get_or_create_node(id=compound.get(r'refid'), type=KINDS_TO_NODE_TYPES[compound.get(r'kind')])

        if node.type is graph.File:  # files use their local name?? doxygen is so fucking weird
            node.local_name = tail(extract_subelement_text(compound, r'name').strip().replace('\\', r'/').rstrip(r'/'), r'/')  #
        else:
            node.qualified_name = extract_subelement_text(compound, r'name')

        # <member>
        for member_elem in compound.findall(rf'member'):
            member_kind = member_elem.get(r'kind')
            if member_kind == r'enumvalue':
                continue
            member = g.get_or_create_node(id=member_elem.get(r'refid'), type=KINDS_TO_NODE_TYPES[member_kind], parent=node)
            name = extract_subelement_text(member_elem, r'name')
            if name:
                if member.type is graph.Define:
                    member.local_name = name
                    member.qualified_name = name
                elif node.type not in (graph.Directory, graph.File):
                    member.local_name = name
                    if node.qualified_name:
                        member.qualified_name = rf'{node.qualified_name}::{name}'

    # <compounddef>
    for compounddef in root.findall(r'compounddef'):
        if not compounddef.get(r'kind'):
            raise Error(rf"Malformed XML: <compounddef> tag missing attribute 'kind'")
        if compounddef.get(r'kind') == r'friend':
            raise Error(rf"Malformed XML: <compounddef> tag attribute 'kind' had unexpected value 'friend'")

        node = g.get_or_create_node(id=compounddef.get(r'id'), type=KINDS_TO_NODE_TYPES[compounddef.get(r'kind')])
        node.access_level = compounddef.get(r'prot')
        parse_brief(node, compounddef)
        parse_detail(node, compounddef)
        parse_initializer(node, compounddef)
        parse_location(node, compounddef)
        parse_type(node, compounddef)

        # qualified name
        qualified_name = extract_subelement_text(compounddef, r'qualifiedname')
        qualified_name = qualified_name.strip() if qualified_name is not None else r''
        if not qualified_name and node.type in (graph.Directory, graph.File):
            qualified_name = compounddef.find(r'location')
            qualified_name = qualified_name.get(r'file') if qualified_name is not None else r''
            qualified_name = qualified_name.rstrip(r'/')
        if not qualified_name:
            qualified_name = extract_qualified_name(compounddef)
        node.qualified_name = qualified_name

        # get all memberdefs in one flat list
        memberdefs = [compounddef]
        memberdefs += [s for s in compounddef.findall(r'sectiondef')]
        memberdefs = [s.findall(r'memberdef') for s in memberdefs]  # list of lists of memberdefs
        memberdefs = list(itertools.chain.from_iterable(memberdefs))  # list of memberdefs

        def get_memberdefs(kind: str):
            nonlocal memberdefs
            return [m for m in memberdefs if m.get(r'kind') == kind]

        # all <memberdefs>
        for elem in memberdefs:
            kind = elem.get(r'kind')
            member = g.get_or_create_node(id=elem.get(r'id'), type=KINDS_TO_NODE_TYPES[kind], parent=node)
            parse_brief(member, elem)
            parse_detail(member, elem)
            parse_initializer(member, elem)
            parse_location(member, elem)
            member.local_name = extract_subelement_text(elem, r'name')
            member.qualified_name = extract_qualified_name(elem)
            member.access_level = elem.get(r'prot')
            member.static = elem.get(r'static')
            member.const = elem.get(r'const')
            member.constexpr = elem.get(r'constexpr')
            member.consteval = elem.get(r'consteval')
            member.inline = elem.get(r'inline')
            member.explicit = elem.get(r'explicit')
            member.virtual = True if elem.get(r'virtual') == r'virtual' else None
            member.strong = elem.get(r'strong')
            member.definition = extract_subelement_text(elem, r'definition')

            # fix trailing return types in some situations (https://github.com/mosra/m.css/issues/94)
            trailing_return_type = None
            if kind == r'function':
                type_elem = elem.find(r'type')
                args_elem = elem.find(r'argsstring')
                if (type_elem is not None and type_elem.text) and (  #
                    args_elem is not None and args_elem.text and args_elem.text.find(r'decltype') == -1
                ):
                    match = re.search(r'^(.*?)\s*->\s*([a-zA-Z][a-zA-Z0-9_::*&<>\s]+?)\s*$', args_elem.text)
                    if match:
                        args_elem.text = str(match[1])
                        trailing_return_type = str(match[2]).strip()
                        trailing_return_type = re.sub(r'\s+', r' ', trailing_return_type)
                        trailing_return_type = re.sub(r'(::|[<>*&])\s+', r'\1', trailing_return_type)
                        trailing_return_type = re.sub(r'\s+(::|[<>*&])', r'\1', trailing_return_type)

            parse_type(member, elem, resolve_auto_as=trailing_return_type)

        # enums
        for elem in get_memberdefs(r'enum'):
            member = g.get_or_create_node(id=elem.get(r'id'), type=graph.Enum, parent=node)
            for value_elem in elem.findall(r'enumvalue'):
                value = g.get_or_create_node(id=value_elem.get(r'id'), type=graph.EnumValue, parent=member)
                value.access_level = value_elem.get(r'prot')
                value.local_name = extract_subelement_text(value_elem, r'name')
                parse_brief(value, value_elem)
                parse_detail(value, value_elem)
                parse_initializer(value, value_elem)
                parse_location(value, value_elem)

        # typedefs
        for elem in get_memberdefs(r'typedef'):
            member = g.get_or_create_node(id=elem.get(r'id'), type=graph.Typedef, parent=node)

        # vars
        for elem in get_memberdefs(r'variable'):
            member = g.get_or_create_node(id=elem.get(r'id'), type=graph.Variable, parent=node)

        # functions
        for elem in get_memberdefs(r'function'):
            member = g.get_or_create_node(id=elem.get(r'id'), type=graph.Function, parent=node)

        #

        # <inner(dir|file|class|namespace|page|group|concept)>
        for inner_suffix in (r'dir', r'file', r'class', r'namespace', r'page', r'group', r'concept'):
            for inner_elem in compounddef.findall(rf'inner{inner_suffix}'):
                inner = g.get_or_create_node(id=inner_elem.get(r'refid'), parent=node)
                if inner_suffix == r'class':
                    if inner.id.startswith(r'class'):
                        inner.type = graph.Class
                    elif inner.id.startswith(r'struct'):
                        inner.type = graph.Struct
                    elif inner.id.startswith(r'union'):
                        inner.type = graph.Union
                elif node.type in (graph.Class, graph.Struct, graph.Union) and inner_suffix == r'group':
                    inner.type = graph.MemberGroup
                else:
                    inner.type = KINDS_TO_NODE_TYPES[inner_suffix]
                if node.type is graph.Directory:
                    if inner.type is graph.Directory:
                        inner.qualified_name = inner_elem.text
                    else:
                        assert inner.type is graph.File
                        inner.qualified_name = rf'{node.qualified_name}/{inner_elem.text}'
                elif node.type in graph.CPP_TYPES and inner.type in graph.CPP_TYPES:
                    inner.qualified_name = inner_elem.text


def read_graph_from_xml(folder, log_func=None) -> graph.Graph:
    assert folder is not None
    folder = coerce_path(folder).resolve()
    g = graph.Graph()

    # parse files
    for path in get_all_files(folder, all=r"*.xml"):
        try:
            _parse_xml_file(g=g, path=path, log_func=log_func)
        except KeyError:
            raise
        except graph.GraphError as ex:
            raise graph.GraphError(rf'Parsing {path.name} failed: {ex}')
        except Exception as ex:
            raise Error(rf'Parsing {path.name} failed: {ex}')

    # deduce any missing qualified_names for C++ constructs
    again = True
    while again:
        again = False
        for namespace in g(graph.Namespace, graph.Class, graph.Struct, graph.Union, graph.Enum):
            if not namespace.qualified_name:
                continue
            for member in namespace(
                graph.Namespace,
                graph.Class,
                graph.Struct,
                graph.Union,
                graph.Variable,
                graph.Concept,
                graph.Enum,
                graph.EnumValue,
                graph.Function,
                graph.Typedef,
            ):
                if member.local_name and not member.qualified_name:
                    member.qualified_name = rf'{namespace.qualified_name}::{member.local_name}'
                    again = True

    # deduce any missing qualified_names for files and folders
    again = True
    while again:
        again = False
        for dir in g(graph.Directory):
            if not dir.qualified_name:
                continue
            for member in dir(graph.Directory, graph.File):
                if member.local_name and not member.qualified_name:
                    member.qualified_name = rf'{dir.qualified_name}/{member.local_name}'
                    again = True

    # add missing dir nodes + link file hierarchy
    for node in list(g(graph.Directory, graph.File)):
        sep = node.qualified_name.rstrip(r'/').rfind(r'/')
        if sep == -1:
            continue
        parent_path = node.qualified_name[:sep]
        if not parent_path:
            continue
        parent = None
        for dir in g(graph.Directory):
            if dir.qualified_name == parent_path:
                parent = dir
                break
        if parent is None:
            parent = g.get_or_create_node(type=graph.Directory)
        parent.qualified_name = parent_path
        parent.add(node)

    # resolve file links
    for node in g:
        if not node or node.type in (graph.Directory, graph.File, graph.ExternalResource) or not node.file:
            continue
        for file in g(graph.File):
            if file.qualified_name == node.file:
                file.add(node)

    g.validate()

    # replace doxygen's stupid nondeterministic IDs with something more robust
    id_remap = dict()

    def fix_ids(node: graph.Node) -> str:
        nonlocal id_remap
        assert node is not None
        assert node.type is not None

        # enum values are special - their ids always begin with the ID of their owning enum
        if node.type is graph.EnumValue:
            assert node.has_parent(graph.Enum)
            assert node.local_name
            parent = list(node(graph.Enum, parents=True))[0]
            id = re.sub(r'[/+!@#$%&*()+=.,{}<>;:?\[\]\^\-\\]+', r'_', node.local_name).rstrip(r'_')
            id = rf'{fix_ids(parent)}_{id}'
            id_remap[node.id] = id
            return id

        # if we don't have a qualified name then there's no meaningful transformation to do
        # we also don't transform functions because overloading makes them ambiguous (todo: handle functions)
        if not node.qualified_name or node.type is graph.Function:
            id_remap[node.id] = node.id
            return node.id

        id = re.sub(r'[/+!@#$%&*()+=.,{}<>;:?\[\]\^\-\\]+', r'_', node.qualified_name).rstrip(r'_')
        if len(id) > 128:
            id = sha1(id)
        id = rf'{node.type_name.lower()}_{id}'
        id_remap[node.id] = id
        return id

    # g = g.copy(id_transform=fix_ids)
    # g.validate()

    return g


def write_graph_to_xml(g: graph.Graph, folder: Path, log_func=None):
    assert folder is not None
    folder.mkdir(exist_ok=True, parents=True)

    def make_structured_text(elem, nodes):
        assert elem is not None
        assert nodes is not None

        # all the ones at the start that are just plain text get
        # concatenated and set as the main text of the root subelement
        if elem.text is None:
            elem.text = r''
        while nodes and nodes[0].type is graph.Text:
            elem.text = elem.text + nodes[0].text
            nodes.pop(0)

        # paragraphs/references/other exposition markup
        prev = None
        while nodes:
            if nodes[0].type is graph.Paragraph:
                para = xml_utils.make_child(elem, rf'para')
                para.text = nodes[0].text
                make_structured_text(
                    para, [n for n in nodes[0](graph.Paragraph, graph.Text, graph.Reference, graph.ExpositionMarkup)]
                )
                prev = para
            elif nodes[0].type is graph.ExpositionMarkup:
                assert nodes[0].tag
                markup = xml_utils.make_child(elem, nodes[0].tag)
                for k, v in nodes[0].extra_attributes:
                    markup.set(k, v)
                markup.text = nodes[0].text
                make_structured_text(
                    markup, [n for n in nodes[0](graph.Paragraph, graph.Text, graph.Reference, graph.ExpositionMarkup)]
                )
                prev = markup
            elif nodes[0].type is graph.Reference and nodes[0].is_parent:
                ref = xml_utils.make_child(elem, rf'ref', refid=nodes[0][0].id)
                ref.text = nodes[0].text
                if nodes[0].kind:
                    ref.set(r'kindref', nodes[0].kind)
                if nodes[0][0].type is graph.ExternalResource:
                    ref.set(r'external', nodes[0][0].file)
                prev = ref
            else:
                assert nodes[0].type in (graph.Text, graph.Reference)
                assert prev is not None
                if prev.tail is None:
                    prev.tail = r''
                prev.tail = prev.tail + nodes[0].text
            nodes.pop(0)

    def make_text_subnode(elem, subelem_tag: str, node: graph.Node, subnode_type):
        assert elem is not None
        assert subelem_tag is not None
        assert node is not None
        assert subnode_type is not None
        subelem = xml_utils.make_child(elem, subelem_tag)
        subelem.text = r''
        if subnode_type not in node:
            return
        text = [n for n in node(subnode_type)]  # list of BriefDescription
        text = [
            [i for i in n(graph.Paragraph, graph.Text, graph.Reference, graph.ExpositionMarkup)] for n in text
        ]  # list of lists
        text = list(itertools.chain.from_iterable(text))  # flattened list of Text/Paragraph/Reference
        if not text:
            return
        make_structured_text(subelem, text)

    def make_brief(elem, node: graph.Node):
        make_text_subnode(elem, r'briefdescription', node, graph.BriefDescription)

    def make_detail(elem, node: graph.Node):
        make_text_subnode(elem, r'detaileddescription', node, graph.DetailedDescription)

    def make_initializer(elem, node: graph.Node):
        make_text_subnode(elem, r'initializer', node, graph.Initializer)

    def make_type(elem, node: graph.Node):
        make_text_subnode(elem, r'type', node, graph.Type)

    def make_location(elem, node: graph.Node):
        subelem = None
        if node.type is graph.Directory:
            subelem = xml_utils.make_child(elem, rf'location', file=rf'{node.qualified_name}/')
        elif node.type is graph.File:
            subelem = xml_utils.make_child(elem, rf'location', file=rf'{node.qualified_name}')
        else:
            subelem = xml_utils.make_child(elem, rf'location', line=str(node.line), column=str(node.column))
            if node.file:
                subelem.set(r'file', node.file)
            else:
                files = [f for f in node(graph.File, parents=True)]
                if files and files[0].qualified_name:
                    subelem.set(r'file', files[0].qualified_name)
        for k, v in node.extra_attributes:
            subelem.set(k, v)

    # serialize the compound nodes
    for node in g(*COMPOUND_NODE_TYPES):
        if not node:
            continue
        assert node.qualified_name

        kind = NODE_TYPES_TO_KINDS[node.type]
        assert kind in COMPOUNDS

        path = Path(folder, rf'{node.id}.xml')
        root = etree.XML(
            rf'''<doxygen
						xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
						xsi:noNamespaceSchemaLocation="compound.xsd"
						version="{VERSION}"
						xml:lang="en-US">
					<!-- This file was created by Poxy - https://github.com/marzer/poxy -->
					<compounddef id="{node.id}" kind="{kind}" language="C++">
						<compoundname>{node.local_name if node.type is graph.File else node.qualified_name}</compoundname>
					</compounddef>
				</doxygen>''',
            xml_utils.DEFAULT_PARSER,
        )

        # create the root <compounddef>
        compounddef = root.find(r'compounddef')
        if node.type not in (graph.Namespace, graph.Directory, graph.File, graph.Concept):
            compounddef.set(r'prot', str(Prot(node.access_level)))

        # <includes>
        if node.type in (graph.Class, graph.Struct, graph.Union, graph.Concept):
            files = [f for f in g(graph.File) if (f and f is not node and node in f)]
            for f in files:
                assert f.local_name
                xml_utils.make_child(compounddef, rf'includes', local=r'no').text = f.local_name

        # create all the <sectiondefs>
        # (empty ones will be deleted at the end)
        sectiondefs = (
            # namespace/file sections:
            r'enum',
            r'typedef',
            r'var',
            r'func',
            # class/struct/union sections:
            r'public-type',
            r'protected-type',
            r'private-type',
            r'public-static-func',
            r'protected-static-func',
            r'private-static-func',
            r'public-func',
            r'protected-func',
            r'private-func',
            r'public-static-attrib',
            r'protected-static-attrib',
            r'private-static-attrib',
            r'public-attrib',
            r'protected-attrib',
            r'private-attrib',
            r'friend',
        )
        sectiondefs = {k: xml_utils.make_child(compounddef, r'sectiondef', kind=k) for k in sectiondefs}

        # enums
        enums = list(node(graph.Enum))
        enums.sort(key=lambda n: n.qualified_name)
        for member in enums:
            section = r'enum'
            if node.type in (graph.Class, graph.Struct, graph.Union):
                section = rf'{Prot(member.access_level)}-type'
            elem = xml_utils.make_child(
                sectiondefs[section],
                rf'memberdef',
                id=member.id,
                kind=r'enum',
                static=str(Bool(member.static)),
                strong=str(Bool(member.strong)),
                prot=str(Prot(member.access_level)),
            )
            make_type(elem, member)
            xml_utils.make_child(elem, r'name').text = member.local_name
            xml_utils.make_child(elem, r'qualifiedname').text = member.qualified_name
            for value in member(graph.EnumValue):
                value_elem = xml_utils.make_child(elem, rf'enumvalue', id=value.id, prot=str(Prot(value.access_level)))
                xml_utils.make_child(value_elem, r'name').text = value.local_name
                if graph.Initializer in value:
                    make_initializer(value_elem, value)
                make_brief(value_elem, value)
                make_detail(value_elem, value)
            make_brief(elem, member)
            make_detail(elem, member)
            xml_utils.make_child(elem, r'inbodydescription').text = r''  # todo
            make_location(elem, member)

        # typedefs
        typedefs = list(node(graph.Typedef))
        typedefs.sort(key=lambda n: n.qualified_name)
        for member in typedefs:
            section = r'typedef'
            if node.type in (graph.Class, graph.Struct, graph.Union):
                section = rf'{Prot(member.access_level)}-type'
            elem = xml_utils.make_child(
                sectiondefs[section],
                rf'memberdef',
                id=member.id,
                kind=r'typedef',
                static=str(Bool(member.static)),
                prot=str(Prot(member.access_level)),
            )
            make_type(elem, member)
            xml_utils.make_child(elem, r'definition').text = member.definition
            xml_utils.make_child(elem, r'argsstring')
            xml_utils.make_child(elem, r'name').text = member.local_name
            xml_utils.make_child(elem, r'qualifiedname').text = member.qualified_name
            make_brief(elem, member)
            make_detail(elem, member)
            xml_utils.make_child(elem, r'inbodydescription').text = r''  # todo
            make_location(elem, member)

        # variables
        variables = list(node(graph.Variable))
        if node.type in (graph.Class, graph.Struct, graph.Union):
            static_vars = [v for v in variables if v.static]
            static_vars.sort(key=lambda n: n.qualified_name)
            variables = static_vars + [v for v in variables if not v.static]
        else:
            variables.sort(key=lambda n: n.qualified_name)
        for member in variables:
            section = r'var'
            if node.type in (graph.Class, graph.Struct, graph.Union):
                section = rf'{Prot(member.access_level)}-{"static-" if member.static else ""}attrib'
            elem = xml_utils.make_child(
                sectiondefs[section],
                rf'memberdef',
                id=member.id,
                kind=r'variable',
                prot=str(Prot(member.access_level)),
                static=str(Bool(member.static)),
                constexpr=str(Bool(member.constexpr)),
                constinit=str(Bool(member.constinit)),
                mutable=str(Bool(member.strong)),
            )
            make_type(elem, member)
            xml_utils.make_child(elem, r'definition').text = member.definition
            xml_utils.make_child(elem, r'argsstring')
            xml_utils.make_child(elem, r'name').text = member.local_name
            xml_utils.make_child(elem, r'qualifiedname').text = member.qualified_name
            make_brief(elem, member)
            make_detail(elem, member)
            make_initializer(elem, member)
            xml_utils.make_child(elem, r'inbodydescription').text = r''  # todo
            make_location(elem, member)

        # functions
        functions = list(node(graph.Function))
        functions.sort(key=lambda n: n.qualified_name)
        for member in functions:
            section = r'func'
            if node.type in (graph.Class, graph.Struct, graph.Union):
                section = rf'{Prot(member.access_level)}-{"static-" if member.static else ""}func'
            elem = xml_utils.make_child(
                sectiondefs[section],
                rf'memberdef',
                id=member.id,
                kind=r'function',
                prot=str(Prot(member.access_level)),
                static=str(Bool(member.static)),
                const=str(Bool(member.const)),
                constexpr=str(Bool(member.constexpr)),
                consteval=str(Bool(member.consteval)),
                explicit=str(Bool(member.explicit)),
                inline=str(Bool(member.inline)),
                noexcept=str(Bool(member.noexcept)),
                virtual=str(Virt(member.virtual)),
            )
            make_type(elem, member)
            xml_utils.make_child(elem, r'name').text = member.local_name
            xml_utils.make_child(elem, r'qualifiedname').text = member.qualified_name
            make_brief(elem, member)
            make_detail(elem, member)
            xml_utils.make_child(elem, r'inbodydescription').text = r''  # todo
            make_location(elem, member)

        # <initializer> for concepts
        if node.type is graph.Concept:
            make_initializer(compounddef, node)

        # <briefdescription>, <detaileddescription>, <location>
        make_brief(compounddef, node)
        make_detail(compounddef, node)
        make_location(compounddef, node)

        # <listofallmembers>
        if node.type in (graph.Class, graph.Struct, graph.Union):
            listofallmembers = xml_utils.make_child(compounddef, rf'listofallmembers')
            listofallmembers.text = r''
            for member_type in _ordered(graph.Function, graph.Variable):
                for member in node(member_type):
                    member_elem = xml_utils.make_child(
                        listofallmembers,
                        rf'member',
                        refid=member.id,
                        prot=str(Prot(member.access_level)),
                        virtual=str(Virt(member.virtual)),
                    )
                    xml_utils.make_child(member_elem, r'scope').text = node.qualified_name
                    xml_utils.make_child(member_elem, r'name').text = member.local_name

        # add the inners
        for inner_type in _ordered(
            graph.Directory,  #
            graph.File,
            graph.Namespace,
            graph.Class,
            graph.Struct,
            graph.Union,
            graph.Concept,
            graph.Page,
            graph.Group,
            graph.MemberGroup,
        ):
            for inner_node in node(inner_type):
                if not inner_node:
                    continue
                assert inner_node.qualified_name

                kind = None
                if inner_node.type in (graph.Class, graph.Struct, graph.Union):
                    kind = r'class'
                elif inner_node.type is graph.MemberGroup:
                    kind = r'group'
                else:
                    kind = NODE_TYPES_TO_KINDS[inner_node.type]
                inner_elem = xml_utils.make_child(compounddef, rf'inner{kind}', refid=inner_node.id)
                if node.type not in (graph.Namespace, graph.Directory, graph.File, graph.Group, graph.Page):
                    inner_elem.set(r'prot', str(Prot(inner_node.access_level)))
                inner_elem.text = inner_node.qualified_name

        # prune empty <sectiondefs> etc
        for tag_name in (r'sectiondef',):
            for elem in list(compounddef.findall(tag_name)):
                if not len(elem):
                    elem.getparent().remove(elem)

        if log_func:
            log_func(rf'Writing {path}')
        xml_utils.write(root, path)

    # serialize index.xml
    if 1:
        path = Path(folder, rf'index.xml')
        root = etree.XML(
            rf'''<doxygenindex
						xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
						xsi:noNamespaceSchemaLocation="index.xsd"
						version="{VERSION}"
						xml:lang="en-US">
					<!-- This file was created by Poxy - https://github.com/marzer/poxy -->
				</xmlns>''',
            parser=xml_utils.DEFAULT_PARSER,
        )
        for node_type in _ordered(*COMPOUND_NODE_TYPES):
            for node in g(node_type):
                compound = xml_utils.make_child(root, r'compound', refid=node.id, kind=NODE_TYPES_TO_KINDS[node.type])  #
                xml_utils.make_child(compound, r'name').text = node.qualified_name
                if node.type is graph.Directory:
                    continue
                for child_type in _ordered(graph.Define, graph.Function, graph.Variable, graph.Enum):
                    children = list(node(child_type))
                    if child_type is graph.Variable and node.type in (graph.Class, graph.Struct, graph.Union):
                        static_vars = [c for c in children if c.static]
                        static_vars.sort(key=lambda n: n.qualified_name)
                        children = static_vars + [c for c in children if not c.static]
                    else:
                        children.sort(key=lambda n: n.qualified_name)
                    for child in children:
                        assert child.local_name
                        member = xml_utils.make_child(
                            compound, r'member', refid=child.id, kind=NODE_TYPES_TO_KINDS[child.type]  #
                        )
                        xml_utils.make_child(member, r'name').text = child.local_name
                        if child_type is graph.Enum:
                            for enumvalue in child(graph.EnumValue):
                                assert enumvalue.local_name
                                elem = xml_utils.make_child(
                                    compound, r'member', refid=enumvalue.id, kind=NODE_TYPES_TO_KINDS[enumvalue.type]  #
                                )
                                xml_utils.make_child(elem, r'name').text = enumvalue.local_name

        if log_func:
            log_func(rf'Writing {path}')
        xml_utils.write(root, path)
