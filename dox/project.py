#!/usr/bin/env python3
# This file is a part of marzer/dox and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/dox/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

try:
	from dox.utils import *
except:
	from utils import *

import os
import copy
import pytomlpp
import threading
import json
import datetime



#=======================================================================================================================
# PROJECT CONTEXT
#=======================================================================================================================

class _Defaults(object):
	enums = {
		r'(?:std::)?ios(?:_base)?::(?:app|binary|in|out|trunc|ate)'
	}
	namespaces = {
		r'std',
		r'std::chrono',
		r'std::execution',
		r'std::filesystem',
		r'std::(?:literals::)?(?:chrono|complex|string|string_view)_literals',
		r'std::literals',
		r'std::numbers',
		r'std::ranges',
		r'std::this_thread'
	}
	inline_namespaces = {
		r'std::(?:literals::)?(?:chrono|complex|string|string_view)_literals'
	}
	types = {
		#------ standard/built-in types
		r'__(?:float|fp)[0-9]{1,3}',
		r'__m[0-9]{1,3}[di]?',
		r'_Float[0-9]{1,3}',
		r'(?:std::)?(?:basic_)?ios(?:_base)?',
		r'(?:std::)?(?:const_)?(?:reverse_)?iterator',
		r'(?:std::)?(?:shared_|recursive_)?(?:timed_)?mutex',
		r'(?:std::)?array',
		r'(?:std::)?byte',
		r'(?:std::)?exception',
		r'(?:std::)?lock_guard',
		r'(?:std::)?optional',
		r'(?:std::)?pair',
		r'(?:std::)?span',
		r'(?:std::)?streamsize',
		r'(?:std::)?string(?:_view)?',
		r'(?:std::)?tuple',
		r'(?:std::)?vector',
		r'(?:std::)?(?:unique|shared|scoped)_(?:ptr|lock)',
		r'(?:std::)?(?:unordered_)?(?:map|set)',
		r'[a-zA-Z_][a-zA-Z_0-9]*_t(?:ype(?:def)?|raits)?',
		r'bool',
		r'char',
		r'double',
		r'float',
		r'int',
		r'long',
		r'short',
		r'signed',
		r'unsigned',
		r'(?:std::)?w?(?:(?:(?:i|o)?(?:string|f))|i|o|io)stream',
		#------ documentation-only types
		r'[T-V][0-9]',
		r'Foo',
		r'Bar',
		r'[Vv]ec(?:tor)?[1-4][hifd]?',
		r'[Mm]at(?:rix)?[1-4](?:[xX][1-4])?[hifd]?'
	}
	defines = {
		r'DOXYGEN' :					1,
		r'__DOXYGEN__' :				1,
		r'__doxygen__' :				1,
		r'__DOX__' :					1,
		r'__dox__' :					1,
		r'__has_include(...)' :			0,
		r'__has_attribute(...)' :		0,
		r'__has_cpp_attribute(...)' :	999999,
	}
	cpp_builtin_defines = {
		1998 : {
			r'__cplusplus' 		: r'199711L',
			r'__cpp_rtti' 		: 199711,
			r'__cpp_exceptions' : 199711
		},

		2003 : dict(), # apparently?

		2011 : {
			r'__cplusplus'						: r'201103L',
			r'__cpp_unicode_characters'			: 200704,
			r'__cpp_raw_strings'				: 200710,
			r'__cpp_unicode_literals'			: 200710,
			r'__cpp_user_defined_literals'		: 200809,
			r'__cpp_threadsafe_static_init'		: 200806,
			r'__cpp_lambdas'					: 200907,
			r'__cpp_constexpr'					: 200704,
			r'__cpp_range_based_for'			: 200907,
			r'__cpp_static_assert'				: 200410,
			r'__cpp_decltype'					: 200707,
			r'__cpp_attributes'					: 200809,
			r'__cpp_rvalue_references'			: 200610,
			r'__cpp_variadic_templates'			: 200704,
			r'__cpp_initializer_lists'			: 200806,
			r'__cpp_delegating_constructors'	: 200604,
			r'__cpp_nsdmi'						: 200809,
			r'__cpp_inheriting_constructors'	: 200802,
			r'__cpp_ref_qualifiers'				: 200710,
			r'__cpp_alias_templates'			: 200704
		},

		2014 : {
			r'__cplusplus'								: r'201402L',
			r'__cpp_binary_literals'					: 201304,
			r'__cpp_init_captures'						: 201304,
			r'__cpp_generic_lambdas'					: 201304,
			r'__cpp_sized_deallocation'					: 201309,
			r'__cpp_constexpr'							: 201304,
			r'__cpp_decltype_auto'						: 201304,
			r'__cpp_return_type_deduction'				: 201304,
			r'__cpp_aggregate_nsdmi'					: 201304,
			r'__cpp_variable_templates'					: 201304,
			r'__cpp_lib_integer_sequence'				: 201304,
			r'__cpp_lib_exchange_function'				: 201304,
			r'__cpp_lib_tuples_by_type'					: 201304,
			r'__cpp_lib_tuple_element_t'				: 201402,
			r'__cpp_lib_make_unique'					: 201304,
			r'__cpp_lib_transparent_operators'			: 201210,
			r'__cpp_lib_integral_constant_callable'		: 201304,
			r'__cpp_lib_transformation_trait_aliases'	: 201304,
			r'__cpp_lib_result_of_sfinae'				: 201210,
			r'__cpp_lib_is_final'						: 201402,
			r'__cpp_lib_is_null_pointer'				: 201309,
			r'__cpp_lib_chrono_udls'					: 201304,
			r'__cpp_lib_string_udls'					: 201304,
			r'__cpp_lib_generic_associative_lookup'		: 201304,
			r'__cpp_lib_null_iterators'					: 201304,
			r'__cpp_lib_make_reverse_iterator'			: 201402,
			r'__cpp_lib_robust_nonmodifying_seq_ops'	: 201304,
			r'__cpp_lib_complex_udls'					: 201309,
			r'__cpp_lib_quoted_string_io'				: 201304,
			r'__cpp_lib_shared_timed_mutex'				: 201402,
		},

		2017 : {
			r'__cplusplus'									: r'201703L',
			r'__cpp_hex_float'								: 201603,
			r'__cpp_inline_variables'						: 201606,
			r'__cpp_aligned_new'							: 201606,
			r'__cpp_guaranteed_copy_elision'				: 201606,
			r'__cpp_noexcept_function_type'					: 201510,
			r'__cpp_fold_expressions'						: 201603,
			r'__cpp_capture_star_this'						: 201603,
			r'__cpp_constexpr'								: 201603,
			r'__cpp_if_constexpr'							: 201606,
			r'__cpp_range_based_for'						: 201603,
			r'__cpp_static_assert'							: 201411,
			r'__cpp_deduction_guides'						: 201703,
			r'__cpp_nontype_template_parameter_auto'		: 201606,
			r'__cpp_namespace_attributes'					: 201411,
			r'__cpp_enumerator_attributes'					: 201411,
			r'__cpp_inheriting_constructors'				: 201511,
			r'__cpp_variadic_using'							: 201611,
			r'__cpp_structured_bindings'					: 201606,
			r'__cpp_aggregate_bases'						: 201603,
			r'__cpp_nontype_template_args'					: 201411,
			r'__cpp_template_template_args'					: 201611,
			r'__cpp_lib_byte'								: 201603,
			r'__cpp_lib_hardware_interference_size'			: 201703,
			r'__cpp_lib_launder'							: 201606,
			r'__cpp_lib_uncaught_exceptions'				: 201411,
			r'__cpp_lib_as_const'							: 201510,
			r'__cpp_lib_make_from_tuple'					: 201606,
			r'__cpp_lib_apply'								: 201603,
			r'__cpp_lib_optional'							: 201606,
			r'__cpp_lib_variant'							: 201606,
			r'__cpp_lib_any'								: 201606,
			r'__cpp_lib_addressof_constexpr'				: 201603,
			r'__cpp_lib_raw_memory_algorithms'				: 201606,
			r'__cpp_lib_transparent_operators'				: 201510,
			r'__cpp_lib_enable_shared_from_this'			: 201603,
			r'__cpp_lib_shared_ptr_weak_type'				: 201606,
			r'__cpp_lib_shared_ptr_arrays'					: 201611,
			r'__cpp_lib_memory_resource'					: 201603,
			r'__cpp_lib_boyer_moore_searcher'				: 201603,
			r'__cpp_lib_invoke'								: 201411,
			r'__cpp_lib_not_fn'								: 201603,
			r'__cpp_lib_void_t'								: 201411,
			r'__cpp_lib_bool_constant'						: 201505,
			r'__cpp_lib_type_trait_variable_templates'		: 201510,
			r'__cpp_lib_logical_traits'						: 201510,
			r'__cpp_lib_is_swappable'						: 201603,
			r'__cpp_lib_is_invocable'						: 201703,
			r'__cpp_lib_has_unique_object_representations'	: 201606,
			r'__cpp_lib_is_aggregate'						: 201703,
			r'__cpp_lib_chrono'								: 201611,
			r'__cpp_lib_execution'							: 201603,
			r'__cpp_lib_parallel_algorithm'					: 201603,
			r'__cpp_lib_to_chars'							: 201611,
			r'__cpp_lib_string_view'						: 201606,
			r'__cpp_lib_allocator_traits_is_always_equal'	: 201411,
			r'__cpp_lib_incomplete_container_elements'		: 201505,
			r'__cpp_lib_map_try_emplace'					: 201411,
			r'__cpp_lib_unordered_map_try_emplace'			: 201411,
			r'__cpp_lib_node_extract'						: 201606,
			r'__cpp_lib_array_constexpr'					: 201603,
			r'__cpp_lib_nonmember_container_access'			: 201411,
			r'__cpp_lib_sample'								: 201603,
			r'__cpp_lib_clamp'								: 201603,
			r'__cpp_lib_gcd_lcm'							: 201606,
			r'__cpp_lib_hypot'								: 201603,
			r'__cpp_lib_math_special_functions'				: 201603,
			r'__cpp_lib_filesystem'							: 201703,
			r'__cpp_lib_atomic_is_always_lock_free'			: 201603,
			r'__cpp_lib_shared_mutex'						: 201505,
			r'__cpp_lib_scoped_lock'						: 201703,
		},

		2020 : {
			r'__cplusplus'								: r'202002L',
			r'__cpp_aggregate_paren_init'				: 201902,
			r'__cpp_char8_t'							: 201811,
			r'__cpp_concepts'							: 201907,
			r'__cpp_conditional_explicit'				: 201806,
			r'__cpp_consteval'							: 201811,
			r'__cpp_constexpr'							: 201907,
			r'__cpp_constexpr_dynamic_alloc'			: 201907,
			r'__cpp_constexpr_in_decltype'				: 201711,
			r'__cpp_constinit'							: 201907,
			r'__cpp_deduction_guides'					: 201907,
			r'__cpp_designated_initializers'			: 201707,
			r'__cpp_generic_lambdas'					: 201707,
			r'__cpp_impl_coroutine'						: 201902,
			r'__cpp_impl_destroying_delete'				: 201806,
			r'__cpp_impl_three_way_comparison'			: 201907,
			r'__cpp_init_captures'						: 201803,
			r'__cpp_lib_array_constexpr'				: 201811,
			r'__cpp_lib_assume_aligned'					: 201811,
			r'__cpp_lib_atomic_flag_test'				: 201907,
			r'__cpp_lib_atomic_float'					: 201711,
			r'__cpp_lib_atomic_lock_free_type_aliases'	: 201907,
			r'__cpp_lib_atomic_ref'						: 201806,
			r'__cpp_lib_atomic_shared_ptr'				: 201711,
			r'__cpp_lib_atomic_value_initialization'	: 201911,
			r'__cpp_lib_atomic_wait'					: 201907,
			r'__cpp_lib_barrier'						: 201907,
			r'__cpp_lib_bind_front'						: 201907,
			r'__cpp_lib_bit_cast'						: 201806,
			r'__cpp_lib_bitops'							: 201907,
			r'__cpp_lib_bounded_array_traits'			: 201902,
			r'__cpp_lib_char8_t'						: 201907,
			r'__cpp_lib_chrono'							: 201907,
			r'__cpp_lib_concepts'						: 202002,
			r'__cpp_lib_constexpr_algorithms'			: 201806,
			r'__cpp_lib_constexpr_complex'				: 201711,
			r'__cpp_lib_constexpr_dynamic_alloc'		: 201907,
			r'__cpp_lib_constexpr_functional'			: 201907,
			r'__cpp_lib_constexpr_iterator'				: 201811,
			r'__cpp_lib_constexpr_memory'				: 201811,
			r'__cpp_lib_constexpr_numeric'				: 201911,
			r'__cpp_lib_constexpr_string'				: 201907,
			r'__cpp_lib_constexpr_string_view'			: 201811,
			r'__cpp_lib_constexpr_tuple'				: 201811,
			r'__cpp_lib_constexpr_utility'				: 201811,
			r'__cpp_lib_constexpr_vector'				: 201907,
			r'__cpp_lib_coroutine'						: 201902,
			r'__cpp_lib_destroying_delete'				: 201806,
			r'__cpp_lib_endian'							: 201907,
			r'__cpp_lib_erase_if'						: 202002,
			r'__cpp_lib_execution'						: 201902,
			r'__cpp_lib_format'							: 201907,
			r'__cpp_lib_generic_unordered_lookup'		: 201811,
			r'__cpp_lib_int_pow2'						: 202002,
			r'__cpp_lib_integer_comparison_functions'	: 202002,
			r'__cpp_lib_interpolate'					: 201902,
			r'__cpp_lib_is_constant_evaluated'			: 201811,
			r'__cpp_lib_is_layout_compatible'			: 201907,
			r'__cpp_lib_is_nothrow_convertible'			: 201806,
			r'__cpp_lib_is_pointer_interconvertible'	: 201907,
			r'__cpp_lib_jthread'						: 201911,
			r'__cpp_lib_latch'							: 201907,
			r'__cpp_lib_list_remove_return_type'		: 201806,
			r'__cpp_lib_math_constants'					: 201907,
			r'__cpp_lib_polymorphic_allocator'			: 201902,
			r'__cpp_lib_ranges'							: 201911,
			r'__cpp_lib_remove_cvref'					: 201711,
			r'__cpp_lib_semaphore'						: 201907,
			r'__cpp_lib_shared_ptr_arrays'				: 201707,
			r'__cpp_lib_shift'							: 201806,
			r'__cpp_lib_smart_ptr_for_overwrite'		: 202002,
			r'__cpp_lib_source_location'				: 201907,
			r'__cpp_lib_span'							: 202002,
			r'__cpp_lib_ssize'							: 201902,
			r'__cpp_lib_starts_ends_with'				: 201711,
			r'__cpp_lib_string_view'					: 201803,
			r'__cpp_lib_syncbuf'						: 201803,
			r'__cpp_lib_three_way_comparison'			: 201907,
			r'__cpp_lib_to_address'						: 201711,
			r'__cpp_lib_to_array'						: 201907,
			r'__cpp_lib_type_identity'					: 201806,
			r'__cpp_lib_unwrap_ref'						: 201811,
			r'__cpp_modules'							: 201907,
			r'__cpp_nontype_template_args'				: 201911,
			r'__cpp_using_enum'							: 201907,
		},

		2023 : dict(),

		2026 : dict(),

		2029 : dict(),
	}
	# syntax highlighting only
	macros = {
			# standard builtins:
			r'__cplusplus(?:_cli|_winrt)?',
			r'__cpp_[a-zA-Z_]+?',
			r'__has_(?:(?:cpp_)?attribute|include)',
			r'assert',
			r'offsetof',
			# msvc:
			r'__(?:'
				+ r'FILE|LINE|DATE|TIME|COUNTER'
				+ r'|STDC(?:_HOSTED|_NO_ATOMICS|_NO_COMPLEX|_NO_THREADS|_NO_VLA|_VERSION|_THREADS)?'
				+ r'|STDCPP_DEFAULT_NEW_ALIGNMENT|INTELLISENSE|ATOM'
				+ r'|AVX(?:2|512(?:BW|CD|DQ|F|VL)?)?|FUNC(?:TION|DNAME|SIG)'
				+ r')__',
			r'_M_(?:AMD64|ARM(?:_ARMV7VE|_FP|64)?|X64|CEE(?:_PURE|_SAFE)?|FP_(?:EXCEPT|FAST|PRECISE|STRICT)|IX86(?:_FP)?)',
			r'__CLR_VER|_CHAR_UNSIGNED|_CONTROL_FLOW_GUARD|_CPP(?:RTTI|UNWIND)|_DEBUG|_INTEGRAL_MAX_BITS|_ISO_VOLATILE',
			r'_KERNEL_MODE|_MANAGED|_MSC_(?:BUILD|EXTENSIONS|(?:FULL_)?VER)|NDEBUG|_MSC(?:_FULL)_VER|_MSVC_LANG|_WIN(?:32|64)'
	}
	string_literals = {
		r'sv?'
	}
	numeric_literals = set()
	autolinks = {
		# builtins
		r'const_cast' : r'https://en.cppreference.com/w/cpp/language/const_cast',
		r'dynamic_cast' : r'https://en.cppreference.com/w/cpp/language/dynamic_cast',
		r'reinterpret_cast' : r'https://en.cppreference.com/w/cpp/language/reinterpret_cast',
		r'static_cast' : r'https://en.cppreference.com/w/cpp/language/static_cast',
		r'(?:_Float|__fp)16s?' : r'https://gcc.gnu.org/onlinedocs/gcc/Half-Precision.html',
		r'(?:_Float|__float)(128|80)s?' : r'https://gcc.gnu.org/onlinedocs/gcc/Floating-Types.html',
		r'(?:wchar|char(?:8|16|32))_ts?' : r'https://en.cppreference.com/w/cpp/language/types#Character_types',
		r'(?:__cplusplus|__(?:FILE|LINE|DATE|TIME|STDC_HOSTED|STDCPP_DEFAULT_NEW_ALIGNMENT)__)'
			: r'https://en.cppreference.com/w/cpp/preprocessor/replace',
		# standard library
		r'std::assume_aligned(?:\(\))?' : r'https://en.cppreference.com/w/cpp/memory/assume_aligned',
		r'(?:std::)?nullptr_t' : r'https://en.cppreference.com/w/cpp/types/nullptr_t',
		r'(?:std::)?ptrdiff_t' : r'https://en.cppreference.com/w/cpp/types/ptrdiff_t',
		r'(?:std::)?size_t' : r'https://en.cppreference.com/w/cpp/types/size_t',
		r'(?:std::)?u?int(?:_fast|_least)?(?:8|16|32|64)_ts?' : r'https://en.cppreference.com/w/cpp/types/integer',
		r'(?:std::)?u?int(?:max|ptr)_t' : r'https://en.cppreference.com/w/cpp/types/integer',
		r'\s(?:<|&lt;)fstream(?:>|&gt;)' : r'https://en.cppreference.com/w/cpp/header/fstream',
		r'\s(?:<|&lt;)iosfwd(?:>|&gt;)' : r'https://en.cppreference.com/w/cpp/header/iosfwd',
		r'\s(?:<|&lt;)iostream(?:>|&gt;)' : r'https://en.cppreference.com/w/cpp/header/iostream',
		r'\s(?:<|&lt;)sstream(?:>|&gt;)' : r'https://en.cppreference.com/w/cpp/header/sstream',
		r'\s(?:<|&lt;)string(?:>|&gt;)' : r'https://en.cppreference.com/w/cpp/header/string',
		r'\s(?:<|&lt;)string_view(?:>|&gt;)' : r'https://en.cppreference.com/w/cpp/header/string_view',
		r'std::(?:basic_|w)?fstreams?' : r'https://en.cppreference.com/w/cpp/io/basic_fstream',
		r'std::(?:basic_|w)?ifstreams?' : r'https://en.cppreference.com/w/cpp/io/basic_ifstream',
		r'std::(?:basic_|w)?iostreams?' : r'https://en.cppreference.com/w/cpp/io/basic_iostream',
		r'std::(?:basic_|w)?istreams?' : r'https://en.cppreference.com/w/cpp/io/basic_istream',
		r'std::(?:basic_|w)?istringstreams?' : r'https://en.cppreference.com/w/cpp/io/basic_istringstream',
		r'std::(?:basic_|w)?ofstreams?' : r'https://en.cppreference.com/w/cpp/io/basic_ofstream',
		r'std::(?:basic_|w)?ostreams?' : r'https://en.cppreference.com/w/cpp/io/basic_ostream',
		r'std::(?:basic_|w)?ostringstreams?' : r'https://en.cppreference.com/w/cpp/io/basic_ostringstream',
		r'std::(?:basic_|w)?stringstreams?' : r'https://en.cppreference.com/w/cpp/io/basic_stringstream',
		r'std::(?:basic_|w|u(?:8|16|32))?string_views?' : r'https://en.cppreference.com/w/cpp/string/basic_string_view',
		r'std::(?:basic_|w|u(?:8|16|32))?strings?' : r'https://en.cppreference.com/w/cpp/string/basic_string',
		r'std::[fl]?abs[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/abs',
		r'std::acos[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/acos',
		r'std::add_[lr]value_reference(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/add_reference',
		r'std::add_(?:cv|const|volatile)(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/add_cv',
		r'std::add_pointer(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/add_pointer',
		r'std::allocators?' : r'https://en.cppreference.com/w/cpp/memory/allocator',
		r'std::arrays?' : r'https://en.cppreference.com/w/cpp/container/array',
		r'std::as_(writable_)?bytes(?:\(\))?' : r'https://en.cppreference.com/w/cpp/container/span/as_bytes',
		r'std::asin[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/asin',
		r'std::atan2[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/atan2',
		r'std::atan[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/atan',
		r'std::bad_alloc' : r'https://en.cppreference.com/w/cpp/memory/new/bad_alloc',
		r'std::basic_ios' : r'https://en.cppreference.com/w/cpp/io/basic_ios',
		r'std::bit_cast(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/bit_cast',
		r'std::bit_ceil(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/bit_ceil',
		r'std::bit_floor(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/bit_floor',
		r'std::bit_width(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/bit_width',
		r'std::bytes?' : r'https://en.cppreference.com/w/cpp/types/byte',
		r'std::ceil[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/ceil',
		r'std::char_traits' : r'https://en.cppreference.com/w/cpp/string/char_traits',
		r'std::chrono::durations?' : r'https://en.cppreference.com/w/cpp/chrono/duration',
		r'std::clamp(?:\(\))?' : r'https://en.cppreference.com/w/cpp/algorithm/clamp',
		r'std::conditional(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/conditional',
		r'std::cos[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/cos',
		r'std::countl_one(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/countl_one',
		r'std::countl_zero(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/countl_zero',
		r'std::countr_one(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/countr_one',
		r'std::countr_zero(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/countr_zero',
		r'std::enable_if(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/enable_if',
		r'std::exceptions?' : r'https://en.cppreference.com/w/cpp/error/exception',
		r'std::floor[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/floor',
		r'std::fpos' : r'https://en.cppreference.com/w/cpp/io/fpos',
		r'std::has_single_bit(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/has_single_bit',
		r'std::hash' : r'https://en.cppreference.com/w/cpp/utility/hash',
		r'std::initializer_lists?' : r'https://en.cppreference.com/w/cpp/utility/initializer_list',
		r'std::integral_constants?' : r'https://en.cppreference.com/w/cpp/types/integral_constant',
		r'std::ios(?:_base)?' : r'https://en.cppreference.com/w/cpp/io/ios_base',
		r'std::is_(?:nothrow_)?convertible(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_convertible',
		r'std::is_(?:nothrow_)?invocable(?:_r)?' : r'https://en.cppreference.com/w/cpp/types/is_invocable',
		r'std::is_base_of(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_base_of',
		r'std::is_constant_evaluated(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/is_constant_evaluated',
		r'std::is_enum(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_enum',
		r'std::is_floating_point(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_floating_point',
		r'std::is_integral(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_integral',
		r'std::is_pointer(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_pointer',
		r'std::is_reference(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_reference',
		r'std::is_same(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_same',
		r'std::is_signed(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_signed',
		r'std::is_unsigned(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_unsigned',
		r'std::is_void(?:_v)?' : r'https://en.cppreference.com/w/cpp/types/is_void',
		r'std::launder(?:\(\))?' : r'https://en.cppreference.com/w/cpp/utility/launder',
		r'std::lerp(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/lerp',
		r'std::maps?' : r'https://en.cppreference.com/w/cpp/container/map',
		r'std::max(?:\(\))?' : r'https://en.cppreference.com/w/cpp/algorithm/max',
		r'std::min(?:\(\))?' : r'https://en.cppreference.com/w/cpp/algorithm/min',
		r'std::numeric_limits::min(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/min',
		r'std::numeric_limits::lowest(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/lowest',
		r'std::numeric_limits::max(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/max',
		r'std::numeric_limits::epsilon(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/epsilon',
		r'std::numeric_limits::round_error(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/round_error',
		r'std::numeric_limits::infinity(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/infinity',
		r'std::numeric_limits::quiet_NaN(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/quiet_NaN',
		r'std::numeric_limits::signaling_NaN(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/signaling_NaN',
		r'std::numeric_limits::denorm_min(?:\(\))?' : r'https://en.cppreference.com/w/cpp/types/numeric_limits/denorm_min',
		r'std::numeric_limits' : r'https://en.cppreference.com/w/cpp/types/numeric_limits',
		r'std::optionals?' : r'https://en.cppreference.com/w/cpp/utility/optional',
		r'std::pairs?' : r'https://en.cppreference.com/w/cpp/utility/pair',
		r'std::popcount(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/popcount',
		r'std::remove_cv(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/remove_cv',
		r'std::remove_reference(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/remove_reference',
		r'std::reverse_iterator' : r'https://en.cppreference.com/w/cpp/iterator/reverse_iterator',
		r'std::runtime_errors?' : r'https://en.cppreference.com/w/cpp/error/runtime_error',
		r'std::sets?' : r'https://en.cppreference.com/w/cpp/container/set',
		r'std::shared_ptrs?' : r'https://en.cppreference.com/w/cpp/memory/shared_ptr',
		r'std::sin[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/sin',
		r'std::spans?' : r'https://en.cppreference.com/w/cpp/container/span',
		r'std::sqrt[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/sqrt',
		r'std::tan[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/tan',
		r'std::to_address(?:\(\))?' : r'https://en.cppreference.com/w/cpp/memory/to_address',
		r'std::(?:true|false)_type' : r'https://en.cppreference.com/w/cpp/types/integral_constant',
		r'std::trunc[fl]?(?:\(\))?' : r'https://en.cppreference.com/w/cpp/numeric/math/trunc',
		r'std::tuple_element(?:_t)?' : r'https://en.cppreference.com/w/cpp/utility/tuple/tuple_element',
		r'std::tuple_size(?:_v)?' : r'https://en.cppreference.com/w/cpp/utility/tuple/tuple_size',
		r'std::tuples?' : r'https://en.cppreference.com/w/cpp/utility/tuple',
		r'std::type_identity(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/type_identity',
		r'std::underlying_type(?:_t)?' : r'https://en.cppreference.com/w/cpp/types/underlying_type',
		r'std::unique_ptrs?' : r'https://en.cppreference.com/w/cpp/memory/unique_ptr',
		r'std::unordered_maps?' : r'https://en.cppreference.com/w/cpp/container/unordered_map',
		r'std::unordered_sets?' : r'https://en.cppreference.com/w/cpp/container/unordered_set',
		r'std::vectors?' : r'https://en.cppreference.com/w/cpp/container/vector',
		r'std::atomic[a-zA-Z_0-9]*' : r'https://en.cppreference.com/w/cpp/atomic/atomic',
		r'(?:Legacy)?InputIterators?' : r'https://en.cppreference.com/w/cpp/named_req/InputIterator',
		r'(?:Legacy)?OutputIterators?' : r'https://en.cppreference.com/w/cpp/named_req/OutputIterator',
		r'(?:Legacy)?ForwardIterators?' : r'https://en.cppreference.com/w/cpp/named_req/ForwardIterator',
		r'(?:Legacy)?BidirectionalIterators?' : r'https://en.cppreference.com/w/cpp/named_req/BidirectionalIterator',
		r'(?:Legacy)?RandomAccessIterators?' : r'https://en.cppreference.com/w/cpp/named_req/RandomAccessIterator',
		r'(?:Legacy)?ContiguousIterators?' : r'https://en.cppreference.com/w/cpp/named_req/ContiguousIterator',
		# windows
		r'(?:L?P)?(?:'
			+ r'D?WORD(?:32|64|_PTR)?|HANDLE|HMODULE|BOOL(?:EAN)?'
			+ r'|U?SHORT|U?LONG|U?INT(?:8|16|32|64)?'
			+ r'|BYTE|VOID|C[WT]?STR'
			+ r')'
			: r'https://docs.microsoft.com/en-us/windows/desktop/winprog/windows-data-types',
		r'__INTELLISENSE__|_MSC(?:_FULL)_VER|_MSVC_LANG|_WIN(?:32|64)'
			: r'https://docs.microsoft.com/en-us/cpp/preprocessor/predefined-macros?view=vs-2019',
		r'IUnknowns?' : r'https://docs.microsoft.com/en-us/windows/win32/api/unknwn/nn-unknwn-iunknown',
		r'(?:IUnknown::)?QueryInterface?' : r'https://docs.microsoft.com/en-us/windows/win32/api/unknwn/nf-unknwn-iunknown-queryinterface(q)',
		# unreal engine types
		r'(?:::)?FStrings?' : r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Containers/FString/index.html',
		r'(?:::)?FVector2Ds?' : r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector2D/index.html',
		r'(?:::)?FVector4s?' : r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector4/index.html',
		r'(?:::)?FVectors?' : r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector/index.html',
		r'(?:::)?FBox(?:es)?' : r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FBox/index.html',
		r'(?:::)?FMatrix(?:es|ices)?' : r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FMatrix/index.html',
		r'(?:::)?TMatrix(?:es|ices)?' : r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/TMatrix/index.html',
	}
	navbar = [r'files', r'groups', r'namespaces', r'classes']
	aliases = {
		r'cpp' : r'@code{.cpp}',
		r'ecpp' : r'@endcode',
		r'endcpp' : r'@endcode',
		r'out' : r'@code{.shell-session}',
		r'eout' : r'@endcode',
		r'endout' : r'@endcode',
		r'bash' : r'@code{.sh}',
		r'ebash' : r'@endcode',
		r'endbash' : r'@endcode',
		r'detail' : r'@details',
		r'inline_subheading{1}' : r'[h4]\1[/h4] ^^',
		r'conditional_return{1}' : r'<strong><em>\1:</em></strong> ^^',
		r'inline_note' : r'[set_class m-note m-info]',
		r'inline_warning' : r'[set_class m-note m-danger]',
		r'inline_attention' : r'[set_class m-note m-warning]',
		r'inline_remark' : r'[set_class m-note m-default]',
		r'github{1}' : r'<a href="https://github.com/\1" target="_blank">\1</a>',
		r'github{2}' : r'<a href="https://github.com/\1" target="_blank">\2</a>',
		r'godbolt{1}' : r'<a href="https://godbolt.org/z/\1" target="_blank">Try this code on Compiler Explorer</a>',
		r'flags_enum' : r'@note This enum is a flags type; it is equipped with a full complement of bitwise operators. ^^',
		r'implementers' : r'@par [parent_set_class m-block m-dim][emoji hammer][entity nbsp]Implementers: ',
		r'optional' : r'@par [parent_set_class m-block m-info]Optional field ^^',
		r'required' : r'@par [parent_set_class m-block m-warning][emoji warning][entity nbsp]Required field ^^',
		r'availability' : r'@par [parent_set_class m-block m-special]Conditional availability ^^',
		r'figure{1}' : r'@image html \1',
		r'figure{2}' : r'@image html \1 "\2"',
		r'm_div{1}' : r'@xmlonly<mcss:div xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="\1">@endxmlonly',
		r'm_enddiv' : r'@xmlonly</mcss:div>@endxmlonly',
		r'm_span{1}' : r'@xmlonly<mcss:span xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="\1">@endxmlonly',
		r'm_endspan' : r'@xmlonly</mcss:span>@endxmlonly',
		r'm_class{1}' : r'@xmlonly<mcss:class xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="\1" />@endxmlonly',
		r'm_footernavigation' : r'@xmlonly<mcss:footernavigation xmlns:mcss="http://mcss.mosra.cz/doxygen/" />@endxmlonly',
		r'm_examplenavigation{2}' : r'@xmlonly<mcss:examplenavigation xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:page="\1" mcss:prefix="\2" />@endxmlonly',
		r'm_keywords{1}' : r'@xmlonly<mcss:search xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:keywords="\1" />@endxmlonly',
		r'm_keyword{3}' : r'@xmlonly<mcss:search xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:keyword="\1" mcss:title="\2" mcss:suffix-length="\3" />@endxmlonly',
		r'm_enum_values_as_keywords' : r'@xmlonly<mcss:search xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:enum-values-as-keywords="true" />@endxmlonly'
	}



def _extract_kvps(config, table,
		key_label=None,
		value_label=None,
		strip_keys=True,
		allow_blank_keys=False,
		strip_values=True,
		allow_blank_values=False,
		value_type=None):

	assert config is not None
	assert isinstance(config, dict)
	assert table is not None

	if table not in config:
		return {}

	if key_label is None:
		key_label = r'key'
	if value_label is None:
		value_label = r'value'

	out = {}
	for k, v in config[table].items():
		key = str(k)
		if strip_keys:
			key = key.strip()
			if key in out:
				raise Exception(rf'{table}.{key}: cannot be specified more than once')
		if not allow_blank_keys and not key:
			raise Exception(rf'{table}: keys cannot be blank')

		if is_collection(v):
			raise Exception(rf'{table}.{key}: must be of the form "<{key_label}>" = "<{value_label}>"')

		value = str(v)
		if strip_values:
			value = value.strip()
		if not allow_blank_values and not value:
			raise Exception(rf'{table}.{key}: values cannot be blank')

		if value_type is not None:
			value = value_type(value)

		out[key] = value

	del config[table]

	return out



class _Warnings(object):
	def __init__(self, config):
		self.enabled = None
		self.treat_as_errors = None
		self.undocumented = None

		if 'warnings' not in config:
			return
		vals = config['warnings']

		if 'enabled' in vals:
			self.treat_as_errors = bool(vals['enabled'])
			del vals['enabled']

		if 'treat_as_errors' in vals:
			self.treat_as_errors = bool(vals['treat_as_errors'])
			del vals['treat_as_errors']

		if 'undocumented' in vals:
			self.treat_as_errors = bool(vals['undocumented'])
			del vals['undocumented']

		for k, v in vals.items():
			raise Exception(rf"Unknown config property 'warnings.{k}'")
		del config['warnings']



class _Highlighting(object):
	def __init__(self, config, defines):
		self.types = copy.deepcopy(_Defaults.types)
		self.macros = copy.deepcopy(_Defaults.macros)
		self.string_literals = copy.deepcopy(_Defaults.string_literals)
		self.numeric_literals = copy.deepcopy(_Defaults.numeric_literals)
		self.enums = copy.deepcopy(_Defaults.enums)
		self.namespaces = copy.deepcopy(_Defaults.namespaces)

		if 'highlighting' in config:
			vals = config['highlighting']

			if 'types' in vals:
				for t in coerce_collection(vals['types']):
					type_ = str(t).strip()
					if type_:
						self.types.add(type_)
				del vals['types']

			if 'macros' in vals:
				for m in coerce_collection(vals['macros']):
					macro = str(m).strip()
					if macro:
						self.macros.add(macro)
				del vals['macros']

			if 'string_literals' in vals:
				for lit in coerce_collection(vals['string_literals']):
					literal = str(lit).strip()
					if literal:
						self.string_literals.add(literal)
				del vals['string_literals']

			if 'numeric_literals' in vals:
				for lit in coerce_collection(vals['numeric_literals']):
					literal = str(lit).strip()
					if literal:
						self.numeric_literals.add(literal)
				del vals['numeric_literals']

			if 'enums' in vals:
				for e in coerce_collection(vals['enums']):
					enum = str(e).strip()
					if enum:
						self.enums.add(enum)
				del vals['enums']

			if 'namespaces' in vals:
				for ns in coerce_collection(vals['namespaces']):
					namespace = str(ns).strip()
					if namespace:
						self.namespaces.add(namespace)
				del vals['namespaces']

			for k, v in vals.items():
				raise Exception(rf"Unknown config property 'highlighting.{k}'")
			del config['highlighting']

		for k, v in defines.items():
			define = str(k)
			bracket = define.find('(')
			if bracket != -1:
				define = define[:bracket].strip()
			if define:
				self.macros.add(define)



class Context(object):

	__emoji = None
	__emoji_codepoints = None
	__emoji_uri = re.compile(r".+unicode/([0-9a-fA-F]+)[.]png.*", re.I)
	__data_files_lock = threading.Lock()

	def is_verbose(self):
		return self.__verbose

	def verbose(self, msg):
		if self.__verbose:
			log(self.logger, msg, level=logging.DEBUG)

	def verbose_value(self, name, val):
		if not self.__verbose:
			return
		with io.StringIO() as buf:
			print(rf'{name+": ":<35}', file=buf, end='')
			if val is not None:
				if isinstance(val, dict):
					if val:
						first = True
						for k, v in val.items():
							if not first:
								print(f'\n{" ":<35}', file=buf, end='')
							first = False
							print(rf'{k:<35} => {v}', file=buf, end='')
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
			log(self.logger, buf.getvalue(), level=logging.DEBUG)

	def verbose_object(self, name, obj):
		if not self.__verbose:
			return
		for k, v in obj.__dict__.items():
			self.verbose_value(rf'{name}.{k}', v)

	@classmethod
	def __init_data_files(cls, data_dir):
		cls.__data_files_lock.acquire()
		try:
			data_dir.mkdir(exist_ok=True)
			if cls.__emoji is None:
				file_path = coerce_path(data_dir, 'emoji.json')
				cls.__emoji = json.loads(read_all_text_from_file(file_path, 'https://api.github.com/emojis'))
				if '__processed' not in cls.__emoji:
					emoji = {}
					cls.__emoji_codepoints = set()
					for key, uri in cls.__emoji.items():
						m2 = cls.__emoji_uri.fullmatch(uri)
						if m2:
							cp = int(m2[1], 16)
							emoji[key] = [ cp, uri ]
							cls.__emoji_codepoints.add(cp)
					aliases = [
						('sundae', 'ice_cream'),
						('info', 'information_source')
					]
					for alias, key in aliases:
						emoji[alias] = emoji[key]
					emoji['__codepoints'] = [cp for cp in cls.__emoji_codepoints]
					emoji['__processed'] = True
					print(rf'Writing {file_path}')
					with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
						print(json.dumps(emoji, sort_keys=True, indent=4), file=f)
					cls.__emoji = emoji
				cls.__emoji_codepoints = set()
				for cp in cls.__emoji['__codepoints']:
					cls.__emoji_codepoints.add(cp)
		finally:
			cls.__data_files_lock.release()

	def __init__(self, config_path, output_dir, threads, cleanup, verbose, mcss_dir, temp_file_name, logger):

		self.logger = logger
		self.__verbose = bool(verbose)

		self.cleanup = bool(cleanup)
		self.verbose_value(r'Context.cleanup', self.cleanup)

		self.temp_file_name = str(temp_file_name).strip() if temp_file_name is not None else None
		self.verbose_value(r'Context.temp_file_name', self.temp_file_name)

		threads = int(threads)
		if threads <= 0:
			threads = os.cpu_count()
		self.threads = max(1, min(32, os.cpu_count(), threads))
		self.verbose_value(r'Context.threads', self.threads)

		self.fixers = None
		self.tagfile_path = None
		self.warnings = None

		# resolve paths
		if 1:

			# environment
			self.this_dir = Path(__file__).resolve().parent
			self.verbose_value(r'Context.this_dir', self.this_dir)
			self.data_dir = Path(self.this_dir, 'data')
			self.verbose_value(r'Context.data_dir', self.data_dir)
			self.dox_dir = self.this_dir.parent
			self.verbose_value(r'Context.dox_dir', self.dox_dir)
			if output_dir is None:
				output_dir = Path.cwd()
			if not isinstance(output_dir, Path):
				output_dir = Path(str(output_dir))
			self.output_dir = output_dir.resolve()
			self.verbose_value(r'Context.output_dir', self.output_dir)
			assert self.output_dir.is_absolute()

			# config + doxyfile
			input_dir = None
			self.config_path = None
			self.doxyfile_path = None
			if config_path is None:
				config_path = self.output_dir
			else:
				if not isinstance(config_path, Path):
					config_path = Path(str(config_path))
				if not config_path.is_absolute():
					config_path = Path(self.output_dir, config_path)
				config_path = config_path.resolve()
			if config_path.exists() and config_path.is_file():
				if config_path.suffix.lower() == '.toml':
					self.config_path = config_path
				else:
					self.doxyfile_path = config_path
			elif Path(str(config_path) + ".toml").exists():
				self.config_path = Path(str(config_path) + ".toml")
			elif config_path.is_dir():
				input_dir = config_path
				if Path(config_path, 'dox.toml').exists():
					self.config_path = Path(config_path, 'dox.toml')
				elif Path(config_path, 'Doxyfile-mcss').exists():
					self.doxyfile_path = Path(config_path, 'Doxyfile-mcss')
				elif Path(config_path, 'Doxyfile').exists():
					self.doxyfile_path = Path(config_path, 'Doxyfile')
			if input_dir is None:
				if self.config_path is not None:
					input_dir = self.config_path.parent
				elif self.doxyfile_path is not None:
					input_dir = self.doxyfile_path.parent
			if input_dir is not None:
				if self.config_path is None and Path(input_dir, 'dox.toml').exists():
					self.config_path = Path(input_dir, 'dox.toml')
				if self.doxyfile_path is None and Path(input_dir, 'Doxyfile-mcss').exists():
					self.doxyfile_path = Path(input_dir, 'Doxyfile-mcss')
				if self.doxyfile_path is None:
					self.doxyfile_path = Path(input_dir, 'Doxyfile')
			self.input_dir = input_dir
			self.verbose_value(r'Context.input_dir', self.input_dir)
			assert_existing_directory(self.input_dir)

			assert self.doxyfile_path is not None
			self.doxyfile_path = self.doxyfile_path.resolve()
			if self.doxyfile_path.exists() and not self.doxyfile_path.is_file():
				raise Exception(rf'{doxyfile_path} was not a file')
			if self.config_path is not None:
				self.config_path = self.config_path.resolve()
			self.verbose_value(r'Context.config_path', self.config_path)
			self.verbose_value(r'Context.doxyfile_path', self.doxyfile_path)

			# output folders
			self.xml_dir = Path(self.output_dir, 'xml')
			self.html_dir = Path(self.output_dir, 'html')
			self.verbose_value(r'Context.xml_dir', self.xml_dir)
			self.verbose_value(r'Context.html_dir', self.html_dir)

			# m.css
			if mcss_dir is None:
				mcss_dir = Path(self.dox_dir, 'external/mcss')
			if not isinstance(mcss_dir, Path):
				mcss_dir = Path(str(mcss_dir))
			mcss_dir = mcss_dir.resolve()
			assert_existing_directory(mcss_dir)
			assert_existing_file(Path(mcss_dir, 'documentation/doxygen.py'))
			self.mcss_dir = mcss_dir
			self.verbose_value(r'Context.mcss_dir', self.mcss_dir)

		# read + check config
		if 1:
			extra_files = []
			badges = []

			config = dict()
			if self.config_path is not None:
				assert_existing_file(self.config_path)
				config = pytomlpp.loads(read_all_text_from_file(self.config_path))

			self.warnings = _Warnings(config) # printed in run.py post-doxyfile

			# project name (PROJECT_NAME)
			self.name = ''
			if 'name' in config:
				self.name = str(config['name']).strip()
				del config['name']
			self.verbose_value(rf'Context.name', self.name)

			# project description (PROJECT_BRIEF)
			self.description = ''
			if 'description' in config:
				self.description = str(config['description']).strip()
				del config['description']
			self.verbose_value(r'Context.description', self.description)

			# project C++ version
			# defaults to 'current' cpp year version based on (current year - 2)
			self.cpp = max(int(datetime.datetime.now().year) - 2, 2011)
			self.cpp = self.cpp - ((self.cpp - 2011) % 3)
			if 'cpp' in config:
				self.cpp = str(config['cpp']).lstrip('0 \t').rstrip()
				if not self.cpp:
					self.cpp = '20'
				self.cpp = int(self.cpp)
				if self.cpp in (1998, 98):
					self.cpp = 1998
				else:
					self.cpp = self.cpp % 2000
					if self.cpp in (3, 11, 14, 17, 20, 23, 26, 29):
						self.cpp = self.cpp + 2000
					else:
						raise Exception(rf"'{config['cpp']}' is not a valid cpp standard version")
				del config['cpp']
			self.verbose_value(r'Context.cpp', self.cpp)
			badge = rf'dox-badge-c++{str(self.cpp)[2:]}.svg'
			badges.append((rf'C++{str(self.cpp)[2:]}', badge, r'https://en.cppreference.com/w/cpp/compiler_support'))
			extra_files.append(Path(self.data_dir, badge))

			# project license
			self.license = None
			if 'license' in config:
				if not is_collection(config['license']) or len(config['license']) != 2:
					raise Exception(rf'license: must be of the form [ "<name>" , "<uri>" ]')
				name = str(config['license'][0]).strip()
				uri = str(config['license'][1]).strip()
				if name and uri:
					self.license = (name, uri)
				del config['license']
				if self.license:
					badge = Path(self.data_dir, rf'dox-badge-license-{self.license[0].lower()}.svg')
					if badge.exists():
						extra_files.append(badge)
						badges.append((self.license[0], badge.name, self.license[1]))
			self.verbose_value(r'Context.license', self.license)

			# project repo access level
			self.private_repo = False
			if 'private_repo' in config:
				self.private_repo = bool(config['github'])
				del config['private_repo']

			# project github repo
			self.github = ''
			if 'github' in config:
				self.github = str(config['github']).strip().replace('\\', '/').strip('/')
				del config['github']
			self.verbose_value(r'Context.github', self.github)
			if self.github and not self.private_repo:
				badges.append((
					r'Releases',
					rf'https://img.shields.io/github/v/release/{self.github}?style=flat-square',
					rf'https://github.com/{self.github}/releases'
				))

			# m.css navbar
			if 'navbar' in config:
				self.navbar = []
				for v in coerce_collection(config['navbar']):
					val = str(v).strip().lower()
					if val:
						self.navbar.append(val)
				del config['navbar']
			else:
				self.navbar = copy.deepcopy(_Defaults.navbar)
			for i in range(len(self.navbar)):
				if self.navbar[i] == 'classes':
					self.navbar[i] = 'annotated'
				elif self.navbar[i] == 'groups':
					self.navbar[i] = 'modules'
			if self.github and 'github' not in self.navbar:
				self.navbar.append('github')
			self.navbar = tuple(self.navbar)
			self.verbose_value(r'Context.navbar', self.navbar)

			# <meta> tags
			self.meta = {}
			for k, v in _extract_kvps(config, 'meta', key_label='name', allow_blank_values=True, value_label='content').items():
				self.meta[k] = v
			if self.description and 'description' not in self.meta:
				self.meta['description'] = self.description
			self.verbose_value(r'Context.meta', self.meta)

			# TAGFILES
			self.tagfiles = {}
			for k,v in _extract_kvps(config, 'tagfiles', key_label='file', value_label='uri').items():
				self.tagfiles[str(Path(self.input_dir, k).resolve())] = v
			self.tagfiles[str(Path(self.data_dir, r'cppreference-doxygen-web.tag.xml'))] = r'http://en.cppreference.com/w/'
			for k, v in self.tagfiles.items():
				assert_existing_file(k)
			self.verbose_value(r'Context.tagfiles', self.tagfiles)

			# PREDEFINED
			self.defines = copy.deepcopy(_Defaults.defines)
			for k, v in _extract_kvps(config, 'defines', key_label='define', allow_blank_values=True).items():
				self.defines[k] = v
			non_cpp_def_defines = copy.deepcopy(self.defines)
			cpp_defs = dict()
			for ver in (1998, 2003, 2011, 2014, 2017, 2020, 2023, 2026, 2029):
				if ver > self.cpp:
					break
				for k, v in _Defaults.cpp_builtin_defines[ver].items():
					cpp_defs[k] = v
			for k, v in cpp_defs.items():
				self.defines[k] = v
			self.verbose_value(r'Context.defines', self.defines)

			# inline namespaces for old versions of doxygen
			self.inline_namespaces = copy.deepcopy(_Defaults.inline_namespaces)
			if 'inline_namespaces' in config:
				for ns in coerce_collection(config['inline_namespaces']):
					namespace = str(ns).strip()
					if namespace:
						self.inline_namespaces.add(namespace)
				del config['inline_namespaces']
			self.verbose_value(r'Context.inline_namespaces', self.inline_namespaces)

			# autolinks
			default_autolinks = [(k, v) for k, v in _Defaults.autolinks.items()]
			user_autolinks = []
			if 'autolinks' in config:
				for pattern, u in config['autolinks'].items():
					if is_collection(u):
						raise Exception(rf'autolinks.{pattern}: must be of the form "<pattern>" = "<uri>"')
					uri = str(u).strip()
					if pattern.strip() and uri:
						user_autolinks.append((pattern, uri))
				del config['autolinks']
			default_autolinks.sort(key = lambda v: len(v[0]), reverse=True)
			user_autolinks.sort(key = lambda v: len(v[0]), reverse=True)
			self.autolinks = tuple(user_autolinks + default_autolinks)
			self.verbose_value(r'Context.autolinks', self.autolinks)

			# ALIASES
			self.aliases = copy.deepcopy(_Defaults.aliases)
			if 'aliases' in config:
				for k, v in config['aliases'].items():
					if is_collection(v):
						raise Exception(rf'aliases.{k}: must be of the form "<alias>" = "<replacement>"')
					alias = str(k).strip()
					if not alias:
						continue
					if alias in self.aliases:
						raise Exception(rf'aliases.{k}: cannot override a built-in alias')
						self.aliases[alias] = v
				del config['autolinks']
			self.verbose_value(r'Context.aliases', self.aliases)

			# implementation headers to merge
			self.implementation_headers = []
			if 'implementation_headers' in config:
				for k, v in config['implementation_headers'].items():
					header = str(k).strip()
					if not is_collection(v):
						raise Exception(rf'implementation_headers.{text}: must be of the form "<main header>" = [ "<impl header>", "<impl header>", ... ]')
					impls = [str(i).strip() for i in v]
					impls = [i for i in impls if len(i)]
					if header and impls:
						self.implementation_headers .append((header, impls))
				del config['implementation_headers']
			self.implementation_headers = tuple(self.implementation_headers)
			self.verbose_value(r'Context.implementation_headers', self.implementation_headers)

			# SHOW_INCLUDES
			self.show_includes = None
			if 'show_includes' in config:
				self.show_includes = bool(config['show_includes'])
				del config['show_includes']
			self.verbose_value(r'Context.show_includes', self.show_includes)

			# GENERATE_TAGFILE
			self.generate_tagfile = None
			if 'generate_tagfile' in config:
				self.generate_tagfile = bool(config['generate_tagfile'])
				del config['generate_tagfile']
			self.verbose_value(r'Context.generate_tagfile', self.generate_tagfile)

			# badges (shields) for index.html
			if 'badges' in config:
				for k, v in config['badges'].items():
					text = str(k).strip()
					if not is_collection(v) or len(v) != 2:
						raise Exception(rf'badges.{text}: must be of the form "<name>" = [ "<image>", "<uri>" ]')
					image_uri = str(v[0]).strip()
					anchor_uri = str(v[1]).strip()
					if text and image_uri and anchor_uri:
						badges.append((text, image_uri, anchor_uri))
				del config['badges']
			self.badges = tuple(badges)
			self.verbose_value(r'Context.badges', self.badges)

			# HTML_EXTRA_FILES
			if 'extra_files' in config:
				for f in coerce_collection(config['extra_files']):
					file = str(f).strip()
					if file:
						extra_files.append(Path(file))
				del config['extra_files']

			# m.css favicon
			self.favicon = None
			if 'favicon' in config:
				file = str(config['favicon'])
				if file:
					file = Path(file)
					if not file.is_absolute():
						file = Path(self.input_dir, file)
					self.favicon = file.resolve()
					extra_files.append(self.favicon)
				del config['favicon']
			else:
				favicon = Path(self.input_dir, 'favicon.ico')
				if favicon.exists() and favicon.is_file():
					self.favicon = favicon
					extra_files.append(favicon)
			self.verbose_value(r'Context.favicon', self.favicon)

			# add built-ins to extra files
			extra_files.append(Path(self.data_dir, r'dox.css'))
			extra_files.append(Path(self.data_dir, r'dox-github-icon.png'))

			# check extra files
			for i in range(len(extra_files)):
				if not extra_files[i].is_absolute():
					extra_files[i] = Path(self.input_dir, extra_files[i])
				extra_files[i] = extra_files[i].resolve()
				if not extra_files[i].exists() or not extra_files[i].is_file():
					raise Exception(rf'extra_files: {self.extra_files[i]} did not exist or was not a file')
			self.extra_files = set(extra_files)
			self.verbose_value(r'Context.extra_files', self.extra_files)
			extra_filenames = set()
			for f in self.extra_files:
				if f.name in extra_filenames:
					raise Exception(rf'extra_files: Multiple source files with the name {f.name}')
				extra_filenames.add(f.name)

			self.highlighting = _Highlighting(config, non_cpp_def_defines) # printed in run.py post-xml

			for k, v in config.items():
				raise Exception(rf"Unknown config property '{k}'")

		# initialize other data from files on disk
		self.__init_data_files(self.data_dir)
		self.emoji = self.__emoji
		self.emoji_codepoints = self.__emoji_codepoints

	def __bool__(self):
		return True
