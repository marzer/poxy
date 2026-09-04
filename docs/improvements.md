# What poxy does over Doxygen + m.css

[m.css] already turns Doxygen's XML into far nicer HTML than Doxygen's own output, with a great live
search. Poxy sits in front of both: it drives Doxygen with a locked-down configuration, repairs and
normalises the XML, then post-processes the HTML. The result is more consistent across Doxygen versions
and has a number of features neither tool provides alone.

- [Configuration](#configuration)
- [Version-proofing the XML](#version-proofing-the-xml)
- [Appearance and HTML](#appearance-and-html)
- [Authoring conveniences](#authoring-conveniences)
- [Cross-referencing](#cross-referencing)
- [Extras](#extras)

<br>

## Configuration

Poxy is configured with a [`poxy.toml`](configuration.md) instead of a Doxyfile.

- Most of Doxygen's knobs are set by poxy and not exposed. This is deliberate: Doxygen tends to break
  between releases, so keeping it locked down limits the damage and keeps debugging on the python side.
- The config file is self-contained (no Doxyfile-style `@INCLUDE` hierarchy).
- All relative input paths are resolved relative to the config file, not the working directory.
- Output always goes to `<cwd>/html` and `<cwd>/xml`. You choose the location by choosing where you run
  poxy, not through the config.
- C++ feature-test macros (the `__cpp_*` family) are defined automatically for the target language
  version, so conditional code documents correctly without a hand-maintained macro list.
- Source, image and example directories can be recursive or shallow on a per-directory basis.

<br>

## Version-proofing the XML

A core goal of poxy is to be a man-in-the-middle between Doxygen and m.css, ironing out the differences
between Doxygen versions so the same input produces the same output. Poxy reformats the XML consistently
from one release to the next, and applies a set of targeted fixes:

- removes `dir_*.xml` entries for directories that contain no input files
- removes empty `file_*.xml` entries that exist only to describe a documentation-only file (e.g. a
  `.dox` file). The file's content still appears in the docs; only the useless "Files" listing goes away.
- strips local filesystem paths out of generated tagfiles (they serve no purpose and leak directory
  layout)
- removes duplicate `<memberdef>` tags that some Doxygen versions emit when using groups
- merges class-member `@name` groups that share a name, so you do not have to rearrange code to make
  Doxygen behave
- sorts `@name` groups, `<memberdef>` tags, and inner class / namespace / group references
  alphabetically. Non-static data members are left in declaration order.
- adds the missing `inline="yes"` attribute to namespaces listed in [`inline_namespaces`](configuration.md#inline_namespaces)
- stops Doxygen folding non-type keywords such as `friend` and `static` into a function's return type
- repairs the many cases where Doxygen mangles trailing return types (`auto f() -> T`)
- folds a markdown list's first item back into the list when it shared a line with a block command
  (e.g. `@see - @ref a` followed by more items), which Doxygen otherwise leaves stranded as loose text
- normalises section titles and C++20 concept definitions so m.css renders them correctly

It can also merge the documentation of private "implementation" headers into their public counterpart;
see [`implementation_headers`](configuration.md#implementation_headers).

<br>

## Appearance and HTML

- A switchable light theme in addition to m.css's dark one.
- Better C++ syntax highlighting in code blocks: poxy re-highlights with Pygments and additionally
  colours types, namespaces, macros and other tokens that the base highlighter misses.
- Function signatures render qualifiers such as `constexpr`, `noexcept` and `virtual` as distinct labels.
- Support for C++20 concepts.
- A top-level page listing every `#define`, so macros are discoverable without hunting through file docs.
- Undocumented parents of documented symbols (and the values of documented enums) are kept rather than
  pruned, so the tree stays navigable.
- SVGs are inlined, so they can take advantage of [`currentColor`] and follow the active theme.
- Fonts are self-hosted, so a built site makes no external font requests.
- Configured `#include` prefixes can be stripped from the include line shown on each page.
- [Tabbed content blocks](aliases.md#tabbed-content) for showing, for example, one snippet in several
  languages.
- [Embedded iframe pages](configuration.md#pages) for hosting an external report (coverage, benchmarks,
  hand-written HTML) inside the docs without leaving them.

<br>

## Authoring conveniences

- A set of extra [Doxygen @alias commands](aliases.md): language code-block shortcuts, coloured note
  boxes, field decorators, link helpers and more.
- [Square-bracket tags](tags.md) for reliable inline control of the generated HTML (CSS classes,
  wrappers, ids, entities, emoji) where Doxygen's raw HTML support falls short.
- Emoji by name, via `[emoji name]`.

<br>

## Cross-referencing

- The cppreference.com tagfile is bundled and integrated automatically, so references to the standard
  library link to cppreference without any setup.
- [`autolinks`](configuration.md#autolinks) adds your own regex-to-URL hotlinking on top of what Doxygen
  and tagfiles resolve.
- Markdown headings get stable anchors derived from their text and namespaced per page. Doxygen
  otherwise numbers them `autotoc_md<N>` from a counter global to the whole run, so adding one page
  silently renumbers the anchors on every other page and breaks every deep link into them. An explicit
  `{#label}` on a heading is always honoured as written.
- Explicit link requests to documented macros (`#SOME_MACRO`) resolve everywhere, including markdown
  pages. Doxygen can only resolve a macro reference from inside a file scope, so from a page every
  spelling fails; poxy repairs these in the XML so they link like any other reference.
- Poxy can emit a tagfile of your own project for others to link against; see
  [`generate_tagfile`](configuration.md#generate_tagfile).

<br>

## Extras

- A [blog](blog.md) can be built alongside the API documentation: markdown posts with TOML front matter,
  a dated index, tags, drafts, per-post media, an RSS feed and a sitemap. Posts can `@ref` your C++
  symbols, which is most of the reason to keep the blog in the docs at all.
- A git-tag-based semver version switcher can be added to the generated HTML (`--git-tags`).
- Built-in [`navbar`](configuration.md#navbar), [`badges`](configuration.md#badges) and sponsor / social
  links.
- `--bug-report` captures all output in a zip file to make issues easier to report.

[m.css]: https://mcss.mosra.cz/documentation/doxygen/
[`currentColor`]: https://gomakethings.com/currentcolor-and-svgs
