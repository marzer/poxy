#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and types for working with C++ project graphs.
"""

import enum as _enum
from .utils import *

#=======================================================================================================================
# Node types
#=======================================================================================================================



class Namespace(object):
	'''Namespaces.'''
	pass



class Class(object):
	'''Classes.'''
	pass



class Struct(object):
	'''Structs.'''
	pass



class Union(object):
	'''Unions.'''
	pass



class Concept(object):
	'''C++20 `concept`.'''
	pass



class Function(object):
	'''Functions.'''
	pass



class Variable(object):
	'''Variables.'''
	pass



class Enum(object):
	'''Enums.'''
	pass



class EnumValue(object):
	'''Enum values.'''
	pass



class Typedef(object):
	'''Typedefs/aliases.'''
	pass



class Define(object):
	'''Preprocessor `#defines`'''
	pass



class Group(object):
	'''Groups (at the global level).'''
	pass



class MemberGroup(object):
	'''Member groups (at the class/union/struct level).'''
	pass



class Article(object):
	'''A documentation article (e.g. Doxygen's `@page`).'''
	pass



class Directory(object):
	'''A directory in the filesystem.'''
	pass



class File(object):
	'''A file.'''
	pass



NODE_TYPES = {
	Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, EnumValue, Typedef, Define, Group, MemberGroup,
	Article, Directory, File
}
Namespace.CAN_CONNECT_TO = {Function, Class, Struct, Union, Variable, Typedef, Namespace, Concept, Enum}
Class.CAN_CONNECT_TO = {Class, Struct, Union, Function, Variable, Typedef, Enum, MemberGroup}
Struct.CAN_CONNECT_TO = Class.CAN_CONNECT_TO
Union.CAN_CONNECT_TO = Class.CAN_CONNECT_TO
Concept.CAN_CONNECT_TO = set()
Function.CAN_CONNECT_TO = set()  # not stricty true in C++ but true w.r.t documentation
Variable.CAN_CONNECT_TO = set()
Enum.CAN_CONNECT_TO = {EnumValue}
EnumValue.CAN_CONNECT_TO = set()
Typedef.CAN_CONNECT_TO = set()
Define.CAN_CONNECT_TO = set()
Group.CAN_CONNECT_TO = {t for t in NODE_TYPES if t not in (Article, )}
MemberGroup.CAN_CONNECT_TO = {t for t in Class.CAN_CONNECT_TO if t not in (MemberGroup, )}
Article.CAN_CONNECT_TO = set()
File.CAN_CONNECT_TO = {Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, Typedef, Define, Article}
Directory.CAN_CONNECT_TO = {Directory, File}



@_enum.unique
class AccessLevel(_enum.Enum):
	PRIVATE = 0
	PROTECTED = 1
	PUBLIC = 2



#=======================================================================================================================
# Nodes
#=======================================================================================================================



class Node(object):

	class _Props(object):
		pass

	def __init__(self, id: str):
		assert id is not None
		self.__id = id
		self.__connections = dict()
		self.__props = Node._Props()

	#==============
	# getters
	#==============

	def __property_get(self, name: str, out_type=None, default=None):
		assert name is not None
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
	def node_type(self):
		return self.__property_get(r'node_type')

	@property
	def has_node_type(self) -> bool:
		return self.node_type is not None

	@property
	def node_type_name(self) -> str:
		t = self.node_type
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
	def type(self) -> str:
		return self.__property_get(r'type', str, r'')

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
			r'access_level', AccessLevel, AccessLevel.PRIVATE if self.node_type is Class else AccessLevel.PUBLIC
		)

	@property
	def brief(self) -> str:
		return self.__property_get(r'brief', str, r'')

	@property
	def detail(self) -> str:
		return self.__property_get(r'detail', str, r'')

	def __bool__(self) -> bool:
		return self.has_node_type and bool(self.id)

	#==============
	# setters
	#==============

	def __property_is_set(self, name: str) -> bool:
		assert name is not None
		return hasattr(self.__props, str(name))

	def __property_set(self, name: str, out_type, value):
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
					raise Exception(rf"C++ node '{self.id}' property '{name}' could not parse a boolean from '{value}'")
			elif out_type is AccessLevel:
				if value.lower() in (r'pub', r'public'):
					value = AccessLevel.PUBLIC
				elif value.lower() in (r'prot', r'protected'):
					value = AccessLevel.PROTECTED
				elif value.lower() in (r'priv', r'private'):
					value = AccessLevel.PRIVATE
				else:
					raise Exception(
						rf"C++ node '{self.id}' property '{name}' could not parse access level from '{value}'"
					)
				assert isinstance(value, AccessLevel)
		# None == keep whatever the current value is (no-op)
		# (None is never a valid value for a real graph attribute)
		if value is None:
			return
		if out_type is not None and not isinstance(value, out_type):
			value = out_type(value)
		current = getattr(self.__props, str(name), None)
		# it's OK if there's already a value as long as it's identical to the new one,
		# otherwise we throw so that we can detect when the source data is bad or the adapter is faulty
		# (since if a property _can_ be defined in multiple places it should be identical in all of them)
		if current is not None:
			if type(current) != type(value):
				raise Exception(
					rf"C++ node '{self.id}' property '{name}' first seen with type {type(current)}, now seen with type {type(value)}"
				)
			if current != value:
				raise Exception(
					rf"C++ node '{self.id}' property '{name}' first seen with value {current}, now seen with value {value}"
				)
			return
		setattr(self.__props, str(name), value)

	@node_type.setter
	def node_type(self, value):
		global NODE_TYPES
		if value is None:
			return
		if value not in NODE_TYPES:
			raise Exception(rf"Unknown C++ node type '{value}'")
		had_node_type = self.has_node_type
		self.__property_set(r'node_type', None, value)
		if had_node_type != self.has_node_type:
			self.__deduce_local_name()
			for _, node in self.__connections:
				Node._check_connection(self, node)

	def __deduce_local_name(self):
		if not self.qualified_name or self.local_name or not self.has_node_type:
			return
		if self.node_type in (Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, Typedef):
			ln = self.qualified_name
			if ln.find(r'<') != -1:  # templates might have template args with '::' so ignore them
				return
			pos = ln.rfind(r'::')
			if pos != -1:
				ln = ln[pos + 2:]
			self.local_name = ln
		elif self.node_type in (Directory, File):
			ln = self.qualified_name
			pos = ln.rfind(r'/')
			if pos != -1:
				ln = ln[pos + 1:]
			self.local_name = ln

	@qualified_name.setter
	def qualified_name(self, value: str):
		if value is not None:
			value = str(value).strip()
		self.__property_set(r'qualified_name', str, value)
		self.__deduce_local_name()

	@local_name.setter
	def local_name(self, value: str):
		if value is not None:
			value = str(value).strip()
		self.__property_set(r'local_name', str, value)

	@type.setter
	def type(self, value: str):
		if value is not None:
			value = str(value).strip()
		# extract constexpr, constinit, static, mutable etc out of the type if possible
		attrs = re.fullmatch(r'^((?:(?:const(?:expr|init|eval)|static|mutable)\s)+).*?$', value)
		if attrs:
			value = value[len(attrs[1]):].strip()
			if attrs[1].find(r'constexpr') != -1:
				self.constexpr = True
			if attrs[1].find(r'constinit') != -1:
				self.constinit = True
			if attrs[1].find(r'consteval') != -1:
				self.consteval = True
			if attrs[1].find(r'static') != -1:
				self.static = True
			if attrs[1].find(r'mutable') != -1:
				self.mutable = True
		self.__property_set(r'type', str, value)

	@definition.setter
	def definition(self, value: str):
		self.__property_set(r'definition', str, value)

	@static.setter
	def static(self, value: bool):
		self.__property_set(r'static', bool, value)

	@const.setter
	def const(self, value: bool):
		self.__property_set(r'const', bool, value)

	@constexpr.setter
	def constexpr(self, value: bool):
		self.__property_set(r'constexpr', bool, value)

	@constinit.setter
	def constinit(self, value: bool):
		self.__property_set(r'constinit', bool, value)

	@consteval.setter
	def consteval(self, value: bool):
		self.__property_set(r'consteval', bool, value)

	@inline.setter
	def inline(self, value: bool):
		self.__property_set(r'inline', bool, value)

	@final.setter
	def final(self, value: bool):
		self.__property_set(r'final', bool, value)

	@explicit.setter
	def explicit(self, value: bool):
		self.__property_set(r'explicit', bool, value)

	@noexcept.setter
	def noexcept(self, value: bool):
		self.__property_set(r'noexcept', bool, value)

	@virtual.setter
	def virtual(self, value: bool):
		self.__property_set(r'virtual', bool, value)

	@mutable.setter
	def mutable(self, value: bool):
		self.__property_set(r'mutable', bool, value)

	@strong.setter
	def strong(self, value: bool):
		self.__property_set(r'strong', bool, value)

	@access_level.setter
	def access_level(self, value: AccessLevel):
		self.__property_set(r'access_level', AccessLevel, value)

	#==============
	# membership
	#==============

	@property
	def is_leaf(self) -> bool:
		return not bool(self.__connections)

	@classmethod
	def _check_connection(cls, source, dest):
		assert source is not None
		assert isinstance(source, Node)
		assert dest is not None
		assert isinstance(dest, Node)

		# self-connection is always illegal, regardless of node_type information
		if id(source) == id(dest):
			raise Exception(rf"C++ node '{source.id}' may not connect to itself")

		# otherwise if we don't have node_type information the connection is 'OK'
		# (really this just means we defer the check until later)
		if not source.has_node_type or not dest.has_node_type:
			return

		if dest.node_type not in source.node_type.CAN_CONNECT_TO:
			raise Exception(
				rf"C++ node '{source.id}' with type {source.node_type_name} is not allowed to connect to nodes of type {dest.node_type_name}"
			)

	def connect_to(self, dest):
		assert dest is not None
		assert isinstance(dest, Node)

		Node._check_connection(self, dest)

		# connecting to the same node twice is fine (no-op)
		if dest.id in self.__connections:
			existing_dest = self.__connections[dest.id]
			# check that identity is unique
			if id(dest) != id(existing_dest):
				raise Exception(rf"Two different C++ nodes seen with the same ID ('{dest.id}')")
			return

		self.__connections[dest.id] = dest

	def __contains__(self, node_or_id) -> bool:
		assert isinstance(node_or_id, (str, Node))
		if isinstance(node_or_id, str):
			return node_or_id in self.__connections
		return node_or_id in self.__connections.values()

	def __iter__(self):
		for id, node in self.__connections.items():
			yield (id, node)

	def __call__(self, *node_types):
		assert node_types is not None
		if not node_types:
			return self.__iter__()

		global NODE_TYPES
		for t in node_types:
			assert t is None or isinstance(t, bool) or t in NODE_TYPES

		def make_generator(nodes):
			nonlocal node_types
			yield_with_no_node_type = False in node_types or None in node_types
			yield_with_any_node_type = True in node_types
			for id, node in nodes:
				if ((node.node_type is None and yield_with_no_node_type)
					or (node.node_type is not None and (yield_with_any_node_type or node.node_type in node_types))):
					yield (id, node)

		return make_generator(self.__connections.items())



#=======================================================================================================================
# Graph
#=======================================================================================================================



class Graph(object):

	def __init__(self):
		self.__nodes: typing.Dict[str, Node]
		self.__nodes = dict()

	def get_or_create_node(self, id: str) -> Node:
		assert id
		node = None
		if id not in self.__nodes:
			node = Node(id)
			self.__nodes[id] = node
		else:
			node = self.__nodes[id]
		return node

	def __iter__(self):
		for id, node in self.__nodes.items():
			yield (id, node)

	def __call__(self, *node_types):
		assert node_types is not None
		if not node_types:
			return self.__iter__()

		global NODE_TYPES
		for t in node_types:
			assert t is None or isinstance(t, bool) or t in NODE_TYPES

		def make_generator(nodes):
			nonlocal node_types
			yield_with_no_node_type = False in node_types or None in node_types
			yield_with_any_node_type = True in node_types
			for id, node in nodes:
				if ((node.node_type is None and yield_with_no_node_type)
					or (node.node_type is not None and (yield_with_any_node_type or node.node_type in node_types))):
					yield (id, node)

		return make_generator(self.__nodes.items())
