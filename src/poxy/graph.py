#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and types for working with C++ project graphs.
"""

import enum as _enum

from .utils import *

# =======================================================================================================================
# Node types
# =======================================================================================================================


class _NodeType:
    '''Base for the node-type tag classes. CAN_CONTAIN is populated at module scope below.'''

    CAN_CONTAIN: typing.ClassVar[typing.Set[type]] = set()


class Namespace(_NodeType):
    '''Namespaces.'''

    pass


class Class(_NodeType):
    '''Classes.'''

    pass


class Struct(_NodeType):
    '''Structs.'''

    pass


class Union(_NodeType):
    '''Unions.'''

    pass


class Concept(_NodeType):
    '''C++20 `concept`.'''

    pass


class Function(_NodeType):
    '''Functions.'''

    pass


class Type(_NodeType):
    '''The type of a variable/enum/function return.'''

    pass


class Variable(_NodeType):
    '''Variables.'''

    pass


class Enum(_NodeType):
    '''Enums.'''

    pass


class EnumValue(_NodeType):
    '''Enum values.'''

    pass


class Typedef(_NodeType):
    '''Typedefs/aliases.'''

    pass


class Define(_NodeType):
    '''Preprocessor `#defines`'''

    pass


class Group(_NodeType):
    '''Groups (at the global level).'''

    pass


class MemberGroup(_NodeType):
    '''Member groups (at the class/union/struct level).'''

    pass


class Directory(_NodeType):
    '''A directory in the filesystem.'''

    pass


class File(_NodeType):
    '''A file.'''

    pass


class Page(_NodeType):
    '''A documentation page (e.g. Doxygen's `@page`).'''

    pass


class BriefDescription(_NodeType):
    '''A brief description of an element.'''

    pass


class DetailedDescription(_NodeType):
    '''A more detailed description of an element.'''

    pass


class Initializer(_NodeType):
    '''An initializer block (usually a code snippet).'''

    pass


class Paragraph(_NodeType):
    '''A paragraph.'''

    pass


class Text(_NodeType):
    '''Plain text.'''

    pass


class Reference(_NodeType):
    '''A reference to another node.'''

    pass


class ExternalResource(_NodeType):
    '''A reference to some resource outside the project (e.g. something in a tagfile).'''

    pass


class ExpositionMarkup(_NodeType):
    '''A 'leftover' node for representing miscellaneous markup in expository contexts.'''

    pass


class Friend(_NodeType):
    '''A friend relationship.'''

    pass


NODE_TYPES = {
    Namespace,
    Class,
    Struct,
    Union,
    Concept,
    Function,
    Variable,
    Enum,
    EnumValue,
    Typedef,
    Define,
    Group,
    MemberGroup,
    Directory,
    File,
    BriefDescription,
    DetailedDescription,
    Page,
    Initializer,
    Paragraph,
    Text,
    Reference,
    ExternalResource,
    Type,
    ExpositionMarkup,
    Friend,
}
DESCRIPTION_NODE_TYPES = {BriefDescription, DetailedDescription}
EXPOSITION_NODE_TYPES = {
    *DESCRIPTION_NODE_TYPES,
    Page,
    Initializer,
    Paragraph,
    Text,
    Reference,
    ExternalResource,
    Type,
    ExpositionMarkup,
}
CPP_TYPES = {Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, EnumValue, Typedef, Define}
Namespace.CAN_CONTAIN = {
    Function,
    Class,
    Struct,
    Union,
    Variable,
    Typedef,
    Namespace,
    Concept,
    Enum,
    *DESCRIPTION_NODE_TYPES,
}
Class.CAN_CONTAIN = {
    Class,
    Struct,
    Union,
    Function,
    Variable,
    Typedef,
    Enum,
    MemberGroup,
    Friend,
    *DESCRIPTION_NODE_TYPES,
}
Struct.CAN_CONTAIN = Class.CAN_CONTAIN
Union.CAN_CONTAIN = Class.CAN_CONTAIN
Concept.CAN_CONTAIN = {Initializer, *DESCRIPTION_NODE_TYPES}
Function.CAN_CONTAIN = {Type, *DESCRIPTION_NODE_TYPES}
Variable.CAN_CONTAIN = {Type, Initializer, *DESCRIPTION_NODE_TYPES}
Enum.CAN_CONTAIN = {Type, EnumValue, *DESCRIPTION_NODE_TYPES}
EnumValue.CAN_CONTAIN = {Initializer, *DESCRIPTION_NODE_TYPES}
Typedef.CAN_CONTAIN = {Type, *DESCRIPTION_NODE_TYPES}
Define.CAN_CONTAIN = {Initializer, *DESCRIPTION_NODE_TYPES}
Group.CAN_CONTAIN = {t for t in NODE_TYPES if t not in (Page,)}
MemberGroup.CAN_CONTAIN = {t for t in Class.CAN_CONTAIN if t not in (MemberGroup,)}
Directory.CAN_CONTAIN = {Directory, File, *DESCRIPTION_NODE_TYPES}
File.CAN_CONTAIN = {
    Namespace,
    Class,
    Struct,
    Union,
    Concept,
    Function,
    Variable,
    Enum,
    Typedef,
    Define,
    Page,
    *DESCRIPTION_NODE_TYPES,
}
Page.CAN_CONTAIN = {Paragraph, Text, Reference, *DESCRIPTION_NODE_TYPES, ExpositionMarkup}
BriefDescription.CAN_CONTAIN = {Paragraph, Text, Reference, ExpositionMarkup}
DetailedDescription.CAN_CONTAIN = {Paragraph, Text, Reference, ExpositionMarkup}
Initializer.CAN_CONTAIN = {Text, Reference, ExpositionMarkup}
Paragraph.CAN_CONTAIN = {Text, Reference, ExpositionMarkup}
Text.CAN_CONTAIN = set()
ExpositionMarkup.CAN_CONTAIN = {Paragraph, Text, Reference, ExpositionMarkup}
Type.CAN_CONTAIN = {Text, Reference}
Reference.CAN_CONTAIN = {*CPP_TYPES, Page, Group, MemberGroup, Directory, File, ExternalResource}
ExternalResource.CAN_CONTAIN = set()
Friend.CAN_CONTAIN = {Function, Class, Struct, Union, *DESCRIPTION_NODE_TYPES}


@_enum.unique
class AccessLevel(_enum.Enum):
    PRIVATE = 0
    PROTECTED = 1
    PUBLIC = 2


# =======================================================================================================================
# Nodes
# =======================================================================================================================


def _make_node_iterator(nodes, *types):
    assert types is not None

    def permissive_generator():
        nonlocal nodes
        yield from nodes

    if not types:
        return permissive_generator()

    for t in types:
        assert t is None or isinstance(t, bool) or t in NODE_TYPES

    def selective_generator():
        nonlocal nodes
        nonlocal types
        yield_with_no_type = False in types or None in types
        yield_with_any_type = True in types
        for node in nodes:
            if (node.type is None and yield_with_no_type) or (
                node.type is not None and (yield_with_any_type or node.type in types)
            ):
                yield node

    return selective_generator()


class _NullNodeIterator:
    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration


class GraphError(Error):
    """Raised when a C++ graph error occurs."""

    pass


class GraphNodePropertyChanged(GraphError):
    """Raised when an attempt is made to change an already-set property in a graph node."""

    pass


class Node:
    """A single node in a C++ project graph."""

    class _Props:
        pass

    def __make_hierarchy_containers(self):
        if hasattr(self, r'_Node__children'):
            return
        self.__parents = []
        self.__parents_by_id = dict()
        self.__children = []
        self.__children_by_id = dict()

    def __init__(self, id: str):
        assert id is not None
        self.__id = id

    # ==============
    # getters
    # ==============

    def __property_get(self, name: str, out_type=None, default=None) -> typing.Any:
        assert name is not None
        value = None
        if hasattr(self, r'_Node__props'):
            value = getattr(self.__props, str(name), None)
        if value is None:
            value = default
        if value is not None and out_type is not None and not isinstance(value, out_type):
            value = out_type(value)
        return value

    @property
    def id(self) -> str:
        return self.__id

    @property
    def type(self):
        return self.__property_get(r'type')

    @property
    def type_name(self) -> str:
        t = self.type
        if t is None:
            return ''
        return t.__name__

    @property
    def qualified_name(self) -> str:
        return self.__property_get(r'qualified_name', str, r'')

    @property
    def local_name(self) -> str:
        return self.__property_get(r'local_name', str, r'')

    @property
    def definition(self) -> str:
        return self.__property_get(r'definition', str, r'')

    @property
    def static(self) -> bool:
        return self.__property_get(r'static', bool, False)

    @property
    def const(self) -> bool:
        return self.__property_get(r'const', bool, False)

    @property
    def constexpr(self) -> bool:
        return self.__property_get(r'constexpr', bool, False)

    @property
    def constinit(self) -> bool:
        return self.__property_get(r'constinit', bool, False)

    @property
    def consteval(self) -> bool:
        return self.__property_get(r'consteval', bool, False)

    @property
    def inline(self) -> bool:
        return self.__property_get(r'inline', bool, False)

    @property
    def final(self) -> bool:
        return self.__property_get(r'final', bool, False)

    @property
    def explicit(self) -> bool:
        return self.__property_get(r'explicit', bool, False)

    @property
    def noexcept(self) -> bool:
        return self.__property_get(r'noexcept', bool, False)

    @property
    def virtual(self) -> bool:
        return self.__property_get(r'virtual', bool, False)

    @property
    def mutable(self) -> bool:
        return self.__property_get(r'mutable', bool, False)

    @property
    def strong(self) -> bool:
        return self.__property_get(r'strong', bool, False)

    @property
    def access_level(self) -> AccessLevel:
        return self.__property_get(
            r'access_level', AccessLevel, AccessLevel.PRIVATE if self.type is Class else AccessLevel.PUBLIC
        )

    @property
    def text(self) -> str:
        return self.__property_get(r'text', str, r'')

    @property
    def is_paragraph(self) -> bool:
        return self.__property_get(r'is_paragraph', bool, False)

    @property
    def file(self) -> str:
        return self.__property_get(r'file', str, r'')

    @property
    def line(self) -> int:
        return self.__property_get(r'line', int, 0)

    @property
    def column(self) -> int:
        return self.__property_get(r'column', int, 0)

    @property
    def kind(self) -> str:
        return self.__property_get(r'kind', str, r'')

    @property
    def tag(self) -> str:
        return self.__property_get(r'tag', str, r'')

    @property
    def extra_attributes(self) -> typing.Sequence[typing.Tuple[str, str]]:
        return self.__property_get(r'extra_attributes', None, tuple())

    def __bool__(self) -> bool:
        return self.type is not None and bool(self.id)

    # ==============
    # setters
    # ==============

    def __property_set(self, name: str, out_type, value, strip_strings=False):
        assert name is not None
        # known types that have a sensible __bool__ operator can convert to None if false
        if isinstance(value, (str, Path, list, tuple, dict)):
            value = value if value else None
        # converting from strings sometimes lets us do some light parsing, as a treat
        if isinstance(value, str):
            if out_type is bool:
                if value.lower() in (r'no', r'false', r'disabled'):
                    value = False
                elif value.lower() in (r'yes', r'true', r'enabled'):
                    value = True
                else:
                    raise GraphError(rf"Node '{self.id}' property '{name}' could not parse a boolean from '{value}'")
            elif out_type is AccessLevel:
                if value.lower() in (r'pub', r'public'):
                    value = AccessLevel.PUBLIC
                elif value.lower() in (r'prot', r'protected'):
                    value = AccessLevel.PROTECTED
                elif value.lower() in (r'priv', r'private'):
                    value = AccessLevel.PRIVATE
                else:
                    raise GraphError(rf"Node '{self.id}' property '{name}' could not parse access level from '{value}'")
                assert isinstance(value, AccessLevel)
        # None == keep whatever the current value is (no-op)
        # (None is never a valid value for a real graph attribute)
        if value is None:
            return
        if out_type is not None and not isinstance(value, out_type):
            value = out_type(value)
        if strip_strings and isinstance(value, str):
            value = value.strip()
        current = None
        has_props = hasattr(self, r'_Node__props')
        if has_props:
            current = getattr(self.__props, str(name), None)
        # it's OK if there's already a value as long as it's identical to the new one,
        # otherwise we throw so that we can detect when the source data is bad or the adapter is faulty
        # (since if a property _can_ be defined in multiple places it should be identical in all of them)
        if current is not None:
            if type(current) is not type(value):
                raise GraphNodePropertyChanged(
                    rf"Node '{self.id}' property '{name}' first seen with type {type(current)}, now seen with type {type(value)}"
                )
            if current != value:
                raise GraphNodePropertyChanged(
                    rf"Node '{self.id}' property '{name}' first seen with value '{current}', now seen with value '{value}'"
                )
            return
        if not has_props:
            self.__props = Node._Props()
        setattr(self.__props, str(name), value)

    @type.setter
    def type(self, value):
        if value is None:
            return
        if value not in NODE_TYPES:
            raise GraphError(rf"Unknown C++ node type '{value}'")
        had_type = self.type is not None
        self.__property_set(r'type', None, value)
        if had_type != (self.type is not None):
            self.__deduce_local_name()
            if hasattr(self, r'_Node__children'):
                for child in self.__children:
                    Node._check_connection(self, child)

    def __deduce_local_name(self):
        if not self.qualified_name or self.local_name or self.type is None:
            return
        if self.type in (Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, EnumValue, Typedef):
            if self.qualified_name.find(r'<') != -1:  # templates might have template args with '::' so ignore them
                return
            self.local_name = tail(self.qualified_name, r'::')
        elif self.type in (Directory, File):
            self.local_name = tail(self.qualified_name, r'/')
        elif self.type is Define:
            self.local_name = self.qualified_name

    @qualified_name.setter
    def qualified_name(self, value: typing.Optional[str]):
        if value is not None and self.type in (Directory, File):
            value = str(value).strip().replace('\\', r'/').rstrip(r'/')
        self.__property_set(r'qualified_name', str, value, strip_strings=True)
        self.__deduce_local_name()

    @local_name.setter
    def local_name(self, value: typing.Optional[str]):
        self.__property_set(r'local_name', str, value, strip_strings=True)

    @definition.setter
    def definition(self, value: typing.Optional[str]):
        self.__property_set(r'definition', str, value)

    @static.setter
    def static(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'static', bool, value)

    @const.setter
    def const(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'const', bool, value)

    @constexpr.setter
    def constexpr(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'constexpr', bool, value)

    @constinit.setter
    def constinit(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'constinit', bool, value)

    @consteval.setter
    def consteval(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'consteval', bool, value)

    @inline.setter
    def inline(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'inline', bool, value)

    @final.setter
    def final(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'final', bool, value)

    @explicit.setter
    def explicit(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'explicit', bool, value)

    @noexcept.setter
    def noexcept(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'noexcept', bool, value)

    @virtual.setter
    def virtual(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'virtual', bool, value)

    @mutable.setter
    def mutable(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'mutable', bool, value)

    @strong.setter
    def strong(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'strong', bool, value)

    @access_level.setter
    def access_level(self, value: typing.Union[AccessLevel, str, None]):
        self.__property_set(r'access_level', AccessLevel, value)

    @text.setter
    def text(self, value: typing.Optional[str]):
        self.__property_set(r'text', str, value)

    @is_paragraph.setter
    def is_paragraph(self, value: typing.Union[bool, str, None]):
        self.__property_set(r'is_paragraph', bool, value)

    @file.setter
    def file(self, value: typing.Optional[str]):
        if value is not None:
            value = str(value).strip().replace('\\', r'/').rstrip(r'/')
        self.__property_set(r'file', str, value)

    @line.setter
    def line(self, value: typing.Union[int, str, None]):
        self.__property_set(r'line', int, value)

    @column.setter
    def column(self, value: typing.Union[int, str, None]):
        self.__property_set(r'column', int, value)

    @kind.setter
    def kind(self, value: typing.Optional[str]):
        self.__property_set(r'kind', str, value, strip_strings=True)

    @tag.setter
    def tag(self, value: typing.Optional[str]):
        self.__property_set(r'tag', str, value, strip_strings=True)

    @extra_attributes.setter
    def extra_attributes(self, value: typing.Optional[typing.Sequence[typing.Tuple[str, str]]]):
        self.__property_set(r'extra_attributes', None, value)

    # ==============
    # children
    # ==============

    @property
    def is_child(self) -> bool:
        return hasattr(self, r'_Node__children') and bool(self.__parents)

    @property
    def is_parent(self) -> bool:
        return hasattr(self, r'_Node__children') and bool(self.__children)

    def __contains__(self, node_or_id) -> bool:
        assert node_or_id is not None
        assert isinstance(node_or_id, (str, Node)) or node_or_id in NODE_TYPES
        if not hasattr(self, r'_Node__children'):
            return False
        if isinstance(node_or_id, Node):
            node_or_id = node_or_id.id
        if isinstance(node_or_id, str):
            return node_or_id in self.__children_by_id
        else:
            for c in self.__children:
                if c.type is node_or_id:
                    return True
            return False

    def has_parent(self, *node_or_id_or_types) -> bool:
        assert node_or_id_or_types is not None
        if not hasattr(self, r'_Node__parents'):
            return False
        for target in node_or_id_or_types:
            if isinstance(target, Node):
                target = target.id
            if isinstance(target, str):
                return target in self.__parents_by_id
            else:
                assert target in NODE_TYPES
                for c in self.__parents:
                    if c.type is target:
                        return True
        return False

    def __getitem__(self, id_or_index: typing.Union[str, int]):
        assert id_or_index is not None
        assert isinstance(id_or_index, (str, int)) or id_or_index in NODE_TYPES
        if not hasattr(self, r'_Node__children'):
            return None
        if isinstance(id_or_index, str):
            try:
                return self.__children_by_id[id_or_index]
            except Exception:
                return None
        elif isinstance(id_or_index, int):
            return self.__children[id_or_index]
        else:
            for c in self(id_or_index):
                return c
            raise KeyError(id_or_index.__name__)

    @classmethod
    def _check_connection(cls, source, dest):
        assert source is not None
        assert isinstance(source, Node)
        assert dest is not None
        assert isinstance(dest, Node)

        # self-connection is always illegal, regardless of type information
        if id(source) == id(dest):
            raise GraphError(rf"Node '{source.id}' may not connect to itself")

        # otherwise if we don't have type information the connection is 'OK'
        # (really this just means we defer the check until later)
        if source.type is None or dest.type is None:
            return

        # check basic connection rules
        if dest.type not in source.type.CAN_CONTAIN:
            raise GraphError(
                rf"{source.type_name} node '{source.id}' is not allowed to connect to {dest.type_name} nodes"
            )

        # check situations where a node must only belong to one parent of a particular set of types
        def check_single_parent(dest_types, source_types):
            nonlocal source
            nonlocal dest
            source_types = typing.cast(typing.Collection[type], coerce_collection(source_types))
            dest_types = typing.cast(typing.Collection[type], coerce_collection(dest_types))
            if source.type not in source_types or dest.type not in dest_types:
                return
            sum = 0
            for parent in dest(*source_types, parents=True):
                sum += 1
            if dest not in source:
                sum += 1
            if sum > 1:
                raise GraphError(
                    rf"{dest.type_name} node '{dest.id}' is not allowed to be a member of more than one "
                    + rf"{{ {', '.join([t.__name__ for t in source_types])} }}"
                )

        check_single_parent(EnumValue, Enum)
        check_single_parent(Type, (Variable, Function, Enum, Typedef))
        check_single_parent(Friend, (Class, Struct, Union))
        check_single_parent(Reference, NODE_TYPES)

        # same again but in the other direction
        def check_single_child(source_types, dest_types):
            nonlocal source
            nonlocal dest
            source_types = typing.cast(typing.Collection[type], coerce_collection(source_types))
            dest_types = typing.cast(typing.Collection[type], coerce_collection(dest_types))
            if source.type not in source_types or dest.type not in dest_types:
                return
            sum = 0
            for child in source(*dest_types):
                sum += 1
            if dest not in source:
                sum += 1
            if sum > 1:
                raise GraphError(
                    rf"{source.type_name} node '{source.id}' is not allowed to be connected to more than one "
                    + rf"{{ {', '.join([t.__name__ for t in dest_types])} }}"
                )

        check_single_child(Friend, (Class, Struct, Union, Function))
        check_single_child(Reference, NODE_TYPES)

    def add(self, child):
        assert child is not None
        assert isinstance(child, Node)

        # connecting to the same node twice is fine (no-op)
        if child in self:
            existing_child = self.__children_by_id[child.id]
            # check that identity is unique
            if id(child) != id(existing_child):
                raise GraphError(rf"Two different nodes seen with the same ID ('{child.id}')")
            return

        Node._check_connection(self, child)

        self.__make_hierarchy_containers()
        self.__children.append(child)
        self.__children_by_id[child.id] = child

        child.__make_hierarchy_containers()
        child.__parents.append(self)
        child.__parents_by_id[self.id] = self

    def __iter__(self):
        if not hasattr(self, r'_Node__children'):
            return _NullNodeIterator()
        return _make_node_iterator(self.__children)

    def __call__(self, *types, parents=False):
        if not hasattr(self, r'_Node__children'):
            return _NullNodeIterator()
        return _make_node_iterator(self.__parents if parents else self.__children, *types)

    def remove(self, child):
        assert child is not None
        assert isinstance(child, Node)

        if not hasattr(self, r'_Node__children') or child not in self or child is self:
            return

        self.__children.remove(child)
        del self.__children_by_id[child.id]

        child.__parents.remove(self)
        del child.__parents_by_id[self.id]

    def clear(self):
        if not hasattr(self, r'_Node__children'):
            return

        for child in self.__children:
            child.__parents.remove(self)
            del child.__parents_by_id[self.id]

        self.__children.clear()
        self.__children_by_id.clear()

    # ==============
    # relationship queries
    # ==============

    @property
    def is_class_member(self) -> bool:
        return self.has_parent(Class, Struct, Union)

    @property
    def is_class_member_variable(self) -> bool:
        return self.type is Variable and self.is_class_member

    @property
    def is_class_member_function(self) -> bool:
        return self.type is Function and self.is_class_member

    @property
    def is_free_function(self) -> bool:
        return self.type is Function and not self.is_class_member

    @property
    def is_static_function(self) -> bool:
        return self.type is Function and self.static

    @property
    def is_friend(self) -> bool:
        return self.has_parent(Friend)

    @property
    def is_friend_function(self) -> bool:
        return self.type is Function and self.is_friend

    @property
    def is_friend_class(self) -> bool:
        return self.type in (Class, Struct, Union) and self.is_friend

    @property
    def has_friends(self) -> bool:
        return Friend in self

    # ==============
    # misc
    # ==============

    def copy(self, id=None, transform=None):
        node = Node(self.id if id is None else id)
        if transform is not None:
            transform(self, node)
        if hasattr(self, r'_Node__props'):
            node.__props = Node._Props()
            for key, val in self.__props.__dict__.items():
                if not hasattr(node.__props, key):
                    setattr(node.__props, key, val)
        return node


# =======================================================================================================================
# Graph
# =======================================================================================================================


class Graph:
    """A C++ project graph."""

    def __init__(self):
        self.__nodes: typing.Dict[str, Node]
        self.__nodes = dict()
        self.__next_unique_id = 0

    def __get_unique_id(self) -> str:
        id = rf'__graph_unique_id_{self.__next_unique_id}'
        self.__next_unique_id += 1
        return id

    def get_or_create_node(self, id: typing.Optional[str] = None, type=None, parent=None) -> Node:
        if id is None:
            id = self.__get_unique_id()
        assert id
        node = None
        if id not in self.__nodes:
            node = Node(id)
            self.__nodes[id] = node
        else:
            node = self.__nodes[id]
        node.type = type
        if parent is not None:
            parent.add(node)
        return node

    def __iter__(self):
        return _make_node_iterator(self.__nodes.values())

    def __call__(self, *types):
        return _make_node_iterator(self.__nodes.values(), *types)

    def __contains__(self, node_or_id) -> bool:
        assert node_or_id is not None
        assert isinstance(node_or_id, (str, Node)) or node_or_id in NODE_TYPES
        if isinstance(node_or_id, Node):
            node_or_id = node_or_id.id
        if isinstance(node_or_id, str):
            return node_or_id in self.__nodes
        else:
            for n in self.__nodes.values():
                if n.type is node_or_id:
                    return True
            return False

    def __getitem__(self, id: str) -> typing.Optional[Node]:
        assert id is not None
        assert isinstance(id, str)
        try:
            return self.__nodes[id]
        except Exception:
            return None

    def remove(self, *nodes: Node, filter=None):
        if filter is not None and not nodes:
            nodes = tuple(self.__nodes.values())
        prune = []
        for node in nodes:
            if node is None or node not in self:
                continue
            if filter is not None and not filter(node):
                continue
            for _, other in self.__nodes.items():
                if node is not other:
                    other.remove(node)
            node.clear()
            prune.append(node)
        for node in prune:
            del self.__nodes[node.id]

    def validate(self):
        for node in self:
            if node.type is None:
                raise GraphError(rf"Node '{node.id}' is untyped")
            if node.type not in EXPOSITION_NODE_TYPES:
                if not node.qualified_name:
                    raise GraphError(rf"{node.type_name} node '{node.id}' missing attribute 'qualified_name'")
                if not node.local_name:
                    raise GraphError(rf"{node.type_name} node '{node.id}' missing attribute 'local_name'")

            if node.file.find('\\') != -1:
                raise GraphError(rf"{node.type_name} node '{node.id}' attribute 'file' contains back-slashes")
            if node.file.endswith(r'/'):
                raise GraphError(rf"{node.type_name} node '{node.id}' attribute 'file' ends with a forward-slash")
            if node.line < 0:
                raise GraphError(rf"{node.type_name} node '{node.id}' attribute 'line' is negative")
            if node.column < 0:
                raise GraphError(rf"{node.type_name} node '{node.id}' attribute 'column' is negative")

            if node.type in (Directory, File):
                if node.qualified_name.find('\\') != -1:
                    raise GraphError(
                        rf"{node.type_name} node '{node.id}' attribute 'qualified_name' contains back-slashes"
                    )
                if node.qualified_name.endswith(r'/'):
                    raise GraphError(
                        rf"{node.type_name} node '{node.id}' attribute 'qualified_name' ends with a forward-slash"
                    )
            if node.type in CPP_TYPES:
                if node.qualified_name.startswith(r'::'):
                    raise GraphError(rf"{node.type_name} node '{node.id}' attribute 'qualified_name' starts with ::")
                if node.qualified_name.endswith(r'::'):
                    raise GraphError(rf"{node.type_name} node '{node.id}' attribute 'qualified_name' ends with ::")
                if node.type is not EnumValue and not node.file:
                    raise GraphError(rf"{node.type_name} node '{node.id}' missing attribute 'file'")

            if node.type in (EnumValue, Type, Friend):
                if not node.is_child:
                    raise GraphError(rf"{node.type_name} node '{node.id}' is an orphan")

            if node.type in (Function, Variable, Typedef):
                if Type not in node:
                    raise GraphError(rf"{node.type_name} node '{node.id}' is missing a Type")

    def copy(self, filter=None, id_transform=None, transform=None):
        g = Graph()
        id_remap = dict()
        # first pass to copy
        for src in self:
            if filter is not None and not filter(src):
                continue
            id = src.id
            if id_transform is not None:
                id = id_transform(src)
            if id is None:
                id = g.__get_unique_id()
            else:
                id = str(id)
            if id in g:
                raise GraphError(rf"A node with id '{id}' already exists in the destination graph")
            id_remap[src.id] = id
            g.__nodes[id] = src.copy(id=id, transform=transform)
        # second pass to link hierarchy
        for src in self:
            if src.id not in id_remap:
                continue
            for child in src:
                if child.id not in id_remap:
                    continue
                parent = g[id_remap[src.id]]
                remapped_child = g[id_remap[child.id]]
                assert parent is not None and remapped_child is not None
                parent.add(remapped_child)
        return g
