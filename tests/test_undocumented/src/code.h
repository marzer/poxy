/// @file
/// @brief Documented file holding the scoped (namespace/class) cases.

#pragma once

// undocumented namespace containing documented + undocumented children
namespace outer
{
	/// @brief A documented class inside an undocumented namespace.
	/// @details It should survive, and 'outer' should survive to carry it.
	class documented_child
	{
	  public:
		/// @brief A documented method.
		void method();
	};

	// undocumented class with a documented member: should survive (member docs would be lost otherwise)
	class undocumented_with_member
	{
	  public:
		/// @brief A documented method in an undocumented class.
		void documented_method();
	};

	// fully undocumented class: should stay pruned
	class fully_undocumented
	{
	  public:
		void undocumented_method();
	};

	// transitively-undocumented nesting: both namespaces undocumented, deepest class documented
	namespace middle
	{
		namespace inner
		{
			/// @brief A deeply nested documented class.
			class deep
			{};
		}
	}
}

namespace test
{
	/// @brief A documented enum whose values are all undocumented.
	/// @details The enumerator table should still render.
	enum class all_values_undocumented
	{
		red,
		green,
		blue
	};

	/// @brief A documented enum with a single documented value.
	enum class some_values_undocumented
	{
		circle, ///< A round one.
		square,
		triangle
	};

	// fully undocumented enum: should stay pruned
	enum class fully_undocumented_enum
	{
		alpha,
		beta
	};
}
