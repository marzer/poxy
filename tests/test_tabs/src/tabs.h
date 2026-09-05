#pragma once

/// @brief A namespace documented with a tabbed code example.
/// @details Here is the same idea in two languages:
///
/// @tabs
///
/// @tab{C++}
/// @cpp
/// auto greet()
/// {
///     return "hello";
/// }
/// @endcpp
///
/// @tab{Python}
/// @python
/// def greet():
///     return "hello"
/// @endpython
///
/// @endtabs
namespace tabs
{
	/// @brief A function with a tabbed example mixing prose and code.
	/// @details
	///
	/// @tabs
	///
	/// @tab{Usage}
	///
	/// Call it like so:
	///
	/// @cpp
	/// auto x = tabs::func();
	/// @endcpp
	///
	/// @tab{Notes}
	///
	/// Just returns a number. Nothing to see here.
	///
	/// @tab{Video}
	///
	/// @youtube{dQw4w9WgXcQ,a demonstration}
	///
	/// @endtabs
	int func();
}
