// undocumented file holding a documented global: the file page should survive to carry it.

#pragma once

/// @brief A documented global function in an undocumented file.
void global_documented_function();

// fully undocumented global: should stay pruned
void undocumented_global_function();
