# Changelog

## v0.19.7 - 2025-07-08

- fixed various issues related to CHANGELOG and README handling
- fixed page tables of contents being broken on some newer versions of Doxygen

## v0.19.6 - 2025-06-28

- fixed code blocks losing their file type with some versions of doxygen

## v0.19.4 - 2024-12-24

- fixed minor issues on Python 3.8

## v0.19.3 - 2024-11-11

- fixed crash with nested C-style enums without a name (#39) (@tim-janik)
- fixed `POXY_IMPLEMENTATION_DETAIL_IMPL` appearing in HTML in some circumstances

## v0.19.1 - 2024-10-30

- fixed `ModuleNotFoundError` error in Python 3.12 (#38) (@dekinet)

## v0.19.0 - 2024-09-15

- fixed crash when using simple type specifiers in friend declarations (#37) (@benjaminulmer)
- added workaround for [this issue](https://github.com/mosra/m.css/issues/239) introduced in Doxygen 1.9.7
- added auto-linking for various cppreference.com pages
- made `--bug-report` keep a copy of the original (pre-pre-processed?) XML
- updated m.css

## v0.18.0 - 2024-08-03

- added config option `excluded_symbols` (a.k.a. Doxygen's `EXCLUDE_SYMBOLS`) (#36) (@Guekka)

## v0.17.2 - 2024-06-16

- fixed qualified return types appearing squashed together without whitespace in some circumstances
- fixed performance regression in post-process step
- updated m.css
- minor style fixes

## v0.17.1 - 2024-06-14

- fixed `'tuple' object has no attribute 'week'` error on Python &lt;= 3.8

## v0.17.0 - 2024-04-21

- added arguments `--min-version` and `--squash-patches` for more control over `--git-tags` mode

## v0.16.0 - 2024-01-28

- added multi-version mode argument `--git-tags`
- added colour to output

## v0.15.0 - 2023-12-08

- added config option `main_page` (a.k.a. `USE_MDFILE_AS_MAINPAGE`)
- fixed searching for `CHANGELOG` too far up the directory heirarchy (now stops when a `.git` folder is encountered)

## v0.14.0 - 2023-11-25

- added the use of `*` wildcards in `implementation_headers`

## v0.13.9 - 2023-09-10

- fixed crash on Doxygen &lt;= 1.8.17 (#33) (@tim-janik)

## v0.13.8 - 2023-09-09

- fixed regression for Python &lt;= 3.8 (#32) (@tim-janik)

## v0.13.7 - 2023-08-17

- fixed minor syntax highlighting issues

## v0.13.6 - 2023-08-10

- update m.css to fix libgs.so lookup (#31) (@wroyca, @mosra)

## v0.13.5 - 2023-08-09

- fixed `--bug-report` regression (#29) (@wroyca)

## v0.13.4 - 2023-08-06

- fixed excessive `template<>` noise in details views

## v0.13.3 - 2023-08-01

- fixed floating TOCs sometimes clipping off the bottom of the screen when the viewport was vertically narrow

## v0.13.2 - 2023-07-31

- fixed doxygen's `@ref` links to `#id` anchors on the same page being treated as external links
- added auto-linking for C++ [named requirements](https://en.cppreference.com/w/cpp/named_req)
- minor style fixes

## v0.13.1 - 2023-07-29

- fixed crash regression with Doxygen 1.9.7
- fixed issues with \[tag\] substitution
- minor style fixes

## v0.13.0 - 2023-07-28

- migrated to `pyproject.toml`
- fixed footer being off-center (#24) (@wroyca)
- fixed redundant `auto` in trailing return types (#26) (@wroyca)
- added config option `sponsor`
- added config option `twitter`

## v0.12.7 - 2023-07-27

- allowed the use of square-bracket \[tags\] in more places

## v0.12.6 - 2023-07-25

- fixed overlong `template<>` lines in summary views
- fixed function parameter names greedily wrapping in details tables

## v0.12.5 - 2023-07-20

- fixed overlong `template<>` lines in page headers (they now wrap)

## v0.12.4 - 2023-03-23

- fixed changelog not auto-linking with some versions of Doxygen

## v0.12.3 - 2023-02-09

- fixed backwards-incompatible use of a newer `argparse` feature on Python &lt;= 3.8 (#20) (@fwerner)

## v0.12.2 - 2023-02-08

- switched default TOML lib to `tomli`

## v0.12.1 - 2022-11-22

- fixed `github` and `gitlab` config options not accepting periods (`.`)

## v0.12.0 - 2022-11-13

- fixed `AttributeError` during XML post-processing (#17) (@wroyca)
- added command-line option `--bug-report`
- improved diagnostic text in some areas

## v0.11.1 - 2022-10-23

- fixed crash when using `<a>` tags in navbar

## v0.11.0 - 2022-10-21

- added syntax highlighting for functions
- improved syntax highlighting of typenames

## v0.10.2 - 2022-10-16

- fixed crash when tagfile is disabled
- fixed a few syntax highlighting edge-cases
- fixed non-determinism in XML output formatting
- improved performance of syntax highlighting post-process
- minor style fixes

## v0.10.1 - 2022-10-15

- minor style fixes

## v0.10.0 - 2022-10-14

- fixed `static` keyword sometimes appearing twice on variables
- fixed `constexpr` keyword sometimes leaking into variable type
- fixed newer versions of pygments adding unnecessary markup to whitespace
- fixed malformed trailing return types in some circumstances
- fixed changelog page sometimes not having a table-of-contents
- added support for C++20's `constinit`
- added fallback to `tomllib` or `tomli` if `pytomlpp` is not available
- added command-line options `--html`, `--no-html`
- added command-line options `--xml`, `--no-xml`
- added command-line option `--no-werror`
- added `CHANGES` to the set of candidate changelog filenames
- deprecated command-line option `--xmlonly`
- removed command-line option `--doxygen`

## v0.9.1 - 2022-10-04

- fixed SVG inlining not preserving original image class attributes
- fixed `ValueError` when reading some SVG files
- fixed `navbar` option allowing duplicates
- fixed custom navbar items always being transformed to lowercase
- fixed navbar generating links to empty pages
- added `concepts` to the default set of links in `navbar`
- added `navbar` values `all` and `default`
- reduced I/O churn during HTML post-processing
- removed command-line option `--dry`

## v0.9.0 - 2022-10-03

- added support for C++20 concepts

## v0.8.2 - 2022-10-01

- added post-process to inline all local SVGs
- minor style fixes

## v0.8.1 - 2022-09-30

- minor style fixes

## v0.8.0 - 2022-09-29

- added config option `gitlab` (#13) (@wroyca)
- added ixx module extension in source patterns (#11) (@wroyca)
- added support for multi-codepoint emojis
- improved `doxygen.exe` location discovery on Windows
- improved `CHANGELOG` location discovery
- moved all poxy assets in the generated HTML to `html/poxy`
- self-hosted google fonts in generated HTML (instead of requiring additional HTTP requests on page load) (#6)
- removed ability to override m.css implementation
- removed legacy support for reading config options from neighbouring Doxyfiles
- overhauled the light theme
- many minor style fixes and tweaks

## v0.7.1 - 2022-08-17

- fixed crash on python &lt;= 3.8 (#9) (@wroyca)

## v0.7.0 - 2022-08-16

- fixed some `<link>`, `<meta>` and `<script>` tags not being included in `<head>` when a file was excluded from post-processing
- added `theme` command-line option
- added `html_header` config option option
- added automatic generation of github links in changelog when config option `github` is set
- added new light theme
- added dynamic switch for dark/light theme
- removed text from github icon on navbar (#5) (@wroyca)
- removed excessive spacing between article sections (#5) (@wroyca)
- many minor style fixes and tweaks

## v0.6.1 - 2022-08-16

- fixed multi-row navbar occluding page content (#3) (@wroyca)

## v0.6.0 - 2022-08-14

- fixed malformed error messages in some circumstances
- added builtin C++ standard macros for C++23
- added `changelog` config option
- updated cppreference.com tagfile

## v0.5.7 - 2022-05-17

- fixed being able to pass >= 33 threads to Doxygen's `NUM_PROC_THREADS`

## v0.5.6 - 2022-05-14

- fixed path error when using `--dry`
- fixed `friend` keyword sometimes leaking into function return types
- added additional language code block aliases
- added `--nocleanup` to `--help` output
- added support for C++20's `consteval` keyword

## v0.5.5 - 2022-04-16

- fixed C++20 concepts causing a crash in m.css (they are now skipped with a warning) (#1) (@jake-arkinstall)

## v0.5.4 - 2022-04-15

- updated m.css
- updated emoji database

## v0.5.3 - 2021-12-12

- fixed Doxygen bug that would sometimes treat keywords like `friend` as part of a function's return type
- Blacklisted schema 0.7.5 because [it's broken](https://github.com/keleshev/schema/issues/272)

## v0.5.2 - 2021-11-02

- fixed over-eager link-replacement for internal `#anchor` links
- added command-line options `--ppinclude` and `--ppexclude`

## v0.5.1 - 2021-10-09

- fixed over-eager link replacement causing text to be deleted

## v0.5.0 - 2021-09-11

- fixed a crash during HTML post-processing
- fixed `implementation_headers` not working when paths use backslashes
- added warnings when `implementation_headers` doesn't match anything

## v0.4.5 - 2021-06-08

- added command-line option `--xmlonly`

## v0.4.3 - 2021-05-31

- fixed regression in `[code_blocks]` functionality
- fixed minor issues in syntax highlighter
- added symbols from doxygen tagfiles to the syntax highlighter
- minor style tweaks

## v0.4.1 - 2021-05-30

- fixed `.dirs` being glommed as source paths
- added config option `scripts`
- added config option `stylesheets`
- added config option `jquery`
- added `custom` theme
- added ability to use `HOME.md` as main page
- added additional fix for inline `<code>` blocks
- added `.poxy-toc` to table-of-contents elements
- added floating page table-of-contents
- removed m.css favicon fallback
- made improvements to the `light` and `dark` themes
- updated C++ doxygen tagfile

## v0.4.0 - 2021-05-29

- added config option `theme`
- added version number to CSS and javascript filenames to prevent browser cache issues
- added `POXY_IMPLEMENTATION_DETAIL(...)` magic macro
- added `POXY_IGNORE(...)` magic macro
- fixed alignment of nested images inside detail blocks

## v0.3.4 - 2021-05-28

- added basic `using` alias detection to syntax highlighter
- added missing badges for C++23, 26 and 29

## v0.3.3 - 2021-05-23

- fixed sorting of namespace and group members
- fixed m.css failing with new versions of doxygen due to `Doxyfile.xml`
- added google structured data to `\pages`

## v0.3.2 - 2021-05-19

- fixed formatting of `<meta>` tags
- added config option `author`
- added config option `robots`
- added markup tag `[p]`
- added markup tag `[center]`

## v0.3.1 - 2021-05-13

- added config option `macros`
- added command-line option `--version`

## v0.3.0 - 2021-05-09

- Improved handling of m.css and Doxygen warnings and errors
- added command-line option `--doxygen`
- added command-line option `--werror`
- added markup tag `[set_parent_class]`
- added markup tag `[add_parent_class]`
- added markup tag `[remove_parent_class]`
- added config option `images`
- added config option `examples`
- added ability to specify tagfiles as URIs

## v0.2.1 - 2021-05-07

- fixed some minor autolinking issues

## v0.2.0 - 2021-05-06

- added config option `source_patterns`

## v0.1.2 - 2021-05-02

- fixed the Z-order of the nav bar being higher than the search overlay
- added `NDEBUG` to the default set of defines

## v0.1.1 - 2021-04-26

- added an additional cleanup step to the HTML postprocessor

## v0.1.0 - 2021-04-26

First public release :tada:
