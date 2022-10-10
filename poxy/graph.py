#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and types for working with C++ project graphs.
"""

import enum
from .utils import *
from lxml import etree

#=======================================================================================================================
# Node types
#=======================================================================================================================



class Namespace(object):
	pass



class Class(object):
	pass



class Struct(object):
	pass



class Union(object):
	pass



class Concept(object):
	pass



class Function(object):
	pass



class Variable(object):
	pass



class Enum(object):
	pass



class EnumValue(object):
	pass



class Typedef(object):
	pass



class Define(object):
	pass



class Group(object):
	pass



class MemberGroup(object):
	pass



class Article(object):
	pass



class Directory(object):
	pass



class File(object):
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



@enum.unique
class ProtectionLevel(enum.Enum):
	PRIVATE = 0
	PROTECTED = 1
	PUBLIC = 2



#=======================================================================================================================
# Nodes
#=======================================================================================================================



class Node(object):

	def __init__(self, id: str):
		assert id is not None
		self.__id = id
		self.__connections = dict()

	#==============
	# getters
	#==============

	def __property_get(self, name: str, out_type=None, default=None):
		assert name is not None
		val = getattr(self, rf'_Node__{name}', None)
		if val is not None:
			if out_type is not None and not isinstance(val, out_type):
				val = out_type(val)
			return val
		return default

	@property
	def id(self) -> str:
		return self.__id

	@property
	def type(self):
		return self.__property_get(r'type')

	@property
	def has_type(self) -> bool:
		return self.type is not None

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
	def protection_level(self) -> ProtectionLevel:
		return self.__property_get(
			r'protection_level', ProtectionLevel,
			ProtectionLevel.PRIVATE if self.type is Class else ProtectionLevel.PUBLIC
		)

	@property
	def brief(self) -> str:
		return self.__property_get(r'brief', str, r'')

	@property
	def detail(self) -> str:
		return self.__property_get(r'detail', str, r'')

	def __bool__(self) -> bool:
		return self.has_type and bool(self.id) and bool(self.qualified_name)

	#==============
	# setters
	#==============

	def __property_set(self, name: str, out_type, value):
		assert name is not None
		# lxml elements can be assigned directly to take their text as a value
		if isinstance(value, (etree.ElementBase, etree._Element)):
			value = value.text
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
			elif out_type is ProtectionLevel:
				if value.lower() in (r'pub', r'public'):
					value = ProtectionLevel.PUBLIC
				elif value.lower() in (r'prot', r'protected'):
					value = ProtectionLevel.PROTECTED
				elif value.lower() in (r'priv', r'private'):
					value = ProtectionLevel.PRIVATE
				else:
					raise Exception(
						rf"C++ node '{self.id}' property '{name}' could not parse protection level from '{value}'"
					)
				assert isinstance(value, ProtectionLevel)
		# None == keep whatever the current value is (no-op)
		# (None is never a valid value for a real graph attribute)
		if value is None:
			return
		if out_type is not None and not isinstance(value, out_type):
			print(value)
			value = out_type(value)
		current = getattr(self, rf'_Node__{name}', None)
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
		setattr(self, rf'_Node__{name}', value)

	@type.setter
	def type(self, value):
		global NODE_TYPES
		if value is None:
			return
		if value not in NODE_TYPES:
			raise Exception(rf"Unknown C++ node type '{value}'")
		had_type = self.has_type
		self.__property_set(r'type', None, value)
		# if this was the setter responsible for enforcing the type, validate all existing connections
		# (since so far they have gone unchecked)
		if had_type != self.has_type:
			for id, node in self.__connections:
				Node._check_connection(self, node)

	@qualified_name.setter
	def qualified_name(self, value: str):
		self.__property_set(r'qualified_name', str, value)
		if self.qualified_name and not self.local_name and self.type in (
			Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, Typedef
		):
			ln = self.qualified_name
			pos = ln.rfind(r'::')
			if pos != -1:
				ln = ln[pos + 2:]
			ln = self.local_name

	@local_name.setter
	def local_name(self, value: str):
		self.__property_set(r'local_name', str, value)

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

	@protection_level.setter
	def protection_level(self, value: ProtectionLevel):
		self.__property_set(r'protection_level', ProtectionLevel, value)

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

		# self-connection is always illegal, regardless of type information
		if id(source) == id(dest):
			raise Exception(rf"C++ node '{source.id}' may not connect to itself")

		# otherwise if we don't have type information the connection is 'OK'
		# (really this just means we defer the check until later)
		if not source.has_type or not dest.has_type:
			return

		if dest.type not in source.type.CAN_CONNECT_TO:
			raise Exception(
				rf"C++ node '{source.id}' with type {source.type_name} is not allowed to connect to nodes of type {dest.type_name}"
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

	def iterator(self, *types):
		assert types is not None
		if not types:
			return self.__iter__()

		global NODE_TYPES
		for t in types:
			assert t is None or isinstance(t, bool) or t in NODE_TYPES

		def make_generator(nodes):
			nonlocal types
			yield_with_no_type = False in types or None in types
			yield_with_any_type = True in types
			for id, node in nodes:
				if ((node.type is None and yield_with_no_type)
					or (node.type is not None and (yield_with_any_type or node.type in types))):
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

	def iterator(self, *types):
		assert types is not None
		if not types:
			return self.__iter__()

		global NODE_TYPES
		for t in types:
			assert t is None or isinstance(t, bool) or t in NODE_TYPES

		def make_generator(nodes):
			nonlocal types
			yield_with_no_type = False in types or None in types
			yield_with_any_type = True in types
			for id, node in nodes:
				if ((node.type is None and yield_with_no_type)
					or (node.type is not None and (yield_with_any_type or node.type in types))):
					yield (id, node)

		return make_generator(self.__nodes.items())
