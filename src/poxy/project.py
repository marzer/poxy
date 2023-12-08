#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Everything relating to the 'project context' object that describes the project for which the documentation is being generated.
"""

import copy
import os

try:
    import pytomlpp as toml  # fast; based on toml++ (C++)
except ImportError:
    try:
        import tomllib as toml  # PEP 680
    except ImportError:
        import tomli as toml

import datetime
import itertools

from . import doxygen, emoji, paths, repos
from .schemas import *
from .utils import *
from .version import *

# =======================================================================================================================
# internal helpers
# =======================================================================================================================


class Defaults(object):
    inline_namespaces = {r'std::(?:literals::)?(?:chrono|complex|string|string_view)_literals'}
    macros = {
        r'NDEBUG': 1,
        r'DOXYGEN': 1,
        r'__DOXYGEN__': 1,
        r'__doxygen__': 1,
        r'__POXY__': 1,
        r'__poxy__': 1,
        r'__has_include(...)': 0,
        r'__has_attribute(...)': 0,
        r'__has_builtin(...)': 0,
        r'__has_feature(...)': 0,
        r'__has_cpp_attribute(...)': 999999,
        r'POXY_IMPLEMENTATION_DETAIL(...)': r'POXY_IMPLEMENTATION_DETAIL_IMPL',
        r'POXY_IGNORE(...)': r'',
    }
    cpp_builtin_macros = {
        1998: {r'__cplusplus': r'199711L', r'__cpp_rtti': 199711, r'__cpp_exceptions': 199711},
        2003: dict(),  # apparently?
        2011: {
            r'__cplusplus': r'201103L',
            r'__cpp_unicode_characters': 200704,
            r'__cpp_raw_strings': 200710,
            r'__cpp_unicode_literals': 200710,
            r'__cpp_user_defined_literals': 200809,
            r'__cpp_threadsafe_static_init': 200806,
            r'__cpp_lambdas': 200907,
            r'__cpp_constexpr': 200704,
            r'__cpp_range_based_for': 200907,
            r'__cpp_static_assert': 200410,
            r'__cpp_decltype': 200707,
            r'__cpp_attributes': 200809,
            r'__cpp_rvalue_references': 200610,
            r'__cpp_variadic_templates': 200704,
            r'__cpp_initializer_lists': 200806,
            r'__cpp_delegating_constructors': 200604,
            r'__cpp_nsdmi': 200809,
            r'__cpp_inheriting_constructors': 200802,
            r'__cpp_ref_qualifiers': 200710,
            r'__cpp_alias_templates': 200704,
        },
        2014: {
            r'__cplusplus': r'201402L',
            r'__cpp_binary_literals': 201304,
            r'__cpp_init_captures': 201304,
            r'__cpp_generic_lambdas': 201304,
            r'__cpp_sized_deallocation': 201309,
            r'__cpp_constexpr': 201304,
            r'__cpp_decltype_auto': 201304,
            r'__cpp_return_type_deduction': 201304,
            r'__cpp_aggregate_nsdmi': 201304,
            r'__cpp_variable_templates': 201304,
            r'__cpp_lib_integer_sequence': 201304,
            r'__cpp_lib_exchange_function': 201304,
            r'__cpp_lib_tuples_by_type': 201304,
            r'__cpp_lib_tuple_element_t': 201402,
            r'__cpp_lib_make_unique': 201304,
            r'__cpp_lib_transparent_operators': 201210,
            r'__cpp_lib_integral_constant_callable': 201304,
            r'__cpp_lib_transformation_trait_aliases': 201304,
            r'__cpp_lib_result_of_sfinae': 201210,
            r'__cpp_lib_is_final': 201402,
            r'__cpp_lib_is_null_pointer': 201309,
            r'__cpp_lib_chrono_udls': 201304,
            r'__cpp_lib_string_udls': 201304,
            r'__cpp_lib_generic_associative_lookup': 201304,
            r'__cpp_lib_null_iterators': 201304,
            r'__cpp_lib_make_reverse_iterator': 201402,
            r'__cpp_lib_robust_nonmodifying_seq_ops': 201304,
            r'__cpp_lib_complex_udls': 201309,
            r'__cpp_lib_quoted_string_io': 201304,
            r'__cpp_lib_shared_timed_mutex': 201402,
        },
        2017: {
            r'__cplusplus': r'201703L',
            r'__cpp_hex_float': 201603,
            r'__cpp_inline_variables': 201606,
            r'__cpp_aligned_new': 201606,
            r'__cpp_guaranteed_copy_elision': 201606,
            r'__cpp_noexcept_function_type': 201510,
            r'__cpp_fold_expressions': 201603,
            r'__cpp_capture_star_this': 201603,
            r'__cpp_constexpr': 201603,
            r'__cpp_if_constexpr': 201606,
            r'__cpp_range_based_for': 201603,
            r'__cpp_static_assert': 201411,
            r'__cpp_deduction_guides': 201703,
            r'__cpp_nontype_template_parameter_auto': 201606,
            r'__cpp_namespace_attributes': 201411,
            r'__cpp_enumerator_attributes': 201411,
            r'__cpp_inheriting_constructors': 201511,
            r'__cpp_variadic_using': 201611,
            r'__cpp_structured_bindings': 201606,
            r'__cpp_aggregate_bases': 201603,
            r'__cpp_nontype_template_args': 201411,
            r'__cpp_template_template_args': 201611,
            r'__cpp_lib_byte': 201603,
            r'__cpp_lib_hardware_interference_size': 201703,
            r'__cpp_lib_launder': 201606,
            r'__cpp_lib_uncaught_exceptions': 201411,
            r'__cpp_lib_as_const': 201510,
            r'__cpp_lib_make_from_tuple': 201606,
            r'__cpp_lib_apply': 201603,
            r'__cpp_lib_optional': 201606,
            r'__cpp_lib_variant': 201606,
            r'__cpp_lib_any': 201606,
            r'__cpp_lib_addressof_constexpr': 201603,
            r'__cpp_lib_raw_memory_algorithms': 201606,
            r'__cpp_lib_transparent_operators': 201510,
            r'__cpp_lib_enable_shared_from_this': 201603,
            r'__cpp_lib_shared_ptr_weak_type': 201606,
            r'__cpp_lib_shared_ptr_arrays': 201611,
            r'__cpp_lib_memory_resource': 201603,
            r'__cpp_lib_boyer_moore_searcher': 201603,
            r'__cpp_lib_invoke': 201411,
            r'__cpp_lib_not_fn': 201603,
            r'__cpp_lib_void_t': 201411,
            r'__cpp_lib_bool_constant': 201505,
            r'__cpp_lib_type_trait_variable_templates': 201510,
            r'__cpp_lib_logical_traits': 201510,
            r'__cpp_lib_is_swappable': 201603,
            r'__cpp_lib_is_invocable': 201703,
            r'__cpp_lib_has_unique_object_representations': 201606,
            r'__cpp_lib_is_aggregate': 201703,
            r'__cpp_lib_chrono': 201611,
            r'__cpp_lib_execution': 201603,
            r'__cpp_lib_parallel_algorithm': 201603,
            r'__cpp_lib_to_chars': 201611,
            r'__cpp_lib_string_view': 201606,
            r'__cpp_lib_allocator_traits_is_always_equal': 201411,
            r'__cpp_lib_incomplete_container_elements': 201505,
            r'__cpp_lib_map_try_emplace': 201411,
            r'__cpp_lib_unordered_map_try_emplace': 201411,
            r'__cpp_lib_node_extract': 201606,
            r'__cpp_lib_array_constexpr': 201603,
            r'__cpp_lib_nonmember_container_access': 201411,
            r'__cpp_lib_sample': 201603,
            r'__cpp_lib_clamp': 201603,
            r'__cpp_lib_gcd_lcm': 201606,
            r'__cpp_lib_hypot': 201603,
            r'__cpp_lib_math_special_functions': 201603,
            r'__cpp_lib_filesystem': 201703,
            r'__cpp_lib_atomic_is_always_lock_free': 201603,
            r'__cpp_lib_shared_mutex': 201505,
            r'__cpp_lib_scoped_lock': 201703,
        },
        2020: {
            r'__cplusplus': r'202002L',
            r'__cpp_aggregate_paren_init': 201902,
            r'__cpp_char8_t': 201811,
            r'__cpp_concepts': 202002,
            r'__cpp_conditional_explicit': 201806,
            r'__cpp_consteval': 201811,
            r'__cpp_constexpr': 202002,
            r'__cpp_constexpr_dynamic_alloc': 201907,
            r'__cpp_constexpr_in_decltype': 201711,
            r'__cpp_constinit': 201907,
            r'__cpp_deduction_guides': 201907,
            r'__cpp_designated_initializers': 201707,
            r'__cpp_generic_lambdas': 201707,
            r'__cpp_impl_coroutine': 201902,
            r'__cpp_impl_destroying_delete': 201806,
            r'__cpp_impl_three_way_comparison': 201907,
            r'__cpp_init_captures': 201803,
            r'__cpp_lib_array_constexpr': 201811,
            r'__cpp_lib_assume_aligned': 201811,
            r'__cpp_lib_atomic_flag_test': 201907,
            r'__cpp_lib_atomic_float': 201711,
            r'__cpp_lib_atomic_lock_free_type_aliases': 201907,
            r'__cpp_lib_atomic_ref': 201806,
            r'__cpp_lib_atomic_shared_ptr': 201711,
            r'__cpp_lib_atomic_value_initialization': 201911,
            r'__cpp_lib_atomic_wait': 201907,
            r'__cpp_lib_barrier': 201907,
            r'__cpp_lib_bind_front': 201907,
            r'__cpp_lib_bit_cast': 201806,
            r'__cpp_lib_bitops': 201907,
            r'__cpp_lib_bounded_array_traits': 201902,
            r'__cpp_lib_char8_t': 201907,
            r'__cpp_lib_chrono': 201907,
            r'__cpp_lib_concepts': 202002,
            r'__cpp_lib_constexpr_algorithms': 201806,
            r'__cpp_lib_constexpr_complex': 201711,
            r'__cpp_lib_constexpr_dynamic_alloc': 201907,
            r'__cpp_lib_constexpr_functional': 201907,
            r'__cpp_lib_constexpr_iterator': 201811,
            r'__cpp_lib_constexpr_memory': 201811,
            r'__cpp_lib_constexpr_numeric': 201911,
            r'__cpp_lib_constexpr_string': 201907,
            r'__cpp_lib_constexpr_string_view': 201811,
            r'__cpp_lib_constexpr_tuple': 201811,
            r'__cpp_lib_constexpr_utility': 201811,
            r'__cpp_lib_constexpr_vector': 201907,
            r'__cpp_lib_coroutine': 201902,
            r'__cpp_lib_destroying_delete': 201806,
            r'__cpp_lib_endian': 201907,
            r'__cpp_lib_erase_if': 202002,
            r'__cpp_lib_execution': 201902,
            r'__cpp_lib_format': 201907,
            r'__cpp_lib_generic_unordered_lookup': 201811,
            r'__cpp_lib_int_pow2': 202002,
            r'__cpp_lib_integer_comparison_functions': 202002,
            r'__cpp_lib_interpolate': 201902,
            r'__cpp_lib_is_constant_evaluated': 201811,
            r'__cpp_lib_is_layout_compatible': 201907,
            r'__cpp_lib_is_nothrow_convertible': 201806,
            r'__cpp_lib_is_pointer_interconvertible': 201907,
            r'__cpp_lib_jthread': 201911,
            r'__cpp_lib_latch': 201907,
            r'__cpp_lib_list_remove_return_type': 201806,
            r'__cpp_lib_math_constants': 201907,
            r'__cpp_lib_polymorphic_allocator': 201902,
            r'__cpp_lib_ranges': 201911,
            r'__cpp_lib_remove_cvref': 201711,
            r'__cpp_lib_semaphore': 201907,
            r'__cpp_lib_shared_ptr_arrays': 201707,
            r'__cpp_lib_shift': 201806,
            r'__cpp_lib_smart_ptr_for_overwrite': 202002,
            r'__cpp_lib_source_location': 201907,
            r'__cpp_lib_span': 202002,
            r'__cpp_lib_ssize': 201902,
            r'__cpp_lib_starts_ends_with': 201711,
            r'__cpp_lib_string_view': 201803,
            r'__cpp_lib_syncbuf': 201803,
            r'__cpp_lib_three_way_comparison': 201907,
            r'__cpp_lib_to_address': 201711,
            r'__cpp_lib_to_array': 201907,
            r'__cpp_lib_type_identity': 201806,
            r'__cpp_lib_unwrap_ref': 201811,
            r'__cpp_modules': 201907,
            r'__cpp_nontype_template_args': 201911,
            r'__cpp_using_enum': 201907,
        },
        2023: {
            r'__cplusplus': r'202300L',
            r'__cpp_constexpr': 202110,
            r'__cpp_explicit_this_parameter': 202110,
            r'__cpp_if_consteval': 202106,
            r'__cpp_lib_adaptor_iterator_pair_constructor': 202106,
            r'__cpp_lib_allocate_at_least': 202106,
            r'__cpp_lib_associative_heterogeneous_erasure': 202110,
            r'__cpp_lib_byteswap': 202110,
            r'__cpp_lib_constexpr_typeinfo': 202106,
            r'__cpp_lib_format': 202110,
            r'__cpp_lib_invoke_r': 202106,
            r'__cpp_lib_is_scoped_enum': 202011,
            r'__cpp_lib_monadic_optional': 202110,
            r'__cpp_lib_move_only_function': 202110,
            r'__cpp_lib_optional': 202106,
            r'__cpp_lib_out_ptr': 202106,
            r'__cpp_lib_ranges': 202110,
            r'__cpp_lib_ranges_starts_ends_with': 202106,
            r'__cpp_lib_ranges_zip': 202110,
            r'__cpp_lib_spanstream': 202106,
            r'__cpp_lib_stacktrace': 202011,
            r'__cpp_lib_stdatomic_h': 202011,
            r'__cpp_lib_string_contains': 202011,
            r'__cpp_lib_string_resize_and_overwrite': 202110,
            r'__cpp_lib_to_underlying': 202102,
            r'__cpp_lib_variant': 202102,
            r'__cpp_lib_variant': 202106,
            r'__cpp_multidimensional_subscript': 202110,
            r'__cpp_size_t_suffix': 202011,
        },
        2026: {r'__cplusplus': r'202600L'},
        2029: {r'__cplusplus': r'202900L'},
    }
    autolinks = {
        # builtins
        r'const_cast': r'https://en.cppreference.com/w/cpp/language/const_cast',
        r'dynamic_cast': r'https://en.cppreference.com/w/cpp/language/dynamic_cast',
        r'reinterpret_cast': r'https://en.cppreference.com/w/cpp/language/reinterpret_cast',
        r'static_cast': r'https://en.cppreference.com/w/cpp/language/static_cast',
        r'(?:_Float|__fp)16s?': r'https://gcc.gnu.org/onlinedocs/gcc/Half-Precision.html',
        r'(?:_Float|__float)(128|80)s?': r'https://gcc.gnu.org/onlinedocs/gcc/Floating-Types.html',
        r'(?:wchar|char(?:8|16|32))_ts?': r'https://en.cppreference.com/w/cpp/language/types#Character_types',
        regex_trie(
            r'__cplusplus',  #
            r'__FILE__',
            r'__LINE__',
            r'__DATE__',
            r'__TIME__',
            r'__STDC__',
            r'__STDC_HOSTED__',
            r'__STDC_VERSION__',
            r'__STDC_ISO_10646__',
            r'__STDC_MB_MIGHT_NEQ_WC__',
            r'__STDCPP_THREADS__',
            r'__STDCPP_DEFAULT_NEW_ALIGNMENT__',
            r'__STDCPP_STRICT_POINTER_SAFETY__',
        ): r'https://en.cppreference.com/w/cpp/preprocessor/replace',
        # standard library
        r'std::assume_aligned(?:\(\))?': r'https://en.cppreference.com/w/cpp/memory/assume_aligned',
        r'(?:std::)?nullptr_t': r'https://en.cppreference.com/w/cpp/types/nullptr_t',
        r'(?:std::)?ptrdiff_t': r'https://en.cppreference.com/w/cpp/types/ptrdiff_t',
        r'(?:std::)?size_t': r'https://en.cppreference.com/w/cpp/types/size_t',
        r'(?:std::)?u?int(?:_fast|_least)?(?:8|16|32|64)_ts?': r'https://en.cppreference.com/w/cpp/types/integer',
        r'(?:std::)?u?int(?:max|ptr)_t': r'https://en.cppreference.com/w/cpp/types/integer',
        r'\s(?:<|&lt;)fstream(?:>|&gt;)': r'https://en.cppreference.com/w/cpp/header/fstream',
        r'\s(?:<|&lt;)iosfwd(?:>|&gt;)': r'https://en.cppreference.com/w/cpp/header/iosfwd',
        r'\s(?:<|&lt;)iostream(?:>|&gt;)': r'https://en.cppreference.com/w/cpp/header/iostream',
        r'\s(?:<|&lt;)sstream(?:>|&gt;)': r'https://en.cppreference.com/w/cpp/header/sstream',
        r'\s(?:<|&lt;)string(?:>|&gt;)': r'https://en.cppreference.com/w/cpp/header/string',
        r'\s(?:<|&lt;)string_view(?:>|&gt;)': r'https://en.cppreference.com/w/cpp/header/string_view',
        r'std::(?:basic_|w)?fstreams?': r'https://en.cppreference.com/w/cpp/io/basic_fstream',
        r'std::(?:basic_|w)?ifstreams?': r'https://en.cppreference.com/w/cpp/io/basic_ifstream',
        r'std::(?:basic_|w)?iostreams?': r'https://en.cppreference.com/w/cpp/io/basic_iostream',
        r'std::(?:basic_|w)?istreams?': r'https://en.cppreference.com/w/cpp/io/basic_istream',
        r'std::(?:basic_|w)?istringstreams?': r'https://en.cppreference.com/w/cpp/io/basic_istringstream',
        r'std::(?:basic_|w)?ofstreams?': r'https://en.cppreference.com/w/cpp/io/basic_ofstream',
        r'std::(?:basic_|w)?ostreams?': r'https://en.cppreference.com/w/cpp/io/basic_ostream',
        r'std::(?:basic_|w)?ostringstreams?': r'https://en.cppreference.com/w/cpp/io/basic_ostringstream',
        r'std::(?:basic_|w)?stringstreams?': r'https://en.cppreference.com/w/cpp/io/basic_stringstream',
        r'std::(?:basic_|w|u(?:8|16|32))?string_views?': r'https://en.cppreference.com/w/cpp/string/basic_string_view',
        r'std::(?:basic_|w|u(?:8|16|32))?strings?': r'https://en.cppreference.com/w/cpp/string/basic_string',
        r'std::[fl]?abs[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/abs',
        r'std::acos[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/acos',
        r'std::add_[lr]value_reference(?:_t)?': r'https://en.cppreference.com/w/cpp/types/add_reference',
        r'std::add_(?:cv|const|volatile)(?:_t)?': r'https://en.cppreference.com/w/cpp/types/add_cv',
        r'std::add_pointer(?:_t)?': r'https://en.cppreference.com/w/cpp/types/add_pointer',
        r'std::allocators?': r'https://en.cppreference.com/w/cpp/memory/allocator',
        r'std::arrays?': r'https://en.cppreference.com/w/cpp/container/array',
        r'std::as_(writable_)?bytes(?:\(\))?': r'https://en.cppreference.com/w/cpp/container/span/as_bytes',
        r'std::asin[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/asin',
        r'std::atan2[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/atan2',
        r'std::atan[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/atan',
        r'std::bad_alloc': r'https://en.cppreference.com/w/cpp/memory/new/bad_alloc',
        r'std::basic_ios': r'https://en.cppreference.com/w/cpp/io/basic_ios',
        r'std::bit_cast(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/bit_cast',
        r'std::bit_ceil(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/bit_ceil',
        r'std::bit_floor(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/bit_floor',
        r'std::bit_width(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/bit_width',
        r'std::bytes?': r'https://en.cppreference.com/w/cpp/types/byte',
        r'std::ceil[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/ceil',
        r'std::char_traits': r'https://en.cppreference.com/w/cpp/string/char_traits',
        r'std::chrono::durations?': r'https://en.cppreference.com/w/cpp/chrono/duration',
        r'std::clamp(?:\(\))?': r'https://en.cppreference.com/w/cpp/algorithm/clamp',
        r'std::conditional(?:_t)?': r'https://en.cppreference.com/w/cpp/types/conditional',
        r'std::cos[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/cos',
        r'std::countl_one(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/countl_one',
        r'std::countl_zero(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/countl_zero',
        r'std::countr_one(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/countr_one',
        r'std::countr_zero(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/countr_zero',
        r'std::enable_if(?:_t)?': r'https://en.cppreference.com/w/cpp/types/enable_if',
        r'std::exceptions?': r'https://en.cppreference.com/w/cpp/error/exception',
        r'std::floor[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/floor',
        r'std::fpos': r'https://en.cppreference.com/w/cpp/io/fpos',
        r'std::has_single_bit(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/has_single_bit',
        r'std::hash': r'https://en.cppreference.com/w/cpp/utility/hash',
        r'std::initializer_lists?': r'https://en.cppreference.com/w/cpp/utility/initializer_list',
        r'std::integral_constants?': r'https://en.cppreference.com/w/cpp/types/integral_constant',
        r'std::ios(?:_base)?': r'https://en.cppreference.com/w/cpp/io/ios_base',
        r'std::is_(?:nothrow_)?convertible(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_convertible',
        r'std::is_(?:nothrow_)?invocable(?:_r)?': r'https://en.cppreference.com/w/cpp/types/is_invocable',
        r'std::is_base_of(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_base_of',
        r'std::is_constant_evaluated(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/is_constant_evaluated',
        r'std::is_enum(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_enum',
        r'std::is_floating_point(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_floating_point',
        r'std::is_integral(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_integral',
        r'std::is_pointer(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_pointer',
        r'std::is_reference(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_reference',
        r'std::is_same(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_same',
        r'std::is_signed(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_signed',
        r'std::is_unsigned(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_unsigned',
        r'std::is_void(?:_v)?': r'https://en.cppreference.com/w/cpp/types/is_void',
        r'std::launder(?:\(\))?': r'https://en.cppreference.com/w/cpp/utility/launder',
        r'std::lerp(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/lerp',
        r'std::maps?': r'https://en.cppreference.com/w/cpp/container/map',
        r'std::max(?:\(\))?': r'https://en.cppreference.com/w/cpp/algorithm/max',
        r'std::min(?:\(\))?': r'https://en.cppreference.com/w/cpp/algorithm/min',
        r'std::numeric_limits::min(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/min',
        r'std::numeric_limits::lowest(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/lowest',
        r'std::numeric_limits::max(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/max',
        r'std::numeric_limits::epsilon(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/epsilon',
        r'std::numeric_limits::round_error(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/round_error',
        r'std::numeric_limits::infinity(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/infinity',
        r'std::numeric_limits::quiet_NaN(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/quiet_NaN',
        r'std::numeric_limits::signaling_NaN(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/signaling_NaN',
        r'std::numeric_limits::denorm_min(?:\(\))?': r'https://en.cppreference.com/w/cpp/types/numeric_limits/denorm_min',
        r'std::numeric_limits': r'https://en.cppreference.com/w/cpp/types/numeric_limits',
        r'std::optionals?': r'https://en.cppreference.com/w/cpp/utility/optional',
        r'std::pairs?': r'https://en.cppreference.com/w/cpp/utility/pair',
        r'std::popcount(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/popcount',
        r'std::remove_cv(?:_t)?': r'https://en.cppreference.com/w/cpp/types/remove_cv',
        r'std::remove_reference(?:_t)?': r'https://en.cppreference.com/w/cpp/types/remove_reference',
        r'std::reverse_iterator': r'https://en.cppreference.com/w/cpp/iterator/reverse_iterator',
        r'std::runtime_errors?': r'https://en.cppreference.com/w/cpp/error/runtime_error',
        r'std::sets?': r'https://en.cppreference.com/w/cpp/container/set',
        r'std::shared_ptrs?': r'https://en.cppreference.com/w/cpp/memory/shared_ptr',
        r'std::sin[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/sin',
        r'std::spans?': r'https://en.cppreference.com/w/cpp/container/span',
        r'std::sqrt[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/sqrt',
        r'std::tan[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/tan',
        r'std::to_address(?:\(\))?': r'https://en.cppreference.com/w/cpp/memory/to_address',
        r'std::(?:true|false)_type': r'https://en.cppreference.com/w/cpp/types/integral_constant',
        r'std::trunc[fl]?(?:\(\))?': r'https://en.cppreference.com/w/cpp/numeric/math/trunc',
        r'std::tuple_element(?:_t)?': r'https://en.cppreference.com/w/cpp/utility/tuple/tuple_element',
        r'std::tuple_size(?:_v)?': r'https://en.cppreference.com/w/cpp/utility/tuple/tuple_size',
        r'std::tuples?': r'https://en.cppreference.com/w/cpp/utility/tuple',
        r'std::type_identity(?:_t)?': r'https://en.cppreference.com/w/cpp/types/type_identity',
        r'std::underlying_type(?:_t)?': r'https://en.cppreference.com/w/cpp/types/underlying_type',
        r'std::unique_ptrs?': r'https://en.cppreference.com/w/cpp/memory/unique_ptr',
        r'std::unordered_maps?': r'https://en.cppreference.com/w/cpp/container/unordered_map',
        r'std::unordered_sets?': r'https://en.cppreference.com/w/cpp/container/unordered_set',
        r'std::vectors?': r'https://en.cppreference.com/w/cpp/container/vector',
        r'std::atomic[a-zA-Z_0-9]*': r'https://en.cppreference.com/w/cpp/atomic/atomic',
        # named requirements
        r'Allocators?': r'https://en.cppreference.com/w/cpp/named_req/Allocator',
        r'AllocatorAwareContainers?': r'https://en.cppreference.com/w/cpp/named_req/AllocatorAwareContainer',
        r'AssociativeContainers?': r'https://en.cppreference.com/w/cpp/named_req/AssociativeContainer',
        r'BasicFormatters?': r'https://en.cppreference.com/w/cpp/named_req/BasicFormatter',
        r'BasicLockables?': r'https://en.cppreference.com/w/cpp/named_req/BasicLockable',
        r'(?:Legacy)?BidirectionalIterators?': r'https://en.cppreference.com/w/cpp/named_req/BidirectionalIterator',
        r'BinaryPredicates?': r'https://en.cppreference.com/w/cpp/named_req/BinaryPredicate',
        r'BinaryTypeTraits?': r'https://en.cppreference.com/w/cpp/named_req/BinaryTypeTrait',
        r'BitmaskTypes?': r'https://en.cppreference.com/w/cpp/named_req/BitmaskType',
        r'Callables?': r'https://en.cppreference.com/w/cpp/named_req/Callable',
        r'CharTraits?': r'https://en.cppreference.com/w/cpp/named_req/CharTraits',
        r'Compares?': r'https://en.cppreference.com/w/cpp/named_req/Compare',
        r'(?:Legacy)?ConstexprIterators?': r'https://en.cppreference.com/w/cpp/named_req/ConstexprIterator',
        r'Containers?': r'https://en.cppreference.com/w/cpp/named_req/Container',
        r'ContiguousContainers?': r'https://en.cppreference.com/w/cpp/named_req/ContiguousContainer',
        r'(?:Legacy)?ContiguousIterators?': r'https://en.cppreference.com/w/cpp/named_req/ContiguousIterator',
        r'CopyAssignables?': r'https://en.cppreference.com/w/cpp/named_req/CopyAssignable',
        r'CopyConstructibles?': r'https://en.cppreference.com/w/cpp/named_req/CopyConstructible',
        r'CopyInsertables?': r'https://en.cppreference.com/w/cpp/named_req/CopyInsertable',
        r'DefaultConstructibles?': r'https://en.cppreference.com/w/cpp/named_req/DefaultConstructible',
        r'DefaultInsertables?': r'https://en.cppreference.com/w/cpp/named_req/DefaultInsertable',
        r'Destructibles?': r'https://en.cppreference.com/w/cpp/named_req/Destructible',
        r'EmplaceConstructibles?': r'https://en.cppreference.com/w/cpp/named_req/EmplaceConstructible',
        r'EqualityComparables?': r'https://en.cppreference.com/w/cpp/named_req/EqualityComparable',
        r'Erasables?': r'https://en.cppreference.com/w/cpp/named_req/Erasable',
        r'FormattedInputFunctions?': r'https://en.cppreference.com/w/cpp/named_req/FormattedInputFunction',
        r'FormattedOutputFunctions?': r'https://en.cppreference.com/w/cpp/named_req/FormattedOutputFunction',
        r'(?:Legacy)?ForwardIterators?': r'https://en.cppreference.com/w/cpp/named_req/ForwardIterator',
        r'FunctionObjects?': r'https://en.cppreference.com/w/cpp/named_req/FunctionObject',
        r'ImplicitLifetimeTypes?': r'https://en.cppreference.com/w/cpp/named_req/ImplicitLifetimeType',
        r'LegacyIterators?': r'https://en.cppreference.com/w/cpp/named_req/LegacyIterator',
        r'(?:Legacy)?InputIterators?': r'https://en.cppreference.com/w/cpp/named_req/InputIterator',
        r'(?:Legacy)?Iterators?': r'https://en.cppreference.com/w/cpp/named_req/Iterator',
        r'LessThanComparables?': r'https://en.cppreference.com/w/cpp/named_req/LessThanComparable',
        r'LiteralTypes?': r'https://en.cppreference.com/w/cpp/named_req/LiteralType',
        r'Lockables?': r'https://en.cppreference.com/w/cpp/named_req/Lockable',
        r'MoveAssignables?': r'https://en.cppreference.com/w/cpp/named_req/MoveAssignable',
        r'MoveConstructibles?': r'https://en.cppreference.com/w/cpp/named_req/MoveConstructible',
        r'MoveInsertables?': r'https://en.cppreference.com/w/cpp/named_req/MoveInsertable',
        r'NullablePointers?': r'https://en.cppreference.com/w/cpp/named_req/NullablePointer',
        r'NumericTypes?': r'https://en.cppreference.com/w/cpp/named_req/NumericType',
        r'(?:Legacy)?OutputIterators?': r'https://en.cppreference.com/w/cpp/named_req/OutputIterator',
        r'PODTypes?': r'https://en.cppreference.com/w/cpp/named_req/PODType',
        r'Predicates?': r'https://en.cppreference.com/w/cpp/named_req/Predicate',
        r'(?:Legacy)?RandomAccessIterators?': r'https://en.cppreference.com/w/cpp/named_req/RandomAccessIterator',
        r'RandomNumberDistributions?': r'https://en.cppreference.com/w/cpp/named_req/RandomNumberDistribution',
        r'RandomNumberEngines?': r'https://en.cppreference.com/w/cpp/named_req/RandomNumberEngine',
        r'RandomNumberEngineAdaptors?': r'https://en.cppreference.com/w/cpp/named_req/RandomNumberEngineAdaptor',
        r'RangeAdaptorClosureObjects?': r'https://en.cppreference.com/w/cpp/named_req/RangeAdaptorClosureObject',
        r'RangeAdaptorObjects?': r'https://en.cppreference.com/w/cpp/named_req/RangeAdaptorObject',
        r'RegexTraitss?': r'https://en.cppreference.com/w/cpp/named_req/RegexTraits',
        r'ReversibleContainers?': r'https://en.cppreference.com/w/cpp/named_req/ReversibleContainer',
        r'ScalarTypes?': r'https://en.cppreference.com/w/cpp/named_req/ScalarType',
        r'SeedSequences?': r'https://en.cppreference.com/w/cpp/named_req/SeedSequence',
        r'SequenceContainers?': r'https://en.cppreference.com/w/cpp/named_req/SequenceContainer',
        r'SharedLockables?': r'https://en.cppreference.com/w/cpp/named_req/SharedLockable',
        r'SharedMutexs?': r'https://en.cppreference.com/w/cpp/named_req/SharedMutex',
        r'SharedTimedLockables?': r'https://en.cppreference.com/w/cpp/named_req/SharedTimedLockable',
        r'SharedTimedMutexs?': r'https://en.cppreference.com/w/cpp/named_req/SharedTimedMutex',
        r'StandardLayoutTypes?': r'https://en.cppreference.com/w/cpp/named_req/StandardLayoutType',
        r'Swappables?': r'https://en.cppreference.com/w/cpp/named_req/Swappable',
        r'TimedLockables?': r'https://en.cppreference.com/w/cpp/named_req/TimedLockable',
        r'TimedMutexs?': r'https://en.cppreference.com/w/cpp/named_req/TimedMutex',
        r'TransformationTraits?': r'https://en.cppreference.com/w/cpp/named_req/TransformationTrait',
        r'TrivialClocks?': r'https://en.cppreference.com/w/cpp/named_req/TrivialClock',
        r'TriviallyCopyables?': r'https://en.cppreference.com/w/cpp/named_req/TriviallyCopyable',
        r'TrivialTypes?': r'https://en.cppreference.com/w/cpp/named_req/TrivialType',
        r'UnaryTypeTraits?': r'https://en.cppreference.com/w/cpp/named_req/UnaryTypeTrait',
        r'UnformattedInputFunctions?': r'https://en.cppreference.com/w/cpp/named_req/UnformattedInputFunction',
        r'UnformattedOutputFunctions?': r'https://en.cppreference.com/w/cpp/named_req/UnformattedOutputFunction',
        r'UniformRandomBitGenerators?': r'https://en.cppreference.com/w/cpp/named_req/UniformRandomBitGenerator',
        r'UnorderedAssociativeContainers?': r'https://en.cppreference.com/w/cpp/named_req/UnorderedAssociativeContainer',
        r'ValueSwappables?': r'https://en.cppreference.com/w/cpp/named_req/ValueSwappable',
        # windows
        r'(?:L?P)?(?:'
        + r'D?WORD(?:32|64|_PTR)?|HANDLE|HMODULE|BOOL(?:EAN)?'
        + r'|U?SHORT|U?LONG|U?INT(?:8|16|32|64)?'
        + r'|BYTE|VOID|C[WT]?STR'
        + r')': r'https://docs.microsoft.com/en-us/windows/desktop/winprog/windows-data-types',
        r'__INTELLISENSE__|_MSC(?:_FULL)_VER|_MSVC_LANG|_WIN(?:32|64)': r'https://docs.microsoft.com/en-us/cpp/preprocessor/predefined-macros?view=vs-2019',
        r'IUnknowns?': r'https://docs.microsoft.com/en-us/windows/win32/api/unknwn/nn-unknwn-iunknown',
        r'(?:IUnknown::)?QueryInterface?': r'https://docs.microsoft.com/en-us/windows/win32/api/unknwn/nf-unknwn-iunknown-queryinterface(q)',
        # unreal engine types
        r'(?:::)?FBox(?:es)?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FBox/index.html',
        r'(?:::)?FBox2Ds?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FBox2D/index.html',
        r'(?:::)?FColors?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FColor/index.html',
        r'(?:::)?FFloat16s?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FFloat16/index.html',
        r'(?:::)?FFloat32s?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FFloat32/index.html',
        r'(?:::)?FMatrix(?:es|ices)?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FMatrix/index.html',
        r'(?:::)?FMatrix2x2s?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FMatrix2x2/index.html',
        r'(?:::)?FOrientedBox(?:es)?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FOrientedBox/index.html',
        r'(?:::)?FPlanes?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FPlane/index.html',
        r'(?:::)?FQuat2Ds?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FQuat2D/index.html',
        r'(?:::)?FQuats?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FQuat/index.html',
        r'(?:::)?FStrings?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Containers/FString/index.html',
        r'(?:::)?FVector2DHalfs?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector2DHalf/index.html',
        r'(?:::)?FVector2Ds?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector2D/index.html',
        r'(?:::)?FVector4s?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector4/index.html',
        r'(?:::)?FVectors?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/FVector/index.html',
        r'(?:::)?TMatrix(?:es|ices)?': r'https://docs.unrealengine.com/en-US/API/Runtime/Core/Math/TMatrix/index.html',
        r'(?:::)?UStaticMesh(?:es)?': r'https://docs.unrealengine.com/4.27/en-US/API/Runtime/Engine/Engine/UStaticMesh/',
        r'(?:::)?FStaticMeshLODResources': r'https://docs.unrealengine.com/4.27/en-US/API/Runtime/Engine/FStaticMeshLODResources/',
        r'(?:::)?FRawStaticIndexBuffer(?:s)?': r'https://docs.unrealengine.com/4.26/en-US/API/Runtime/Engine/FRawStaticIndexBuffer/',
        r'(?:::)?FStaticMeshVertexBuffers': r'https://docs.unrealengine.com/4.27/en-US/API/Runtime/Engine/FStaticMeshVertexBuffers/',
        r'(?:::)?FStaticMeshVertexBuffer': r'https://docs.unrealengine.com/4.27/en-US/API/Runtime/Engine/Rendering/FStaticMeshVertexBuffer/',
        r'(?:::)?FPositionVertexBuffer(?:s)?': r'https://docs.unrealengine.com/4.27/en-US/API/Runtime/Engine/Rendering/FPositionVertexBuffer/',
        r'(?:::)?TArrayView(?:s)?': r'https://docs.unrealengine.com/4.27/en-US/API/Runtime/Core/Containers/TArrayView/',
        r'(?:::)?TArray(?:s)?': r'https://docs.unrealengine.com/4.27/en-US/API/Runtime/Core/Containers/TArray/',
    }
    navbar = (r'files', r'groups', r'namespaces', r'classes', r'concepts')
    navbar_all = (r'pages', *navbar, r'repo', r'theme')
    aliases = {
        # poxy
        r'cpp': r'@code{.cpp}',
        r'ecpp': r'@endcode',
        r'endcpp': r'@endcode',
        r'out': r'@code{.shell-session}',
        r'eout': r'@endcode',
        r'endout': r'@endcode',
        r'python': r'@code{.py}',
        r'epython': r'@endcode',
        r'endpython': r'@endcode',
        r'meson': r'@code{.py}',
        r'emeson': r'@endcode',
        r'endmeson': r'@endcode',
        r'cmake': r'@code{.cmake}',
        r'ecmake': r'@endcode',
        r'endcmake': r'@endcode',
        r'javascript': r'@code{.js}',
        r'ejavascript': r'@endcode',
        r'endjavascript': r'@endcode',
        r'json': r'@code{.js}',
        r'ejson': r'@endcode',
        r'endjson': r'@endcode',
        r'shell': r'@code{.shell-session}',
        r'eshell': r'@endcode',
        r'endshell': r'@endcode',
        r'bash': r'@code{.sh}',
        r'ebash': r'@endcode',
        r'endbash': r'@endcode',
        r'detail': r'@details',
        r'conditional_return{1}': r'<strong><em>\1:</em></strong> ',
        r'inline_attention': r'[set_class m-note m-warning]',
        r'inline_note': r'[set_class m-note m-info]',
        r'inline_remark': r'[set_class m-note m-default]',
        r'inline_subheading{1}': r'[h4]\1[/h4]',
        r'inline_success': r'[set_class m-note m-success]',
        r'inline_warning': r'[set_class m-note m-danger]',
        r'github{1}': r'<a href="https://github.com/\1" target="_blank">\1</a>',
        r'github{2}': r'<a href="https://github.com/\1" target="_blank">\2</a>',
        r'gitlab{1}': r'<a href="https://gitlab.com/\1" target="_blank">\1</a>',
        r'gitlab{2}': r'<a href="https://gitlab.com/\1" target="_blank">\2</a>',
        r'godbolt{1}': r'<a href="https://godbolt.org/z/\1" target="_blank">Try this code on Compiler Explorer</a>',
        r'flags_enum': r'@note This enum is a flags type; it is equipped with a full complement of bitwise operators. ^^',
        r'implementers': r'@par [parent_parent_set_class m-block m-dim][emoji hammer][entity nbsp]Implementers: ',
        r'optional': r'@par [parent_parent_set_class m-block m-info]Optional field ^^',
        r'required': r'@par [parent_parent_set_class m-block m-warning][emoji warning][entity nbsp]Required field ^^',
        r'availability': r'@par [parent_parent_set_class m-block m-special]Conditional availability ^^',
        r'figure{1}': r'@image html \1',
        r'figure{2}': r'@image html \1 "\2"',
        # m.css
        r'm_div{1}': r'@xmlonly<mcss:div xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="\1">@endxmlonly',
        r'm_enddiv': r'@xmlonly</mcss:div>@endxmlonly',
        r'm_span{1}': r'@xmlonly<mcss:span xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="\1">@endxmlonly',
        r'm_endspan': r'@xmlonly</mcss:span>@endxmlonly',
        r'm_class{1}': r'@xmlonly<mcss:class xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:class="\1" />@endxmlonly',
        r'm_footernavigation': r'@xmlonly<mcss:footernavigation xmlns:mcss="http://mcss.mosra.cz/doxygen/" />@endxmlonly',
        r'm_examplenavigation{2}': r'@xmlonly<mcss:examplenavigation xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:page="\1" mcss:prefix="\2" />@endxmlonly',
        r'm_keywords{1}': r'@xmlonly<mcss:search xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:keywords="\1" />@endxmlonly',
        r'm_keyword{3}': r'@xmlonly<mcss:search xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:keyword="\1" mcss:title="\2" mcss:suffix-length="\3" />@endxmlonly',
        r'm_enum_values_as_keywords': r'@xmlonly<mcss:search xmlns:mcss="http://mcss.mosra.cz/doxygen/" mcss:enum-values-as-keywords="true" />@endxmlonly',
    }
    source_patterns = {
        r'*.h',
        r'*.hh',
        r'*.hxx',
        r'*.hpp',
        r'*.h++',
        r'*.ixx',
        r'*.inc',
        r'*.markdown',
        r'*.md',
        r'*.dox',
    }
    # code block syntax highlighting only
    #
    # note: we don't need to be comprehensive for the std namespace symbols;
    # those will get added from the cppreference tagfile
    cb_enums = {r'(?:std::)?ios(?:_base)?::(?:app|binary|in|out|trunc|ate)'}
    cb_macros = {
        # standard builtins:
        r'__cplusplus(?:_cli|_winrt)?',
        r'__cpp_[a-zA-Z_]+?',
        r'__has_(?:(?:cpp_)?attribute|include)',
        r'assert',
        r'offsetof',
        # poxy:
        r'POXY_[a-zA-Z_]+',
        # compiler builtins:
        regex_trie(
            # standard:
            r'__FILE__',
            r'__LINE__',
            r'__DATE__',
            r'__TIME__',
            r'__STDC__',
            r'__STDC_HOSTED__',
            r'__STDC_VERSION__',
            r'__STDC_ISO_10646__',
            r'__STDC_MB_MIGHT_NEQ_WC__',
            r'__STDCPP_THREADS__',
            r'__STDCPP_DEFAULT_NEW_ALIGNMENT__',
            r'__STDCPP_STRICT_POINTER_SAFETY__',
            # msvc:
            r'_ATL_VER',  #
            r'_CHAR_UNSIGNED',
            r'_CONTROL_FLOW_GUARD',
            r'_CPPRTTI',
            r'_CPPUNWIND',
            r'_DEBUG',
            r'_DLL',
            r'_INTEGRAL_MAX_BITS',
            r'_ISO_VOLATILE',
            r'_KERNEL_MODE',
            r'_MANAGED',
            r'_MFC_VER',
            r'_MSC_BUILD',
            r'_MSC_EXTENSIONS',
            r'_MSC_FULL_VER',
            r'_MSC_VER',
            r'_MSVC_LANG',
            r'_MSVC_TRADITIONAL',
            r'_MT',
            r'_M_AMD64',
            r'_M_ARM',
            r'_M_ARM64',
            r'_M_ARM64EC',
            r'_M_ARM_ARMV7VE',
            r'_M_ARM_FP',
            r'_M_CEE',
            r'_M_CEE_PURE',
            r'_M_CEE_SAFE',
            r'_M_FP_CONTRACT',
            r'_M_FP_EXCEPT',
            r'_M_FP_FAST',
            r'_M_FP_PRECISE',
            r'_M_FP_STRICT',
            r'_M_IX86',
            r'_M_IX86_FP',
            r'_M_X64',
            r'_NATIVE_WCHAR_T_DEFINED',
            r'_OPENMP',
            r'_PREFAST_',
            r'_VC_NODEFAULTLIB',
            r'_WCHAR_T_DEFINED',
            r'_WIN32',
            r'_WIN64',
            r'_WINRT_DLL',
            r'__ATOM__',
            r'__AVX2__',
            r'__AVX512BW__',
            r'__AVX512CD__',
            r'__AVX512DQ__',
            r'__AVX512F__',
            r'__AVX512VL__',
            r'__AVX__',
            r'__CLR_VER',
            r'__COUNTER__',
            r'__FUNCDNAME__',
            r'__FUNCSIG__',
            r'__FUNCTION__',
            r'__INTELLISENSE__',
            r'__MSVC_RUNTIME_CHECKS',
            r'__SANITIZE_ADDRESS__',
            r'__STDC_NO_ATOMICS__',
            r'__STDC_NO_COMPLEX__',
            r'__STDC_NO_THREADS__',
            r'__STDC_NO_VLA__',
            r'__TIMESTAMP__',
            r'__cplusplus_cli',
            r'__cplusplus_winrt',
            r'NDEBUG',
            r'_DEBUG',
        ),
    }
    cb_namespaces = {
        regex_trie(
            r'std',
            r'std::chrono',
            r'std::execution',
            r'std::filesystem',
            r'std::experimental',
            r'std::numbers',
            r'std::literals',
            r'std::literals::chrono_literals',
            r'std::literals::complex_literals',
            r'std::literals::string_literals',
            r'std::literals::string_view_literals',
            r'std::chrono_literals',
            r'std::complex_literals',
            r'std::string_literals',
            r'std::string_view_literals',
            r'std::ranges',
            r'std::this_thread',
        )
    }
    cb_types = {
        # ------ built-in types
        r'__(?:float|fp)[0-9]{1,3}',
        r'__m[0-9]{1,3}[di]?',
        r'_Float[0-9]{1,3}',
        r'[a-zA-Z_][a-zA-Z_0-9]*_t(?:ype(?:def)?|raits)?',
        regex_trie(r'bool', r'char', r'double', r'float', r'int', r'long', r'short', r'signed', r'unsigned'),
        # ------ documentation-only types
        r'(?:[a-zA-Z][a-zA-Z_]+::)*?(?:[a-zA-Z][a-zA-Z_]+_type|Foo|Bar|[Vv]ec(?:tor)?[1-4][hifd]?|[Mm]at(?:rix)?[1-4](?:[xX][1-4])?[hifd]?)',
        r'[S-Z][0-9]?',
    }
    cb_functions = {regex_trie(r'std::as_const', r'std::move', r'std::forward')}


def extract_kvps(
    config,
    table,
    key_getter=str,
    value_getter=str,
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


class Warnings(object):
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


class CodeBlocks(object):
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
                for t in coerce_collection(config['types']):
                    type_ = t.strip()
                    if type_:
                        self.types.add(type_)

            if 'macros' in config:
                for m in coerce_collection(config['macros']):
                    macro = m.strip()
                    if macro:
                        self.macros.add(macro)

            if 'enums' in config:
                for e in coerce_collection(config['enums']):
                    enum = e.strip()
                    if enum:
                        self.enums.add(enum)

            if 'namespaces' in config:
                for ns in coerce_collection(config['namespaces']):
                    namespace = ns.strip()
                    if namespace:
                        self.namespaces.add(namespace)

            if 'functions' in config:
                for f in coerce_collection(config['functions']):
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


class Inputs(object):
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
            for s in coerce_collection(config[r'ignore']):
                ignore = s.strip()
            ignores = [re.compile(i) for i in ignores]
        for ignore in ignores:
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
            for v in coerce_collection(config[r'patterns']):
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

        if key not in config:
            return
        config = config[key]

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
            for s in coerce_collection(config[r'strip_includes']):
                path = s.strip().replace('\\', '/')
                if path:
                    self.strip_includes.append(path)
            self.strip_includes.sort(key=lambda v: len(v), reverse=True)

        if r'extract_all' in config:
            self.extract_all = bool(config['extract_all'])


# =======================================================================================================================
# project context
# =======================================================================================================================


class Context(object):
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
            Optional(r'private_repo'): bool,
            Optional(r'robots'): bool,
            Optional(r'scripts'): ValueOrArray(str, name=r'scripts'),
            Optional(r'show_includes'): bool,
            Optional(r'sources'): Sources.schema,
            Optional(r'stylesheets'): ValueOrArray(str, name=r'stylesheets'),
            Optional(r'tagfiles'): {str: str},
            Optional(r'theme'): Or(r'dark', r'light', r'custom'),
            Optional(r'warnings'): Warnings.schema,
        },
        ignore_extra_keys=True,
    )
    __namespace_qualified = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*::.+$")

    def is_verbose(self):
        return self.__verbose

    def __log(self, level, msg, indent=None):
        if msg is None:
            return
        msg = str(msg).strip(r'\r\n\v\f')
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

    def warning(self, msg, indent=None):
        if self.warnings.treat_as_errors:
            raise WarningTreatedAsError(msg)
        else:
            self.__log(logging.WARNING, rf'Warning: {msg}', indent=indent)

    def verbose_value(self, name, val):
        if not self.__verbose:
            return
        with io.StringIO() as buf:
            print(rf'{name+": ":<35}', file=buf, end='')
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
        config_path: Path,
        output_dir: Path,
        output_html: bool,
        output_xml: bool,
        threads: int,
        cleanup: bool,
        verbose: bool,
        logger,
        html_include: str,
        html_exclude: str,
        treat_warnings_as_errors: bool,
        theme: str,
        copy_assets: bool,
        temp_dir: Path = None,
        bug_report: bool = False,
        **kwargs,
    ):
        self.logger = logger
        self.__verbose = bool(verbose)
        self.output_html = bool(output_html)
        self.output_xml = bool(output_xml)
        self.cleanup = bool(cleanup)
        self.copy_assets = bool(copy_assets)
        self.verbose_logger = logger if self.__verbose else None
        self.bug_report = bool(bug_report)

        self.info(rf'Poxy v{VERSION_STRING}')

        self.verbose_value(r'Context.output_html', self.output_html)
        self.verbose_value(r'Context.output_xml', self.output_xml)
        self.verbose_value(r'Context.cleanup', self.cleanup)

        threads = int(threads) if threads is not None else 0
        if threads <= 0:
            threads = os.cpu_count()
        self.threads = max(1, min(os.cpu_count(), threads))
        self.verbose_value(r'Context.threads', self.threads)

        # additional kwargs (experimental stuff etc)
        self.xml_v2 = bool(kwargs[r'xml_v2']) if r'xml_v2' in kwargs else False
        self.verbose_value(r'Context.xml_v2', self.xml_v2)

        # these are overridden/initialized elsewhere; they're here so duck-typing still quacks
        self.fixers = []
        self.compound_pages = dict()
        self.compound_kinds = set()

        # initial warning state
        # note that this is overwritten after the config is read;
        # it is set here first so that we can have correct 'treat_as_errors' behaviour if we add any pre-config warnings
        self.warnings = Warnings(None)
        if treat_warnings_as_errors is not None:
            self.warnings.treat_as_errors = bool(treat_warnings_as_errors)

        if html_include is not None:
            html_include = re.compile(str(html_include))
        self.html_include = html_include
        if html_exclude is not None:
            html_exclude = re.compile(str(html_exclude))
        self.html_exclude = html_exclude

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
            self.case_sensitive_paths = not (
                Path(str(paths.PACKAGE).upper()).exists() and Path(str(paths.PACKAGE).lower()).exists()
            )
            self.verbose_value(r'Context.case_sensitive_paths', self.case_sensitive_paths)

            # config path
            self.config_path = Path(r'poxy.toml').resolve()
            if config_path is not None:
                self.config_path = coerce_path(config_path).resolve()
                if self.config_path.exists() and self.config_path.is_dir():
                    self.config_path = Path(self.config_path, r'poxy.toml')
                if not self.config_path.exists() or not self.config_path.is_file():
                    raise Error(rf"Config '{self.config_path}' did not exist or was not a file")
                if self.bug_report:
                    copy_file(self.config_path, paths.BUG_REPORT_DIR)
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
                self.temp_dir = re.sub(r'''[!@#$%^&*()+={}<>;:'"_\\/\n\t -]+''', r'_', str(self.input_dir).strip(r'\/'))
                if len(self.temp_dir) > 256:
                    self.temp_dir = str(self.input_dir)
                    if not self.case_sensitive_paths:
                        self.temp_dir = self.temp_dir.upper()
                    self.temp_dir = sha1(self.temp_dir)
                self.temp_dir = Path(paths.TEMP, self.temp_dir)
            self.verbose_value(r'Context.temp_dir', self.temp_dir)
            assert self.temp_dir.is_absolute()

            # temp pages dir
            self.temp_pages_dir = Path(self.temp_dir, r'pages')
            self.verbose_value(r'Context.pages_dir', self.temp_pages_dir)
            assert self.temp_pages_dir.is_absolute()

            # temp xml output path used by doxygen
            self.temp_xml_dir = Path(self.temp_dir, r'xml')
            self.verbose_value(r'Context.temp_xml_dir', self.temp_xml_dir)
            assert self.temp_xml_dir.is_absolute()

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
        if 1:
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
                    raise Error(rf'{TYPE.KEY}: {err}')
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
                for f in coerce_collection(config[r'stylesheets']):
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
                for f in coerce_collection(config[r'scripts']):
                    file = f.strip()
                    if file:
                        if is_uri(file):
                            self.scripts.append(file)
                        else:
                            file = Path(file)
                            self.scripts.append(file.name)
                            extra_files.append(file)
            self.verbose_value(r'Context.scripts', self.scripts)

            # enumerate blog files (need to add them to the doxygen sources)
            self.blog_files = []
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
                        raise Error(rf"failed to parse date from blog post filename '{f.name}': {str(exc)}")
            self.verbose_value(r'Context.blog_files', self.blog_files)

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
                            for name, ext, lower in itertools.product(
                                candidate_names, candidate_extensions, as_lowercase
                            ):
                                candidate_file = Path(candidate_dir, rf'{name.lower() if lower else name}{ext}')
                                if (
                                    candidate_file.exists()
                                    and candidate_file.is_file()
                                    and candidate_file.stat().st_size <= 1024 * 1024 * 2
                                ):
                                    self.changelog = candidate_file
                                    break
                            if (
                                self.changelog
                                or candidate_dir.parent == candidate_dir
                                or (candidate_dir / '.git').exists()
                            ):
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
                            for name, ext, lower in itertools.product(
                                candidate_names, candidate_extensions, as_lowercase
                            ):
                                candidate_file = Path(candidate_dir, rf'{name.lower() if lower else name}{ext}')
                                if (
                                    candidate_file.exists()
                                    and candidate_file.is_file()
                                    and candidate_file.stat().st_size <= 1024 * 1024 * 2
                                ):
                                    self.main_page = candidate_file
                                    break
                            if (
                                self.main_page
                                or candidate_dir.parent == candidate_dir
                                or (candidate_dir / '.git').exists()
                            ):
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
            self.verbose_value(r'Context.main_page', self.main_page)

            # sources (INPUT, FILE_PATTERNS, STRIP_FROM_PATH, STRIP_FROM_INC_PATH, EXTRACT_ALL)
            self.sources = Sources(
                config,
                r'sources',
                self.input_dir,
                additional_inputs=(
                    self.temp_pages_dir,  #
                    self.changelog if self.changelog else None,
                    *[f for f, d in self.blog_files],
                ),
                additional_strip_paths=(self.temp_pages_dir,),
            )
            self.verbose_object(r'Context.sources', self.sources)

            # images (IMAGE_PATH)
            self.images = Inputs(
                config,
                r'images',
                self.input_dir,
                additional_recursive_inputs=[self.blog_dir if self.blog_files else None],
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
            self.tagfiles = {self.cppref_tagfile: (self.cppref_tagfile, r'http://en.cppreference.com/w/')}
            self.unresolved_tagfiles = False
            for k, v in extract_kvps(config, 'tagfiles').items():
                source = str(k)
                dest = str(v)
                if source and dest:
                    if is_uri(source):
                        file = Path(
                            paths.TEMP, rf'tagfile_{sha1(source)}_{self.now.year}_{self.now.isocalendar().week}.xml'
                        )
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

            # navbar
            if 1:
                # initialize
                self.navbar = []
                if r'navbar' in config:
                    for v in coerce_collection(config['navbar']):
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
                for ns in coerce_collection(config['inline_namespaces']):
                    namespace = ns.strip()
                    if namespace:
                        self.inline_namespaces.add(namespace)
            self.verbose_value(r'Context.inline_namespaces', self.inline_namespaces)

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
                    impls = coerce_collection(v)
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
                self.temp_dir, rf'{self.name.replace(" ","_")}.tagfile.xml' if self.name else r'tagfile.xml'
            )
            if r'generate_tagfile' in config:
                self.generate_tagfile = bool(config[r'generate_tagfile'])
            self.verbose_value(r'Context.generate_tagfile', self.generate_tagfile)

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
                    v = coerce_collection(v)
                    image_uri = v[0].strip()
                    anchor_uri = v[1].strip() if len(v) > 1 else r''
                    if text and image_uri:
                        user_badges.append((text, image_uri, anchor_uri))
            user_badges.sort(key=lambda b: b[0])
            self.badges = tuple(badges + user_badges)
            self.verbose_value(r'Context.badges', self.badges)

            # user-specified extra_files (HTML_EXTRA_FILES)
            if r'extra_files' in config:
                for f in coerce_collection(config['extra_files']):
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

        # init emoji db
        self.emoji = emoji.Database()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.cleanup:
            delete_directory(self.temp_dir, logger=self.verbose_logger)

    def __bool__(self):
        return True


__all__ = ['Context']
