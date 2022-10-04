/// \file
/// \brief Code, yo.
/// \details More info.

#include <concepts>

/// \brief A namespace.
/// \details More info.
namespace test
{
	/// \brief A struct.
	/// \details More info.
	struct struct_1
	{
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
}
