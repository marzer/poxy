/// \file
/// \brief Code, yo.
/// \details More info.

#include <concepts>

/// \brief A namespace.
/// \details More info.
namespace test
{
	/// \brief An inline variable.
	/// \details More info.
	inline constexpr bool inline_variable = false;

	/// \brief A struct.
	/// \details More info.
	struct struct_1
	{
		/// \brief A static variable.
		/// \details More info.
		static constexpr bool static_variable = false;

		/// \brief A nested struct.
		/// \details More info.
		struct nested_struct
		{};
	};

	/// \brief A class.
	/// \details More info.
	class class_1
	{};

	/// \brief A template class.
	/// \details More info.
	/// \tparam T A type.
	template <typename T>
	class template_class_1
	{};

	/// \brief A concept.
	/// \details More info.
	/// \tparam T A type.
	template <typename T>
	concept concept_1 = requires(T a) {
							{
								std::hash<T>{}(a)
								} -> std::convertible_to<std::size_t>;
						};

	/// \brief Another namespace.
	namespace nested
	{
		/// \brief A concept.
		/// \details More info.
		/// \tparam T A type.
		template <typename T>
		concept concept_2 = requires(T a) {
								{
									std::hash<T>{}(a)
									} -> std::convertible_to<std::size_t>;
							};
	}

	/// \brief An empty namespace.
	/// \details More info.
	namespace empty
	{
	}

	/// \brief A pre-C++11 unscoped enum.
	/// \details More info.
	enum unscoped_enum
	{
		LEGACY_ENUM_VAL_0,	   ///< Value zero.
		LEGACY_ENUM_VAL_1 = 1, ///< Value one.

		/// \brief Value two.
		LEGACY_ENUM_VAL_2 = 2
	};

	/// \brief A C++11 scoped enum.
	/// \details More info.
	enum scoped_enum
	{
		val_0,	   ///< Value zero.
		val_1 = 1, ///< Value one.

		/// \brief Value two.
		val_2 = 2
	};
}
