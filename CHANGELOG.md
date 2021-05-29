# Changelog

## v0.4.0 - 2020-05-29
- Added config option `theme`
- Added version number to CSS and javascript filenames to prevent browser cache issues
- Added `POXY_IMPLEMENTATION_DETAIL(...)` magic macro
- Added `POXY_IGNORE(...)` magic macro
- Fixed alignment of nested images inside detail blocks

## v0.3.4 - 2020-05-28
- Added basic `using` alias detection to syntax highlighter
- Added missing badges for C++23, 26 and 29

## v0.3.3 - 2020-05-23
- Fixed sorting of namespace and group members
- Fixed m.css failing with new versions of doxygen due to `Doxyfile.xml`
- Added google structured data to `\pages`

## v0.3.2 - 2020-05-19
- Fixed formatting of `<meta>` tags
- Added config option `author`
- Added config option `robots`
- Added markup tag `[p]`
- Added markup tag `[center]`

## v0.3.1 - 2020-05-13
- Added config option `macros`
- Added command-line option `--version`

## v0.3.0 - 2020-05-09
- Improved handling of m.css and Doxygen warnings and errors
- Added command-line option `--doxygen`
- Added command-line option `--werror`
- Added markup tag `[set_parent_class]`
- Added markup tag `[add_parent_class]`
- Added markup tag `[remove_parent_class]`
- Added config option `images`
- Added config option `examples`
- Added ability to specify tagfiles as URIs

## v0.2.1 - 2020-05-07
- Fixed some minor autolinking issues

## v0.2.0 - 2020-05-06
- Added config option `source_patterns`

## v0.1.2 - 2020-05-02
- Fixed the Z-order of the nav bar being higher than the search overlay
- Added `NDEBUG` to the default set of defines

## v0.1.1 - 2020-04-26
- Added an additional cleanup step to the HTML postprocessor

## v0.1.0 - 2020-04-26
First public release :tada:
