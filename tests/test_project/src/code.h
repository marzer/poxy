/// \file
/// \brief Code, yo.
/// \details More info.

#include <concepts>

/// \brief A namespace.
/// \details More info.
namespace test1
{

	/// \brief A foo.
	/// \details More info.
	struct foo
	{
		/// \brief A bar.
		/// \details More info.
		/// \tparam T A type.
		template <typename T>
		class bar
		{};

		/// \brief A concept.
		/// \details More info.
		/// \tparam T A type.
		template <typename T>
		concept concept1 = requires(T a) {
							{
								std::hash<T>{}(a)
								} -> std::convertible_to<std::size_t>;
						};
	};

	/// \brief A concept.
	/// \details More info.
	/// \tparam T A type.
	template <typename T>
	concept concept2 = requires(T a) {
						   {
							   std::hash<T>{}(a)
							   } -> std::convertible_to<std::size_t>;
					   };

	/// \brief Another namespace.
	namespace test2
	{
		/// \brief A concept.
		/// \details More info.
		/// \tparam T A type.
		template <typename T>
		concept concept3 = requires(T a) {
							{
								std::hash<T>{}(a)
								} -> std::convertible_to<std::size_t>;
						};
	}

	/// \brief A empty namespace.
	/// \details More info.
	namespace empty
	{}
}
