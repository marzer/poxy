#pragma once

/// @file
/// detail header a (should be presented as if part of foo.hpp)

/// The answer to life, the universe and everything.
#define IMPL_ANSWER 42

/// The project's namespace.
namespace foo
{
	/// A widget.
	struct widget
	{
		int value; ///< the widget's value
	};

	/// Makes a widget.
	widget make_widget();
}
