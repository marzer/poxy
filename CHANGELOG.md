# Changelog

## v0.5.4 - 2022-04-15
- Updated m.css
- Updated emoji database

## v0.5.3 - 2021-12-12
- Fixed Doxygen bug that would sometimes treat keywords like `friend` as part of a function's return type
- Blacklisted schema 0.7.5 because [it's broken](https://github.com/keleshev/schema/issues/272)

## v0.5.2 - 2021-11-02
- Fixed over-eager link-replacement for internal `#anchor` links
- Added command-line options `--ppinclude` and `--ppexclude`

## v0.5.1 - 2021-10-09
- Fixed over-eager link replacement causing text to be deleted

## v0.5.0 - 2021-09-11
- Fixed a crash during HTML post-processing
- Fixed `implementation_headers` not working when paths use backslashes
- Added warnings when `implementation_headers` doesn't match anything

## v0.4.5 - 2021-06-08
- Added command-line option `--xmlonly`

## v0.4.3 - 2021-05-31
- Fixed regression in `[code_blocks]` functionality
- Fixed minor issues in syntax highlighter
- Added symbols from doxygen tagfiles to the syntax highlighter
- Minor style tweaks

## v0.4.1 - 2021-05-30
- Fixed `.dirs` being glommed as source paths
- Added config option `scripts`
- Added config option `stylesheets`
- Added config option `jquery`
- Added `custom` theme
- Added ability to use `HOME.md` as main page
- Added additional fix for inline `<code>` blocks
- Added `.poxy-toc` to table-of-contents elements
- Added floating page table-of-contents
- Removed m.css favicon fallback
- Made improvements to the `light` and `dark` themes
- Updated C++ doxygen tagfile

## v0.4.0 - 2021-05-29
- Added config option `theme`
- Added version number to CSS and javascript filenames to prevent browser cache issues
- Added `POXY_IMPLEMENTATION_DETAIL(...)` magic macro
- Added `POXY_IGNORE(...)` magic macro
- Fixed alignment of nested images inside detail blocks

## v0.3.4 - 2021-05-28
- Added basic `using` alias detection to syntax highlighter
- Added missing badges for C++23, 26 and 29

## v0.3.3 - 2021-05-23
- Fixed sorting of namespace and group members
- Fixed m.css failing with new versions of doxygen due to `Doxyfile.xml`
- Added google structured data to `\pages`

## v0.3.2 - 2021-05-19
- Fixed formatting of `<meta>` tags
- Added config option `author`
- Added config option `robots`
- Added markup tag `[p]`
- Added markup tag `[center]`

## v0.3.1 - 2021-05-13
- Added config option `macros`
- Added command-line option `--version`

## v0.3.0 - 2021-05-09
- Improved handling of m.css and Doxygen warnings and errors
- Added command-line option `--doxygen`
- Added command-line option `--werror`
- Added markup tag `[set_parent_class]`
- Added markup tag `[add_parent_class]`
- Added markup tag `[remove_parent_class]`
- Added config option `images`
- Added config option `examples`
- Added ability to specify tagfiles as URIs

## v0.2.1 - 2021-05-07
- Fixed some minor autolinking issues

## v0.2.0 - 2021-05-06
- Added config option `source_patterns`

## v0.1.2 - 2021-05-02
- Fixed the Z-order of the nav bar being higher than the search overlay
- Added `NDEBUG` to the default set of defines

## v0.1.1 - 2021-04-26
- Added an additional cleanup step to the HTML postprocessor

## v0.1.0 - 2021-04-26
First public release :tada:
