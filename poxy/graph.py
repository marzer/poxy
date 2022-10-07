#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and types for working with C++ project graphs.
"""

from .utils import *
from enum import Enum
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



class Typedef(object):
	pass



class Group(object):
	pass



class Define(object):
	pass



class File(object):
	pass



class Directory(object):
	pass



NODE_TYPES = {
	Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, Typedef, Group, Define, File, Directory
}
Namespace.CONNECTS_TO = {Function, Class, Struct, Union, Variable, Typedef, Namespace, Concept, Enum}
Class.CONNECTS_TO = {Class, Struct, Union}
Struct.CONNECTS_TO = {Class, Struct, Union}
Union.CONNECTS_TO = {Class, Struct, Union}
Concept.CONNECTS_TO = set()
Function.CONNECTS_TO = {Class, Struct, Union, Variable, Enum, Typedef}
Variable.CONNECTS_TO = set()
Enum.CONNECTS_TO = {Variable}
Typedef.CONNECTS_TO = set()
Group.CONNECTS_TO = NODE_TYPES
Define.CONNECTS_TO = set()
File.CONNECTS_TO = {Namespace, Class, Struct, Union, Concept, Function, Variable, Enum, Typedef, Define}
Directory.CONNECTS_TO = {File, Directory}



class Visibility(Enum):
	PRIVATE = 0
	PROTECTED = 1
	PUBLIC = 2



#=======================================================================================================================
# Nodes
#=======================================================================================================================



class Node(object):

	def __init__(self, id: str):
		assert id
		self.__id = id

	#==============
	# getters
	#==============

	def __property_get(self, name: str, type_func=None, default=None):
		assert name is not None
		val = getattr(self, rf'_Node__{name}', None)
		if val is not None:
			if type_func is not None:
				val = type_func(val)
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
	def visibility(self) -> Visibility:
		return self.__property_get(
			r'visibility', Visibility, Visibility.PRIVATE if self.type is Class else Visibility.PUBLIC
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
	# getters
	#==============

	def __property_set(self, name: str, type_func, value):
		assert name is not None
		if isinstance(value, (str, Path, list, tuple, dict)):
			value = value if value else None
		if isinstance(value, (etree.ElementBase, etree._Element)):
			value = value.text.strip()
		if isinstance(value, str) and type_func is bool:
			if value.lower() in (r'no', r'false', r'disabled'):
				value = False
			elif value.lower() in (r'yes', r'true', r'enabled'):
				value = True
		if value is None:
			return
		if type_func is not None:
			value = type_func(value)
		current = getattr(self, rf'_Node__{name}', None)
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
		if value is not None and value not in NODE_TYPES:
			raise Exception(rf"Unknown C++ node type '{value}'")
		self.__property_set(r'type', None, value)

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

	@visibility.setter
	def visibility(self, value: Visibility):
		self.__property_set(r'visibility', Visibility, value)

	#==============
	# membership
	#==============

	@property
	def is_child(self) -> bool:
		if not hasattr(self, r'_Node__parents'):
			return False
		return bool(self.__parents)

	@property
	def is_parent(self) -> bool:
		if not hasattr(self, r'_Node__children'):
			return False
		return bool(self.__children)

	def add_child(self, node):
		assert node is not None
		assert isinstance(node, Node)

		# make sure we tick the minimum boxes to be allowed to connect these two nodes
		if not self.has_type:
			raise Exception(rf"C++ node '{self.id}' must have a type before children can be added to it")
		if not node.has_type:
			raise Exception(rf"C++ node '{node.id}' must have a type before it can be added as a child")
		if node.type not in self.type.CONNECTS_TO:
			raise Exception(
				rf"C++ node '{node.id}' with type {self.type_name} is not allowed to connect to nodes of type {node.type_name}"
			)

		# lazy-initialize the storage
		if not hasattr(self, r'_Node__children'):
			self.__children = []
			self.__children_by_id = dict()
			self.__parents = []
			self.__parents_by_id = dict()
		if not hasattr(node, r'_Node__children'):
			node.__children = []
			node.__children_by_id = dict()
			node.__parents = []
			node.__parents_by_id = dict()

		# check that identity is unique
		if node.id in self.__children_by_id:
			other = self.__children_by_id[node.id]
			if id(node) == id(other):
				return
			raise Exception(rf"Two different C++ nodes seen with the same ID ('{node.id}')")

		self.__children.append(node)
		self.__children_by_id[node.id] = node
		node.__parents.append(self)
		node.__parents_by_id[self.id] = self



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
		for k, v in self.__nodes.items():
			yield (k, v)
