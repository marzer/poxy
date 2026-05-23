#pragma once

/// @file
/// detail header b (references things from a.hpp to exercise inter-document links)

#include "detail/a.hpp"

namespace foo
{
	/// A gadget that owns a #foo::widget. See also make_widget().
	struct gadget
	{
		widget w; ///< the owned widget
	};

	/// Makes a gadget from a widget.
	/// @see make_widget(), IMPL_ANSWER
	gadget make_gadget(widget const& w);
}
