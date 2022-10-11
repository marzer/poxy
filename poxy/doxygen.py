#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Functions and classes for working with Doxygen.
"""

import subprocess
import itertools
from lxml import etree
from .utils import *
from . import graph

#=======================================================================================================================
# functions
#=======================================================================================================================



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



#=======================================================================================================================
# Doxyfile
#=======================================================================================================================



class Doxyfile(object):

	def __init__(self, input_path=None, output_path=None, cwd=None, logger=None, doxygen_path=None, flush_at_exit=True):
		self.__logger = logger
		self.__dirty = True
		self.__text = ''
		self.__autoflush = bool(flush_at_exit)

		# doxygen
		self.__cwd = Path.cwd() if cwd is None else coerce_path(cwd).resolve()
		assert_existing_directory(self.__cwd)
		self.__doxygen = r'doxygen' if doxygen_path is None else coerce_path(doxygen_path)

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
			result = subprocess.run([str(self.__doxygen), r'-s', r'-g', r'-'],
				check=True,
				capture_output=True,
				cwd=self.__cwd,
				encoding='utf-8')
			self.__text = result.stdout.strip()

		# simplify regex searches by ensuring there's always leading and trailing newlines
		self.__text = f'\n{self.__text}\n'

	def cleanup(self):
		if not self.__dirty:
			return
		if 1:
			log(self.__logger, rf'Invoking doxygen to clean doxyfile')
			result = subprocess.run([str(self.__doxygen), r'-s', r'-u', r'-'],
				check=True,
				capture_output=True,
				cwd=self.__cwd,
				encoding=r'utf-8',
				input=self.__text)
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
			text = text[m.end():]
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



#=======================================================================================================================
# XML <=> Graph
#=======================================================================================================================

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
	r'page': graph.Article
}
NODE_TYPES_TO_KINDS = {t: k for k, t in KINDS_TO_NODE_TYPES.items()}
COMPOUND_NODE_TYPES = {KINDS_TO_NODE_TYPES[c] for c in COMPOUNDS}
VERSION = r'1.9.5'



def _to_kind(node_type) -> str:
	if node_type is None:
		return None
	global NODE_TYPES_TO_KINDS
	assert node_type in NODE_TYPES_TO_KINDS
	return NODE_TYPES_TO_KINDS[node_type]



def _to_node_type(kind: str):
	if kind is None:
		return None
	global KINDS_TO_NODE_TYPES
	assert kind in KINDS_TO_NODE_TYPES
	return KINDS_TO_NODE_TYPES[kind]



def _parse_xml_file(g: graph.Graph, path: Path, parser: etree.XMLParser, log_func=None):
	assert g is not None
	assert path is not None
	assert parser is not None

	root = etree.fromstring(read_all_text_from_file(path, logger=log_func).encode(r'utf-8'), parser=parser)

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
			text = g.get_or_create_node(type=graph.Text)
			text.text = elem.text
			node.connect_to(text)
		# child <tags>
		for child_elem in elem:
			if child_elem.tag == r'para':
				para = g.get_or_create_node(type=graph.Paragraph)
				parse_structured_text(para, child_elem)
				node.connect_to(para)
			elif child_elem.tag == r'ref':
				ref = g.get_or_create_node(type=graph.Text)
				ref.text = child_elem.text
				ref.reference_id = child_elem.get(r'refid')
				node.connect_to(ref)
			else:
				raise Error(rf'Unknown <{elem.tag}> child element <{child_elem.tag}>')
			# text that came after the child <tag>
			if child_elem.tail:
				text = g.get_or_create_node(type=graph.Text)
				text.text = child_elem.tail
				node.connect_to(text)

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
		subnode = g.get_or_create_node(type=subnode_type)
		node.connect_to(subnode)
		parse_structured_text(subnode, subelem)

	def parse_brief(node, elem):
		parse_text_subnode(node, graph.BriefDescription, elem, r'briefdescription')

	def parse_detail(node, elem):
		parse_text_subnode(node, graph.DetailedDescription, elem, r'detaileddescription')

	def parse_initializer(node, elem):
		parse_text_subnode(node, graph.Initializer, elem, r'initializer')

	# <compound>
	# (these are doxygen's version of 'forward declarations')
	for compound in root.findall(r'compound'):
		node = g.get_or_create_node(id=compound.get(r'refid'), type=_to_node_type(compound.get(r'kind')))
		node.qualified_name = extract_qualified_name(compound)

		# <member>
		for member_elem in compound.findall(rf'member'):
			member_kind = member_elem.get(r'kind')
			if member_kind == r'enumvalue':
				continue
			member = g.get_or_create_node(id=member_elem.get(r'refid'), type=_to_node_type(member_kind))
			node.connect_to(member)
			# manually rebuild the fully-qualified name
			name = extract_subelement_text(member_elem, r'name')
			if name:
				if node.node_type is graph.Directory and member.node_type in (graph.Directory, graph.File):
					member.qualified_name = rf'{node.qualified_name}/{name}'
				elif (
					node.node_type not in (graph.Directory, graph.File)  #
					and member.node_type not in (graph.Directory, graph.File)
				):
					member.qualified_name = rf'{node.qualified_name}::{name}'

	# <compounddef>
	for compounddef in root.findall(r'compounddef'):
		node = g.get_or_create_node(id=compounddef.get(r'id'), type=_to_node_type(compounddef.get(r'kind')))
		node.qualified_name = extract_qualified_name(compounddef)
		node.access_level = compounddef.get(r'prot')

		def get_all_memberdefs(kind: str, *sectiondef_kinds):
			nonlocal compounddef
			memberdefs = [
				s for s in compounddef.findall(r'sectiondef') if (s.get(r'kind') in {kind, *sectiondef_kinds})
			]
			memberdefs = [s.findall(r'memberdef') for s in memberdefs]  # list of lists of memberdefs
			memberdefs = list(itertools.chain.from_iterable(memberdefs))  # list of memberdefs
			return [m for m in memberdefs if m.get(r'kind') == kind]  # matching memberdefs

		def get_all_type_memberdefs(kind: str):
			return get_all_memberdefs(kind, r'public-type', r'protected-type', r'private-type')

		def get_all_attrib_memberdefs(kind: str):
			return get_all_memberdefs(
				kind,  #
				r'var',
				r'public-static-attrib',
				r'protected-static-attrib',
				r'private-static-attrib',
				r'public-attrib',
				r'protected-attrib',
				r'private-attrib'
			)

		# enums
		for enum_elem in get_all_type_memberdefs(r'enum'):
			enum = g.get_or_create_node(id=enum_elem.get(r'id'), type=graph.Enum)
			enum.access_level = enum_elem.get(r'prot')
			enum.strong = enum_elem.get(r'strong')
			enum.static = enum_elem.get(r'static')
			enum.local_name = extract_subelement_text(enum_elem, r'name')
			enum.qualified_name = extract_qualified_name(enum_elem)
			parse_brief(enum, enum_elem)
			parse_detail(enum, enum_elem)
			node.connect_to(enum)
			for value_elem in enum_elem.findall(r'enumvalue'):
				value = g.get_or_create_node(id=value_elem.get(r'id'), type=graph.EnumValue)
				value.access_level = value_elem.get(r'prot')
				value.local_name = extract_subelement_text(value_elem, r'name')
				parse_brief(value, value_elem)
				parse_detail(value, value_elem)
				parse_initializer(value, value_elem)
				enum.connect_to(value)

		# vars
		for var_elem in get_all_attrib_memberdefs(r'variable'):
			var = g.get_or_create_node(id=var_elem.get(r'id'), type=graph.Variable)
			var.access_level = var_elem.get(r'prot')
			var.static = var_elem.get(r'static')
			var.constexpr = var_elem.get(r'constexpr')
			var.constinit = var_elem.get(r'constinit')
			var.mutable = var_elem.get(r'mutable')
			var.type = extract_subelement_text(var_elem, r'type')
			var.definition = extract_subelement_text(var_elem, r'definition')
			var.local_name = extract_subelement_text(var_elem, r'name')
			var.qualified_name = extract_qualified_name(var_elem)
			parse_brief(var, var_elem)
			parse_detail(var, var_elem)
			parse_initializer(var, var_elem)
			node.connect_to(var)

		# <inner(namespace|class|concept|file|dir)>
		for inner_suffix in (r'namespace', r'class', r'concept', r'dir', r'file'):
			for inner_elem in compounddef.findall(rf'inner{inner_suffix}'):
				inner = g.get_or_create_node(id=inner_elem.get(r'refid'))
				if inner_suffix == r'class':
					if inner.id.startswith(r'class'):
						inner.node_type = graph.Class
					elif inner.id.startswith(r'struct'):
						inner.node_type = graph.Struct
					elif inner.id.startswith(r'union'):
						inner.node_type = graph.Union
				else:
					inner.node_type = _to_node_type(inner_suffix)
				inner.qualified_name = inner_elem.text
				node.connect_to(inner)

	# deduce any missing qualified_names
	# for node in g(graph.Namespace, graph.Class, graph.Struct, graph.Union):



def read_graph_from_xml(folder, log_func=None) -> graph.Graph:
	assert folder is not None
	folder = coerce_path(folder).resolve()
	parser = etree.XMLParser(
		remove_blank_text=True,  #
		recover=True,
		remove_comments=True,
		ns_clean=True,
		encoding=r'utf-8'
	)
	g = graph.Graph()
	for path in get_all_files(folder, all=r"*.xml"):
		_parse_xml_file(g=g, path=path, parser=parser, log_func=log_func)
	return g



def write_graph_to_xml(g: graph.Graph, folder: Path, log_func=None):
	assert folder is not None
	folder.mkdir(exist_ok=True, parents=True)
	parser = etree.XMLParser(
		remove_blank_text=True,  #
		recover=True,
		remove_comments=False,
		ns_clean=True
	)

	global COMPOUNDS
	global COMPOUND_NODE_TYPES
	global KINDS_TO_NODE_TYPES
	global NODE_TYPES_TO_KINDS
	global VERSION

	def make_text_subnode(elem, subelem_tag: str, node: graph.Node, subnode_type):
		assert node is not None
		assert elem is not None
		assert subelem_tag is not None
		assert subnode_type is not None
		subelem = etree.SubElement(elem, subelem_tag)
		subelem.text = r''
		if subnode_type not in node:
			return
		text = [n for n in node(subnode_type)]  # list of BriefDescription
		text = [[i for i in n(graph.Paragraph, graph.Text)] for n in text]  # list of lists of Text/Paragraph
		text = list(itertools.chain.from_iterable(text))  # list of Text/Paragraph
		if not text:
			return
		# all the ones at the start that are just plain text get
		# concatenated and set as the main text of the root subelement
		while text and text[0].node_type is graph.Text and not text[0].reference_id:
			subelem.text = subelem.text + text[0].text
			text.pop(0)
		# otherwise we need to loop through and make paragraphs/references
		prev = None
		while text:
			if text[0].node_type is graph.Paragraph:
				para = etree.SubElement(subelem, rf'para')
				para.text = text[0].text
				para_children = [n for n in text[0](graph.Text)]
				text.pop(0)
				prev = para
				while para_children and not para_children[0].reference_id:
					para.text = para.text + para_children[0].text
					para_children.pop(0)
				para_prev = None
				while para_children:
					if para_children[0].reference_id:
						para_prev = etree.SubElement(subelem, rf'ref', attrib={r'refid': para_children[0].reference_id})
						para_prev.text = para_children[0].text
						para_children.pop(0)
					else:
						assert para_prev is not None
						while para_children and not para_children[0].reference_id:
							para_prev.tail = para_prev.tail + para_children[0].text
							para_children.pop(0)
			elif text[0].reference_id:
				prev = etree.SubElement(subelem, rf'ref', attrib={r'refid': text[0].reference_id})
				prev.text = text[0].text
				text.pop(0)
			else:
				assert prev is not None
				while text and text[0].node_type is graph.Text and not text[0].reference_id:
					prev.tail = prev.tail + text[0].text
					text.pop(0)

	def make_brief(elem, node):
		make_text_subnode(elem, r'briefdescription', node, graph.BriefDescription)

	def make_detail(elem, node):
		make_text_subnode(elem, r'detaileddescription', node, graph.DetailedDescription)

	def make_initializer(elem, node):
		make_text_subnode(elem, r'initializer', node, graph.Initializer)

	# serialize the compound nodes
	for node in g(*COMPOUND_NODE_TYPES):
		if not node:
			continue
		assert node.qualified_name

		kind = _to_kind(node.node_type)
		assert kind in COMPOUNDS

		path = Path(folder, rf'{node.id}.xml')
		xml = etree.ElementTree(
			etree.XML(
			rf'''<doxygen
						xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
						xsi:noNamespaceSchemaLocation="compound.xsd"
						version="{VERSION}"
						xml:lang="en-US">
					<!-- This file was created by Poxy - https://github.com/marzer/poxy -->
					<compounddef id="{node.id}" kind="{kind}" language="C++">
						<compoundname>{node.qualified_name}</compoundname>
					</compounddef>
				</doxygen>''',
			parser=parser
			)
		)

		# create the root <compounddef>
		compounddef = xml.getroot().find(r'compounddef')
		if node.node_type not in (graph.Namespace, graph.Directory, graph.File):
			compounddef.set(r'prot', str(Prot(node.access_level)))

		# <includes>
		if node.node_type in (graph.Class, graph.Struct, graph.Union):
			files = [f for f in g(graph.File) if (f and f is not node and node in f)]
			for f in files:
				assert f.qualified_name
				elem = etree.SubElement(compounddef, rf'includes', attrib={r'local': r'no'})
				elem.text = f.qualified_name

		# add the inners
		for inner_node in node(
			graph.Namespace, graph.Class, graph.Struct, graph.Union, graph.Concept, graph.Directory, graph.File
		):
			if not inner_node:
				continue
			assert inner_node.qualified_name

			kind = NODE_TYPES_TO_KINDS[inner_node.node_type]
			if inner_node.node_type in (graph.Struct, graph.Union):
				kind = r'class'
			inner_elem = etree.SubElement(compounddef, rf'inner{kind}', attrib={r'refid': inner_node.id})
			if node.node_type not in (graph.Namespace, graph.Directory, graph.File):
				inner_elem.set(r'prot', str(Prot(inner_node.access_level)))
			inner_elem.text = inner_node.qualified_name

		# create all the <sectiondefs>
		# (empty ones will be deleted at the end)
		sectiondefs = (
			# namespace/file sections:
			r'enum',
			r'var',
			# class/struct/union sections:
			r'public-type',
			r'protected-type',
			r'private-type',
			r'public-static-attrib',
			r'protected-static-attrib',
			r'private-static-attrib',
			r'public-attrib',
			r'protected-attrib',
			r'private-attrib'
		)
		sectiondefs = {k: etree.SubElement(compounddef, r'sectiondef', attrib={r'kind': k}) for k in sectiondefs}

		# enums
		for enum in node(graph.Enum):
			section = r'enum'
			if node.node_type in (graph.Class, graph.Struct, graph.Union):
				section = rf'{Prot(enum.access_level)}-type'
			enum_elem = etree.SubElement(
				sectiondefs[section],
				rf'memberdef',
				attrib={
				r'id': enum.id,
				r'kind': r'enum',
				r'static': str(Bool(enum.static)),
				r'strong': str(Bool(enum.strong)),
				r'prot': str(Prot(enum.access_level))
				}
			)
			etree.SubElement(enum_elem, r'type').text = enum.type
			etree.SubElement(enum_elem, r'name').text = enum.local_name
			etree.SubElement(enum_elem, r'qualified_name').text = enum.qualified_name
			make_brief(enum_elem, enum)
			make_detail(enum_elem, enum)
			etree.SubElement(enum_elem, r'inbodydescription').text = r''  # todo
			for value in enum(graph.EnumValue):
				value_elem = etree.SubElement(
					enum_elem, rf'enumvalue', attrib={
					r'id': value.id,
					r'prot': str(Prot(value.access_level))
					}
				)
				etree.SubElement(value_elem, r'name').text = value.local_name
				make_brief(value_elem, value)
				make_detail(value_elem, value)
				make_initializer(value_elem, value)

		# variables
		for var in node(graph.Variable):
			section = r'var'
			if node.node_type in (graph.Class, graph.Struct, graph.Union):
				section = rf'{Prot(var.access_level)}-{"static-" if var.static else ""}attrib'
			var_elem = etree.SubElement(
				sectiondefs[section],
				rf'memberdef',
				attrib={
				r'id': var.id,
				r'kind': r'variable',
				r'prot': str(Prot(var.access_level)),
				r'static': str(Bool(var.static)),
				r'constexpr': str(Bool(var.constexpr)),
				r'constinit': str(Bool(var.constinit)),
				r'mutable': str(Bool(var.strong)),
				}
			)
			etree.SubElement(var_elem, r'type').text = var.type
			etree.SubElement(var_elem, r'definition').text = var.definition
			etree.SubElement(var_elem, r'argsstring')
			etree.SubElement(var_elem, r'name').text = var.local_name
			etree.SubElement(var_elem, r'qualified_name').text = var.qualified_name
			make_brief(var_elem, var)
			make_detail(var_elem, var)
			make_initializer(var_elem, var)
			etree.SubElement(var_elem, r'inbodydescription').text = r''  # todo
			etree.SubElement(var_elem, r'location')

		# <listofallmembers>
		if node.node_type in (graph.Class, graph.Struct, graph.Union):
			listofallmembers = etree.SubElement(compounddef, rf'listofallmembers')

		# prune empty <sectiondefs>
		for _, elem in sectiondefs.items():
			if not len(elem):
				elem.getparent().remove(elem)

		if log_func:
			log_func(rf'Writing {path}')
		xml.write(
			str(path),  #
			encoding=r'utf-8',
			pretty_print=True,
			xml_declaration=True,
			standalone=False
		)
