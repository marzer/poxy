# Changelog

## v0.12.1 - 2022-11-22

-   fixed `github` and `gitlab` config options not accepting periods (`.`)

## v0.12.0 - 2022-11-13

-   fixed `AttributeError` during XML post-processing (#17) (@wroyca)
-   added command-line option `--bug-report`
-   improved diagnostic text in some areas

## v0.11.1 - 2022-10-23

-   fixed crash when using `<a>` tags in navbar

## v0.11.0 - 2022-10-21

-   added syntax highlighting for functions
-   improved syntax highlighting of typenames

## v0.10.2 - 2022-10-16

-   fixed crash when tagfile is disabled
-   fixed a few syntax highlighting edge-cases
-   fixed non-determinism in XML output formatting
-   improved performance of syntax highlighting post-process
-   minor style fixes

## v0.10.1 - 2022-10-15

-   minor style fixes

## v0.10.0 - 2022-10-14

-   fixed `static` keyword sometimes appearing twice on variables
-   fixed `constexpr` keyword sometimes leaking into variable type
-   fixed newer versions of pygments adding unnecessary markup to whitespace
-   fixed malformed trailing return types in some circumstances
-   fixed changelog page sometimes not having a table-of-contents
-   added support for C++20's `constinit`
-   added fallback to `tomllib` or `tomli` if `pytomlpp` is not available
-   added command-line options `--html`, `--no-html`
-   added command-line options `--xml`, `--no-xml`
-   added command-line option `--no-werror`
-   added `CHANGES` to the set of candidate changelog filenames
-   deprecated command-line option `--xmlonly`
-   removed command-line option `--doxygen`

## v0.9.1 - 2022-10-04

-   fixed SVG inlining not preserving original image class attributes
-   fixed `ValueError` when reading some SVG files
-   fixed `navbar` option allowing duplicates
-   fixed custom navbar items always being transformed to lowercase
-   fixed navbar generating links to empty pages
-   added `concepts` to the default set of links in `navbar`
-   added `navbar` values `all` and `default`
-   reduced I/O churn during HTML post-processing
-   removed command-line option `--dry`

## v0.9.0 - 2022-10-03

-   added support for C++20 concepts

## v0.8.2 - 2022-10-01

-   added post-process to inline all local SVGs
-   minor style fixes

## v0.8.1 - 2022-09-30

-   minor style fixes

## v0.8.0 - 2022-09-29

-   added config option `gitlab` (#13) (@wroyca)
-   added ixx module extension in source patterns (#11) (@wroyca)
-   added support for multi-codepoint emojis
-   improved `doxygen.exe` location discovery on Windows
-   improved `CHANGELOG` location discovery
-   moved all poxy assets in the generated HTML to `html/poxy`
-   self-hosted google fonts in generated HTML (instead of requiring additional HTTP requests on page load) (#6)
-   removed ability to override m.css implementation
-   removed legacy support for reading config options from neighbouring Doxyfiles
-   overhauled the light theme
-   many minor style fixes and tweaks

## v0.7.1 - 2022-08-17

-   fixed crash on python &lt;= 3.8 (#9) (@wroyca)

## v0.7.0 - 2022-08-16

-   fixed some `<link>`, `<meta>` and `<script>` tags not being included in `<head>` when a file was excluded from post-processing
-   added `theme` command-line option
-   added `html_header` config option option
-   added automatic generation of github links in changelog when config option `github` is set
-   added new light theme
-   added dynamic switch for dark/light theme
-   removed text from github icon on navbar (#5) (@wroyca)
-   removed excessive spacing between article sections (#5) (@wroyca)
-   many minor style fixes and tweaks

## v0.6.1 - 2022-08-16

-   fixed multi-row navbar occluding page content (#3) (@wroyca)

## v0.6.0 - 2022-08-14

-   fixed malformed error messages in some circumstances
-   added builtin C++ standard macros for C++23
-   added `changelog` config option
-   updated cppreference.com tagfile

## v0.5.7 - 2022-05-17

-   fixed being able to pass >= 33 threads to Doxygen's `NUM_PROC_THREADS`

## v0.5.6 - 2022-05-14

-   fixed path error when using `--dry`
-   fixed `friend` keyword sometimes leaking into function return types
-   added additional language code block aliases
-   added `--nocleanup` to `--help` output
-   added support for C++20's `consteval` keyword

## v0.5.5 - 2022-04-16

-   fixed C++20 concepts causing a crash in m.css (they are now skipped with a warning) (#1) (@jake-arkinstall)

## v0.5.4 - 2022-04-15

-   updated m.css
-   updated emoji database

## v0.5.3 - 2021-12-12

-   fixed Doxygen bug that would sometimes treat keywords like `friend` as part of a function's return type
-   Blacklisted schema 0.7.5 because [it's broken](https://github.com/keleshev/schema/issues/272)

## v0.5.2 - 2021-11-02

-   fixed over-eager link-replacement for internal `#anchor` links
-   added command-line options `--ppinclude` and `--ppexclude`

## v0.5.1 - 2021-10-09

-   fixed over-eager link replacement causing text to be deleted

## v0.5.0 - 2021-09-11

-   fixed a crash during HTML post-processing
-   fixed `implementation_headers` not working when paths use backslashes
-   added warnings when `implementation_headers` doesn't match anything

## v0.4.5 - 2021-06-08

-   added command-line option `--xmlonly`

## v0.4.3 - 2021-05-31

-   fixed regression in `[code_blocks]` functionality
-   fixed minor issues in syntax highlighter
-   added symbols from doxygen tagfiles to the syntax highlighter
-   minor style tweaks

## v0.4.1 - 2021-05-30

-   fixed `.dirs` being glommed as source paths
-   added config option `scripts`
-   added config option `stylesheets`
-   added config option `jquery`
-   added `custom` theme
-   added ability to use `HOME.md` as main page
-   added additional fix for inline `<code>` blocks
-   added `.poxy-toc` to table-of-contents elements
-   added floating page table-of-contents
-   removed m.css favicon fallback
-   made improvements to the `light` and `dark` themes
-   updated C++ doxygen tagfile

## v0.4.0 - 2021-05-29

-   added config option `theme`
-   added version number to CSS and javascript filenames to prevent browser cache issues
-   added `POXY_IMPLEMENTATION_DETAIL(...)` magic macro
-   added `POXY_IGNORE(...)` magic macro
-   fixed alignment of nested images inside detail blocks

## v0.3.4 - 2021-05-28

-   added basic `using` alias detection to syntax highlighter
-   added missing badges for C++23, 26 and 29

## v0.3.3 - 2021-05-23

-   fixed sorting of namespace and group members
-   fixed m.css failing with new versions of doxygen due to `Doxyfile.xml`
-   added google structured data to `\pages`

## v0.3.2 - 2021-05-19

-   fixed formatting of `<meta>` tags
-   added config option `author`
-   added config option `robots`
-   added markup tag `[p]`
-   added markup tag `[center]`

## v0.3.1 - 2021-05-13

-   added config option `macros`
-   added command-line option `--version`

## v0.3.0 - 2021-05-09

-   Improved handling of m.css and Doxygen warnings and errors
-   added command-line option `--doxygen`
-   added command-line option `--werror`
-   added markup tag `[set_parent_class]`
-   added markup tag `[add_parent_class]`
-   added markup tag `[remove_parent_class]`
-   added config option `images`
-   added config option `examples`
-   added ability to specify tagfiles as URIs

## v0.2.1 - 2021-05-07

-   fixed some minor autolinking issues

## v0.2.0 - 2021-05-06

-   added config option `source_patterns`

## v0.1.2 - 2021-05-02

-   fixed the Z-order of the nav bar being higher than the search overlay
-   added `NDEBUG` to the default set of defines

## v0.1.1 - 2021-04-26

-   added an additional cleanup step to the HTML postprocessor

## v0.1.0 - 2021-04-26

First public release :tada:
