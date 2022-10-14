/// \file
/// \brief Code, yo.
/// \details More info.

/// \brief A macro.
/// \details More info.
#define KEK 1

#include <concepts>
#include <vector>

/// \brief A namespace.
/// \details More info. Here's some C++: \code{cpp}
/// int foo()
/// {
///     return 42_a_numeric_udl;
/// }
///
/// const char* bar() noexcept
/// {
///     return ""_a_string_udl;
/// }
/// \endcode
namespace test
{
	/// \brief A function that appears as a friend to a #test::class_1.
	/// \details More info.
	void a_friend_function();

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

		/// \brief A C++11 scoped enum.
		/// \details More info.
		enum class nested_enum
		{
			val_0,	   ///< Value zero.
			val_1 = 1, ///< Value one.

			/// \brief Value two.
			val_2 = 2
		};
	};

	/// \brief A class.
	/// \details More info.
	class class_1
	{
		friend struct struct_1;
		friend void a_friend_function();

	  public:
		/// \brief A public static variable.
		/// \details More info.
		static constexpr std::byte public_static_variable = {};

		/// \brief A public variable.
		/// \details More info.
		bool public_variable;

		/// \brief A public static function.
		/// \details More info.
		static constexpr struct_1 public_static_function();

		/// \brief A public function.
		/// \details More info.
		bool public_function();

		/// \brief A public typedef.
		/// \details More info.
		using public_typedef = int;

		/// \brief A friend function defined entirely in a class.
		/// \details More info.
		friend void another_friend_function()
		{}

	  protected:
		/// \brief A protected static variable.
		/// \details More info.
		static constexpr bool protected_static_variable = false;

		/// \brief A protected variable.
		/// \details More info.
		bool protected_variable;

		/// \brief A protected static function.
		/// \details More info.
		static constexpr bool protected_static_function();

		/// \brief A protected function.
		/// \details More info.
		bool protected_function();

		/// \brief A protected typedef.
		/// \details More info.
		using protected_typedef = int;

	  private:
		/// \brief A private static variable.
		/// \details More info.
		static constexpr bool private_static_variable = false;

		/// \brief A private variable.
		/// \details More info.
		bool private_variable;

		/// \brief A private static function.
		/// \details More info.
		static constexpr bool private_static_function();

		/// \brief A private function.
		/// \details More info.
		bool private_function();

		/// \brief A private  typedef.
		/// \details More info.
		using private_typedef = int;
	};

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
	enum class scoped_enum : unsigned
	{
		val_0,	   ///< Value zero.
		val_1 = 1, ///< Value one.

		/// \brief Value two.
		val_2 = 2
	};

	/// \brief A function.
	/// \details More info.
	std::uint8_t do_the_thing();

	/// \brief A function template.
	/// \details More info.
	/// \tparam T A type.
	/// \tparam U Another type.
	/// \param u An argument.
	/// \returns A T.
	template <typename T, typename U>
	constexpr T do_the_other_thing(U u) noexcept
	{
		return T{};
	}

	/// \brief A function with a trailing return type
	/// \details More info.
	auto do_the_thing_automatically() -> int;

	/// \brief An old-school typedef.
	/// \details More info.
	typedef int a_shit_typedef;

	/// \brief A C++11 'using' typedef.
	/// \details More info.
	using a_typedef = int;

	/// \brief A C++11 'using' typedef template.
	/// \details More info.
	template <typename T>
	using a_typedef_template = T;
}
