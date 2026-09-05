# Configuration options

Every option available in a `poxy.toml`. All relative paths are resolved relative to the config file,
not the working directory.

- [aliases]
- [author]
- [autolinks]
- [badges]
- [blog]
    - [blog.enabled]
    - [blog.dir]
    - [blog.title]
    - [blog.id]
    - [blog.navbar]
    - [blog.drafts]
    - [blog.tags]
    - [blog.feed]
    - [blog.feed_limit]
- [changelog]
- [code_blocks]
    - [code_blocks.enums]
    - [code_blocks.functions]
    - [code_blocks.macros]
    - [code_blocks.namespaces]
    - [code_blocks.types]
- [cpp]
- [description]
- [dot]
- [examples]
    - [examples.paths]
    - [examples.recursive_paths]
    - [examples.patterns]
- [excluded_symbols]
- [extra_files]
- [favicon]
- [generate_tagfile]
- [github]
- [gitlab]
- [html_header]
- [images]
    - [images.paths]
    - [images.recursive_paths]
- [implementation_headers]
- [inline_namespaces]
- [internal_docs]
- [jquery]
- [license]
- [lightbox]
- [logo]
- [macros]
- [main_page]
- [meta_tags]
- [name]
- [navbar]
- [pages]
- [post]
- [private_repo]
- [robots]
- [scripts]
- [show_includes]
- [site_url]
- [sitemap]
- [sources]
    - [sources.extract_all]
    - [sources.paths]
    - [sources.recursive_paths]
    - [sources.patterns]
    - [sources.strip_paths]
    - [sources.strip_includes]
- [sponsor]
- [stylesheets]
- [tagfiles]
- [theme]
- [twitter]
- [warnings]
    - [warnings.enabled]
    - [warnings.treat_as_errors]
    - [warnings.undocumented]

<br> <!-- ========================================================================================================== -->

## `aliases`

Doxygen `@command` aliases.

#### Schema:

A table containing `alias` &rArr; `substitution` mappings.

#### Example:

```toml
[aliases]
'make_link{1}' = '<a href="\1">\1</a>'
'make_link{2}' = '<a href="\1">\2</a>'
```

#### Related Doxygen options:

[ALIASES]

<br><br> <!-- ====================================================================================================== -->

## `author`

The author of the project.

#### Schema:

A `string`.

#### Example:

```toml
author = 'Mark Gillard'
```

<br><br> <!-- ====================================================================================================== -->

## `autolinks`

Adds additional automatic hotlinking beyond what Doxygen and tagfiles can provide alone.

#### Schema:

A table containing `regex` &rArr; `uri` mappings. `uri` can be local or a fully-qualified external link.

#### Example:

```toml
[autolinks]
'(?:toml::)?parse[_ ]results?' = 'classtoml_1_1parse__result.html'
'(?:toml::)?parse[_ ]errors?'  = 'classtoml_1_1parse__error.html'
'(?:toml::)?node[_ ]views?'    = 'classtoml_1_1node__view.html'
```

<br><br> <!-- ====================================================================================================== -->

## `badges`

Adds shields.io-style badges under your main page's banner image.

#### Schema:

A table containing `description` &rArr; `[ image, uri ]` mappings. `image` can be local or a fully-qualified external link.

#### Example:

```toml
[badges]
'C++20'       = [ 'badge-C++20.svg', 'https://en.cppreference.com/w/cpp/compiler_support' ]
'TOML v1.0.0' = [ 'badge-TOML.svg', 'https://toml.io/en/v1.0.0' ]
```

<br><br> <!-- ====================================================================================================== -->

## `blog`

Controls the blog. See [the blog documentation](blog.md) for the post format and directory layout.

A blog is generated whenever the blog directory exists and contains at least one post, so this table is
only needed to change the defaults.

#### Schema:

A table with the sub-options described below.

#### Example:

```toml
[blog]
title = 'News'
feed_limit = 10
```

<br><br> <!-- ====================================================================================================== -->

## `blog.enabled`

Set to `false` to skip the blog entirely, leaving the post files in place.

#### Schema:

A `boolean`.

#### Default:

`true`

<br><br> <!-- ====================================================================================================== -->

## `blog.dir`

The directory containing the posts, relative to `poxy.toml`.

#### Schema:

A `string`.

#### Default:

`'blog'`

<br><br> <!-- ====================================================================================================== -->

## `blog.title`

The title of the blog index page, and of its navbar entry.

#### Schema:

A `string`.

#### Default:

`'Blog'`

<br><br> <!-- ====================================================================================================== -->

## `blog.id`

The page id of the blog index, which also names its output file.

#### Schema:

A `string`.

#### Default:

`'blog'`, giving `blog.html`

#### ℹ&#xFE0F; Notes:

Change this only if you have a [pages] entry that already claims the id `blog`. Poxy raises an error
naming both, so neither gets silently renamed.

<br><br> <!-- ====================================================================================================== -->

## `blog.navbar`

Whether to add the blog index to the navbar automatically.

#### Schema:

A `boolean`.

#### Default:

`true`

#### ℹ&#xFE0F; Notes:

The entry is appended after the content links. To place it yourself, set this to `false` and add `blog`
to [navbar] in the position you want. A site with no posts never gets an entry either way.

<br><br> <!-- ====================================================================================================== -->

## `blog.drafts`

Whether posts marked `draft = true` are built.

#### Schema:

A `boolean`.

#### Default:

`false`

#### ℹ&#xFE0F; Notes:

`--drafts` and `--no-drafts` on the command line override this, which is the more usual way to preview
drafts locally without committing a config change.

<br><br> <!-- ====================================================================================================== -->

## `blog.tags`

Whether to generate a page per tag, plus a tag index.

#### Schema:

A `boolean`.

#### Default:

`true`

#### ℹ&#xFE0F; Notes:

Tag pages enter the search index alongside your C++ symbols. Set this to `false` if that dilution
bothers you; tags still appear on posts, without links.

<br><br> <!-- ====================================================================================================== -->

## `blog.feed`

Whether to generate `feed.xml`, an RSS 2.0 feed.

#### Schema:

A `boolean`.

#### Default:

`true`

#### ℹ&#xFE0F; Notes:

Requires [site_url], since feed entries must carry absolute links. Without it no feed is written,
regardless of this setting.

<br><br> <!-- ====================================================================================================== -->

## `blog.feed_limit`

How many of the most recent posts appear in the feed.

#### Schema:

An `integer`.

#### Default:

`20`

<br><br> <!-- ====================================================================================================== -->

## `changelog`

Adds a changelog page and a link to it in the site footer.

#### Schema:

A `boolean` or explicit `string` path to the changelog markdown file.

#### Default:

`false`

#### Example:

```toml
changelog = false # no changelog will be generated
changelog = true # find the changelog file in the poxy.toml directory or a parent
changelog = 'path/to/the/changelog.md'
```

#### ℹ&#xFE0F; Notes:

When setting this value to `true`, poxy will search for these filenames, in order:

-   `CHANGELOG.md`
-   `CHANGELOG.txt`
-   `CHANGELOG`
-   `HISTORY.md`
-   `HISTORY.txt`
-   `HISTORY`

Searching starts in the same directory as `poxy.toml`, and continues up through parent directories until a match is found.

The file is assumed to be plain-text and will be parsed as markdown. No other formats are supported.

<br><br> <!-- ====================================================================================================== -->

## `code_blocks`

A table of nested options for improving how `<code>` blocks are rendered as HTML. See the specific entries below.

<br><br> <!-- ====================================================================================================== -->

## `code_blocks.enums`

Injects additional enum values into the syntax highligher.

#### Schema:

A single `regex` or an array of `regexes`.

#### Example:

```cpp
namespace magic
{
    enum class values
    {
        a,
        b,
        c,
        COUNT
    };
}
```

```toml
[code_blocks]
enums = [ 'magic::values::[a-zA-Z]+' ]
```

#### ℹ&#xFE0F; Notes:

You do not need to add enum values from your own code or from the C++ standard library; Poxy does this for you.

<br><br> <!-- ====================================================================================================== -->

## `code_blocks.functions`

Injects additional functions into the syntax highligher.

#### Schema:

A single `regex` or an array of `regexes`.

#### Example:

```cpp
namespace magic
{
    void some_function()
	{
		/* ... */
	}

    void some_other_function()
	{
		/* ... */
	}
}
```

```toml
[code_blocks]
functions = [ 'magic::some.*function' ]
```

#### ℹ&#xFE0F; Notes:

-   ⚠&#xFE0F; Don't pre-emptively populate this without first seeing the result! The syntax highlighter will get it right in most cases.
    The ones it is likely to miss are mostly template code.

-   You do not need to add functions from your own code or from the C++ standard library; Poxy does this for you.

<br><br> <!-- ====================================================================================================== -->

## `code_blocks.macros`

Injects additional preprocessor macro `#defines` into the syntax highlighter.

#### Schema:

A single `regex` or an array of `regexes`.

#### Example:

```toml
[code_blocks]
macros = [ 'TOML_[A-Z0-9_]+?', 'print_value' ]
```

#### ℹ&#xFE0F; Notes:

You generally do not need to add macros from your own code or [C++ feature test macros] since Poxy does this for
you. That being said, given library-specific macros tend to be 'namespaced' using a common prefix, a catch-all regex
can be a useful future-proofing mechanism.

<br><br> <!-- ====================================================================================================== -->

## `code_blocks.namespaces`

Injects additional namespaces into the syntax highlighter.

#### Schema:

A single `regex` or an array of `regexes`.

#### Example:

```cpp
namespace magic
{
    namespace more_magic { /* ... */ }
}
```

```toml
[code_blocks]
namespaces = [ 'magic(::more_magic)?' ]
```

#### ℹ&#xFE0F; Notes:

You do not need to add namespaces from your own code or from the C++ standard library; Poxy does this for you.

<br><br> <!-- ====================================================================================================== -->

## `code_blocks.types`

Injects additional typenames into the syntax highlighter.

#### Schema:

A single `regex` or an array of `regexes`.

#### Example:

```toml
[code_blocks]
types = [ 'my::namespace::(foo|bar)' ]
```

#### ℹ&#xFE0F; Notes:

You do not need to add typenames from your own code or from the C++ standard library; Poxy does this for you.

<br><br> <!-- ====================================================================================================== -->

## `cpp`

Specifies the minimum C++ version your project targets. Effects:

-   Adds a badge under your main page's banner image
-   Dictates which [C++ feature test macros] are fed to Doxygen's preprocessor

#### Schema:

A `string` or `integer` containing the C++ standard year as YYYY or YY, e.g. `2003`, `17`, `'20'`, etc.

#### Default:

The current three-yearly C++ standard as if by `(current year - 2)`.

#### Example:

```toml
cpp = 17
```

<br><br> <!-- ====================================================================================================== -->

## `description`

A brief description of the project.

#### Schema:

A `string`.

#### Example:

```toml
description = 'TOML for modern C++'
```

#### Related Doxygen options:

[PROJECT_BRIEF]

<br><br> <!-- ====================================================================================================== -->

## `dot`

Indicates whether the graph generation tool `dot` is available for use by Doxygen.

#### Schema:

A `boolean`.

#### Default:

No value - try to autodiscover if `dot` is available automatically.

#### Example:

```toml
dot = true
```

<br><br> <!-- ====================================================================================================== -->

## `examples`

A table of nested options relating to Doxygen's discovery of example code for `@include`, `@snippet`, et cetera. See the specific entries below.

<br><br> <!-- ====================================================================================================== -->

## `examples.paths`

## `examples.recursive_paths`

## `examples.patterns`

Specifies the input paths and file path filter patterns used by Doxygen to discover example code specified using
`@include`, `@snippet`, etc. Directories specified using `recursive_paths` are searched recursively, while those
specified using `paths` are only subject to shallow searches.

#### Schema:

A single `string` or an array of `strings`.

#### Default:

-   `paths` and `recursive_paths`: No paths are specified by default.
-   `patterns`: `*` (all files are matched)

#### Example:

```toml
[examples]
paths           = '../examples'
recursive_paths = [ '../../include', '../../src' ]
patterns        = [ '*.h' , '*.cpp' ]
```

#### Related Doxygen options:

[EXAMPLE_PATH]  
[EXAMPLE_RECURSIVE]  
[EXAMPLE_PATTERNS]

<br><br> <!-- ====================================================================================================== -->

## `excluded_symbols`

One or more symbols to exclude from the doxygen output.

#### Schema:

A single `string` or an array of `strings`.

#### Default:

No symbols are excluded by default.

#### Example:

```toml
excluded_symbols  = 'toml::impl'
```

#### Related Doxygen options:

[EXCLUDE_SYMBOLS]

<br><br> <!-- ====================================================================================================== -->

## `extra_files`

A list of local files to copy verbatim to the output `html` directory.

#### Schema:

A single `string` or an array of `strings`.

#### Example:

```toml
extra_files = [
    'images/banner_small.png',
    'images/badge-awesome.svg',
    'images/badge-TOML.svg',
    'images/badge-C++20.svg'
]
```

#### Related Doxygen options:

[HTML_EXTRA_FILES]

<br><br> <!-- ====================================================================================================== -->

## `favicon`

Path to the icon file to use as the HTML site's favicon.

#### Schema:

A `string`.

#### Example:

```toml
favicon = 'images/favicon.ico'
```

#### Related m.css option:

[M_FAVICON]

<br><br> <!-- ====================================================================================================== -->

## `generate_tagfile`

Specifies whether a doxygen tagfile should be generated and linked to in HTML page footers.

#### Schema:

A `boolean`.

#### Default:

`true`

#### Example:

```toml
generate_tagfile = true
```

#### Related Doxygen options:

[GENERATE_TAGFILE]

<br><br> <!-- ====================================================================================================== -->

## `github`

## `gitlab`

Specifies the GitHub or GitLab repository the project relates to. Effects:

-   Adds a repository link to the navbar
-   Adds repository and "Report an issue" links to the page footer
-   Adds a "Releases" badge under the main page's banner (if [`private_repo`] is `false`)
-   Linkifies issues (`#999`), users (`@person`) and pull requests (`!person`) in the changelog page when [`changelog`] is used

#### Schema:

A `user/repository` string.

#### Example:

```toml
github = 'marzer/tomlplusplus'
```

#### ℹ&#xFE0F; Notes:

Specify one or the other; do not specify both. If your project has a repository on both, specify only the one that is the main
developer tree (i.e. not merely a mirror).

<br><br> <!-- ====================================================================================================== -->

## `html_header`

Adds an additional snippet of HTML to each page's `<head>` section.

#### Schema:

A single `string`.

#### Example:

```toml
html_header = '''
    <script> console.log("this is going to be ugly!"); </script>
    <style> div { background-color: red; } </style>
''''
```

#### ℹ&#xFE0F; Notes:

This option is exposed for more advanced scenarios since most things you'd typically put in a page's `<head>`
already have their own configuration options:

-   Setting page title: [`name`]
-   Adding CSS stylesheets: [`stylesheets`]
-   Adding JS scripts: [`scripts`]
-   Adding page metadata (`<meta>`tags): [`meta_tags`]
-   Controlling robots/scrapers: [`robots`]

#### Related m.css options:

[HTML_HEADER]

<br><br> <!-- ====================================================================================================== -->

## `images`

A table of nested options relating to Doxygen's discovery of image files for the `@image` command.
See the specific entries below.

<br><br> <!-- ====================================================================================================== -->

## `images.paths`

## `images.recursive_paths`

Specifies the input paths used by Doxygen to discover images specified using the `@image` command.
Directories specified using `recursive_paths` are searched recursively, while those specified using `paths`
are only subject to shallow searches.

#### Schema:

A single `string` or an array of `strings`.

#### Example:

```toml
[images]
paths           = '../images'
# recursive_paths = [ ]
```

#### Related Doxygen options:

[IMAGE_PATH]

<br><br> <!-- ====================================================================================================== -->

## `implementation_headers`

Folds documentation from internal implementation headers up into the public header they support.

#### Schema:

A table containing `header` &rArr; `impl header` mappings.

#### Example:

Given a project with the following structure:

```
/include
    /impl
        strings_utf8.h
        strings_utf16.h
        strings_utf32.h
    strings.h
```

To have all documentation parsed from the `/impl/strings_XXXX.h` headers appear as though it were
actually from `strings.h`:

```toml
[implementation_headers]
'include/strings.h' = [
    'include/impl/strings_utf8.h',
    'include/impl/strings_utf16.h',
    'include/impl/strings_utf32.h'
]
```

**Since v0.14.0**: Wildcards (`*`) are also supported:

```toml
[implementation_headers]
'include/strings.h' = [ 'include/impl/strings_*.h' ]
```

<br><br> <!-- ====================================================================================================== -->

## `inline_namespaces`

Tells Doxygen which namespaces are `inline namespaces`, since older versions of Doxygen would lose this information.

#### Schema:

A single `string` or an array of `strings`.

#### Example:

```toml
inline_namespaces = [ 'toml::literals' ]
```

#### ℹ&#xFE0F; Notes:

This property is unnecessary if you're using Doxygen 1.8.19 or later.

<br><br> <!-- ====================================================================================================== -->

## `internal_docs`

Specifies that the documentation generated from this config file is 'internal'. Effects:

-   `true`:
    -   Sets Doxygen's [INTERNAL_DOCS] to `YES`
    -   Adds `private` and `internal` to Doxygen's [ENABLED_SECTIONS]
-   `false`:
    -   Sets Doxygen's [INTERNAL_DOCS] to `NO`
    -   Adds `public` and `external` to Doxygen's [ENABLED_SECTIONS]

#### Schema:

A `boolean`.

#### Default:

`false`

#### Example:

```toml
internal_docs = false
```

#### Related Doxygen options:

[ENABLED_SECTIONS]  
[INTERNAL_DOCS]

<br><br> <!-- ====================================================================================================== -->

## `jquery`

Specifies whether [jQuery](https://jquery.com/) should be included as part of the generated HTML.

#### Schema:

A `boolean`

#### Default:

`false`

#### Example:

```toml
jquery = true
```

#### ℹ&#xFE0F; Notes:

Poxy itself doesn't (currently) use jQuery; it's here in case you want it in your own [`scripts`]. Enabling it
without adding any javascript of your own does nothing.

<br><br> <!-- ====================================================================================================== -->

## `license`

Specifies the license used by the project. Effects:

-   Adds a license link to the HTML page footer
-   Adds a badge under your main page's banner image

#### Schema:

An `[ SDPX, uri ]` pair.
`uri` can be local or a fully-qualified external link.

#### Example:

```toml
license = [ 'MIT', 'https://github.com/marzer/tomlplusplus/blob/master/LICENSE' ]
```

<br><br> <!-- ====================================================================================================== -->

## `lightbox`

**Since v0.27.0**

Specifies whether images in page content open full-size in an overlay when clicked.

#### Schema:

A `boolean`

#### Default:

`true`

#### Example:

```toml
lightbox = false
```

#### ℹ&#xFE0F; Notes:

Each eligible image is wrapped in a link to itself, so with javascript disabled a click still opens the
image, and middle-click still opens it in a new tab. Images that are already links are left alone, as are
SVGs, which poxy injects into the document instead.

The overlay's caption is the image's `figcaption` where it has one, and its alt text otherwise. Doxygen
gives a captioned image `alt="Image"`, so on an ordinary page the caption is what you wrote after the
filename; in a blog post, where poxy stages the images itself, the alt survives and is what you get.

<br><br> <!-- ====================================================================================================== -->

## `logo`

Specifies the project logo image to feature in the HTML navbar.

#### Schema:

A `string`.

#### Example:

```toml
logo = 'images/logo.png'
```

#### Related Doxygen options:

[PROJECT_LOGO]

<br><br> <!-- ====================================================================================================== -->

## `macros`

Specifies additional macros to pass to Doxygen's preprocessor. Also makes these definitions known to the syntax highlighter.

#### Schema:

A table containing `macro` &rArr; `expansion` mappings.

#### Example:

```toml
[macros]
'TOML_ASYMMETRICAL_EQUALITY_OPS(...)' = 'static_assert(true)'
'TOML_ABI_NAMESPACE_START(...)'       = 'static_assert(true)'
'TOML_ABI_NAMESPACE_BOOL(...)'        = 'static_assert(true)'
```

#### ℹ&#xFE0F; Notes:

In addition to the [C++ feature test macros], Poxy automatically defines many 'built-in' macros for you:
| macro                      | expansion                            |
| -------------------------- | ------------------------------------ |
| `NDEBUG`                   | 1                                    |
| `DOXYGEN`                  | 1                                    |
| `__DOXYGEN__`              | 1                                    |
| `__doxygen__`              | 1                                    |
| `__POXY__`                 | 1                                    |
| `__poxy__`                 | 1                                    |
| `__has_builtin(...)`       | 0                                    |
| `__has_feature(...)`       | 0                                    |
| `__has_include(...)`       | 0                                    |
| `__has_attribute(...)`     | 0                                    |
| `__has_cpp_attribute(...)` | 999999                               |
| `__cplusplus`              | the standard value per [`cpp`](#cpp) |

#### Related Doxygen options:

[PREDEFINED]

<br><br> <!-- ====================================================================================================== -->

## `main_page`

Sets a specific markdown page to use as the main page, or instructs poxy to search for one.

#### Schema:

A `boolean` or explicit `string` path to the markdown file.

#### Default:

`false`

#### Example:

```toml
main_page = false # no markdown file will be used as the main page
main_page = true # try to find a suitable markdown page to use in the poxy.toml directory or a parent
main_page = 'path/to/the/main_page.md'
```

#### ℹ&#xFE0F; Notes:

When setting this value to `true`, poxy will search for these filenames, in order:

-   `README.md`
-   `README.txt`
-   `README`
-   `HOME.md`
-   `HOME.txt`
-   `HOME`
-   `MAINPAGE.md`
-   `MAINPAGE.txt`
-   `MAINPAGE`
-   `INDEX.md`
-   `INDEX.txt`
-   `INDEX`

Searching starts in the same directory as `poxy.toml`, and continues up through parent directories until a match is found.

The file is assumed to be plain-text and will be parsed as markdown. No other formats are supported.

#### Related Doxygen options:

[USE_MDFILE_AS_MAINPAGE]

<br><br> <!-- ====================================================================================================== -->

## `meta_tags`

Specifies addititional `<meta>` tags to add to the generated HTML `<head>`.

#### Schema:

A table of `name` &rArr; `content` mappings, where `content` may be a `string` or an `integer`.

#### Example:

```toml
[meta_tags]
'google-site-verification' = 'kjnwnkj234njk324wefknsdf'
```

<br><br> <!-- ====================================================================================================== -->

## `name`

The name of the project.

#### Schema:

A `string`.

#### Example:

```toml
name = 'toml++'
```

#### Related Doxygen options:

[PROJECT_NAME]

<br><br> <!-- ====================================================================================================== -->

## `navbar`

Specifies what appears on the navbar of each HTML page.

#### Schema:

A single `string` or list of `strings`:
| Value             | Links to                                                       |
| ----------------- | -------------------------------------------------------------- |
| `all`             | Expands to _all_ the other values.                             |
| `classes`         | `class`/`struct`/`union` index page                            |
| `concepts`        | `concept` index page (C++20 Concepts)                          |
| `default`         | Expands to the default set of values.                          |
| `files`           | File hierarchy index page (per Doxygen's `@file` command)      |
| `github`          | Alias of `repo` if config option [`github`] was specified.     |
| `gitlab`          | Alias of `repo` if config option [`gitlab`] was specified.     |
| `groups`          | Group index page (per Doxygen's `@addgroup`, `@ingroup`, etc.) |
| `modules`         | Alias of `groups`                                              |
| `namespaces`      | `namespace` index page                                         |
| `pages`           | Index of articles created using `@mainpage`, `@page`, etc.     |
| `repo`            | Repository link (per [`github`], [`gitlab`], etc).             |
| `sponsor`         | Repository link (per [`sponsor`]).                             |
| `twitter`         | Repository link (per [`twitter`]).                             |
| `<a href=""></a>` | Custom anchor tags can be added directly.                      |

#### Default:

`files`, `groups`, `namespaces`, `classes`, `concepts` **(since `v0.9.1`)**, `repo`, `theme`

#### Example

```toml
navbar = [ 'namespaces', 'classes' ]
```

#### ℹ&#xFE0F; Notes:

-   `repo` is always added if a repository is specified
-   `theme` is always added if a value other than `custom` is specified for [`theme`].
-   `repo` and `theme` may be explicitly specified if you wish to change their positions (otherwise they always appear at the end)
-   **Since v0.9.1**: duplicate links are removed.
-   **Since v0.9.1**: links to empty index pages are removed (e.g. specifying `concepts` for a project that does not contain any C++20 concepts is a no-op)
-   **Since v0.13.0**: `twitter` is always added if a value is specified for [`twitter`].
-   **Since v0.13.0**: `sponsor` is always added if a value is specified for [`sponsor`].

#### Related m.css options:

[M_LINKS_NAVBAR1]  
[M_LINKS_NAVBAR2]

<br><br> <!-- ====================================================================================================== -->

## `pages`

**Since v0.24.0**

Adds custom pages that embed external HTML (a coverage report, a benchmark dashboard, hand-written HTML, etc.)
in an `<iframe>`, rendered inside the normal poxy chrome so the reader never leaves the documentation.

#### Schema:

A table of `id` &rArr; `{ options }` entries. Each entry's options are:

| Key        | Description                                                                                                                                                                   |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `title`    | The page + navbar title. Defaults to the entry's `id`.                                                                                                                        |
| `content`  | A local file or directory to bundle into the output and embed. For a directory, the iframe loads its `index.html`.                                                            |
| `url`      | An external URL to embed instead of bundling local content. Exactly one of `content` or `url` is required.                                                                    |
| `navbar`   | Whether to add a navbar link to the page. Defaults to `true`.                                                                                                                 |
| `required` | Whether a missing `content` path is an error. Defaults to `true`; set `false` to skip the page (with a non-fatal warning) when its content has not been generated this build. |
| `layout`   | `full` (default) for an edge-to-edge iframe that fills the viewport, or `inline` to sit in the content column.                                                                |
| `height`   | Height of the iframe for the `inline` layout (any CSS length). Ignored for `full`.                                                                                            |

#### Example:

```toml
[pages.coverage]
title   = 'Coverage'
content = 'build/coverage'   # a directory; bundled into html/coverage/, embeds index.html

[pages.benchmarks]
title  = 'Benchmarks'
url    = 'https://my-project.example.com/benchmarks'
navbar = true

[pages.notes]
title   = 'Design notes'
content = 'notes.html'       # a single file
layout  = 'inline'
height  = '40rem'
```

#### ℹ&#xFE0F; Notes:

-   Bundled `content` is copied verbatim into `html/<id>/` and is not post-processed by poxy, so a report keeps its own styling.
-   `required = false` suits content produced by a separate build step (a coverage report, say): if it has not been generated, the page is skipped with a warning instead of failing the build, even under `--werror`.
-   Each page also appears in the "Pages" index regardless of its `navbar` setting.
-   The entry's `id` is used for both the output filename (`<id>.html`) and the bundled content directory; non-identifier characters in the key are replaced with underscores.

<br><br> <!-- ====================================================================================================== -->

## `post`

**Since v0.25.0**

One or more shell commands run after a successful build. Useful for packaging, deploying, or applying
your own post-processing to the generated output.

#### Schema:

An array of tables (`[[post]]`). Each entry runs its `commands` in order and may set options shared by
those commands:

| Key                 | Description                                                                                                                                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `commands`          | The commands to run, in order. Each is either a `string` (tokenized with POSIX shell-quoting rules on every platform) or an `array` of arguments (used verbatim, no tokenizing - best for paths with spaces or backslashes). Required. |
| `shell`             | Run each command through the system shell (`cmd.exe` on Windows, `/bin/sh` on POSIX) so pipes, `&&`, redirection and globbing work. Defaults to `false`. Not portable across operating systems.                       |
| `working_directory` | `output` (default) to run in the output directory (where `html/` and `xml/` are written), or `config` to run in the directory containing your `poxy.toml`.                                                            |
| `allow_failure`     | When `true`, a non-zero exit is downgraded to a warning instead of failing the build (still escalated to an error under `--werror`). Defaults to `false`.                                                             |
| `timeout`           | Optional per-command time limit, in seconds. Exceeding it fails the build. No limit by default.                                                                                                                      |

#### Default:

None (no commands run).

#### Example:

```toml
# package the html once it's built
[[post]]
commands = [
    'tar -czf docs.tar.gz html',
]

# deploy in a shell (for the pipe), allowed to fail without breaking the build
[[post]]
shell         = true
allow_failure = true
commands = [
    'rsync -a html/ user@host:/var/www/docs/',
]

# run a helper script that reads the poxy-provided paths from the environment
[[post]]
commands = [
    ['python', 'tools/postprocess.py'],
]
```

#### ℹ&#xFE0F; Notes:

-   Commands do **not** run when neither HTML nor XML output was produced.
-   Paths are provided to each command as environment variables rather than substituted into the command
    text, so paths containing spaces or shell metacharacters are always safe:
    -   `POXY_OUTPUT_DIR` - the output directory (also the default working directory)
    -   `POXY_CONFIG_DIR` - the directory containing `poxy.toml`
    -   `POXY_CONFIG_PATH` - the `poxy.toml` file itself
    -   `POXY_HTML_DIR` - the `html/` directory (only set when HTML was generated)
    -   `POXY_XML_DIR` - the `xml/` directory (only set when XML was generated)
-   `shell = false` (the default) runs commands directly, without a shell: portable and free of
    shell-injection surprises. Reach for `shell = true` only when you need shell features like pipes.
-   `post` runs arbitrary programs during the build, so treat a checked-in `poxy.toml` with the same
    trust you would give a build script.
-   Under `--git-tags`, `post` runs **once** for the whole build, after every version has been generated
    and assembled, with `POXY_HTML_DIR` pointing at the top-level `html/` that contains all versions
    (each under `html/<tag>`).

<br><br> <!-- ====================================================================================================== -->

## `private_repo`

Specifies whether the Github repository for this project is private.

#### Schema:

A `boolean`.

#### Default:

`false`

#### Example:

```toml
private_repo = false
```

<br><br> <!-- ====================================================================================================== -->

## `robots`

Specifies whether search 'bots' and webcrawlers should interact with the generated HTML.

#### Schema:

A `boolean`.

#### Default:

`true`

#### Example:

```toml
robots = true
```

<br><br> <!-- ====================================================================================================== -->

## `scripts`

A list of javascript files to include as `<script>` tags in the `<head>` of each generated HTML page.

#### Schema:

A single `string` or an array of `strings`.

#### Example:

```toml
scripts = [
    'some_local_script.js',
    'https://code.jquery.com/jquery-3.6.0.min.js'
]
```

#### ℹ&#xFE0F; Notes:

Any local files will be copied to the output directory as if by adding them to [`extra_files`].

#### Related Doxygen options:

[HTML_EXTRA_FILES]

<br><br> <!-- ====================================================================================================== -->

## `show_includes`

Specifies whether `#include` directives should be shown in HTML pages.

#### Schema:

A `boolean`.

#### Default:

`true`

#### Example:

```toml
show_includes = true
```

<br><br> <!-- ====================================================================================================== -->

## `site_url`

The absolute URL your documentation is published at. Without it, everything needing a full link is
skipped: the RSS feed, `sitemap.xml`, `<link rel="canonical">` and `og:url`.

#### Schema:

An absolute `http` or `https` URL. A trailing slash is ignored.

#### Default:

None.

#### Example:

```toml
site_url = 'https://marzer.github.io/tomlplusplus'
```

#### ℹ&#xFE0F; Notes:

Poxy does not infer this from [github]. That guess is wrong for `<user>.github.io` repositories and for
every custom domain, and unlike poxy's other guesses the result is baked into a published feed, where a
wrong base URL is worse than no feed at all.

<br><br> <!-- ====================================================================================================== -->

## `sitemap`

Whether to generate a `sitemap.xml` covering every generated page.

#### Schema:

A `boolean`.

#### Default:

`true` when [site_url] is set, `false` otherwise.

#### ℹ&#xFE0F; Notes:

Post entries carry a `lastmod` taken from the post date. Nothing else does, because file modification
times are meaningless in CI, where a fresh clone stamps every file identically.

Redirect stubs generated from a post's `aliases` are excluded, as is `404.html`.

<br><br> <!-- ====================================================================================================== -->

## `sources`

A table of nested options relating to Doxygen's discovery and handling of source files. See the specific entries below.

<br><br> <!-- ====================================================================================================== -->

## `sources.extract_all`

Default behaviour is to only emit documentation for explicitly documented symbols to encourage careful, selective
documentation practices. Override this by setting `sources.extract_all` to `true`.

#### Schema:

A `boolean`

#### Default:

`false`

#### Example:

```toml
[sources]
extract_all = true
```

#### Related Doxygen options:

[EXTRACT_ALL]

#### Related m.css options:

[M_SHOW_UNDOCUMENTED]

<br><br> <!-- ====================================================================================================== -->

## `sources.paths`

## `sources.recursive_paths`

## `sources.patterns`

Specifies the input paths and file path filter patterns used by Doxygen to discover documentation source files.
Directories specified using `recursive_paths` are searched recursively, while those specified using `paths`
are only subject to shallow searches.

#### Schema:

A single `string` or an array of `strings`.

#### Default:

-   `paths` and `recursive_paths`: No paths are specified by default.
-   `patterns`: `*.h`, `*.hh`, `*.hxx`, `*.hpp`, `*.h++`, `*.inc`, `*.markdown`, `*.md`, `*.dox`

#### Example:

```toml
[sources]
paths           = 'pages'
recursive_paths = [ '../include' ]
patterns        = [ '*.h' , '*.dox' ]
```

#### Related Doxygen options:

[INPUT]  
[FILE_PATTERNS]  
[RECURSIVE]

<br><br> <!-- ====================================================================================================== -->

## `sources.strip_paths`

Specifies path prefixes to strip from file paths emitted in documentation.

#### Schema:

A single `string` or an array of `strings`.

#### Example:

```toml
[sources]
strip_paths     = [ '../include' ]
```

#### Related Doxygen options:

[STRIP_FROM_PATH]

<br><br> <!-- ====================================================================================================== -->

## `sources.strip_includes`

Specifies path prefixes to strip from `#include <path/to/header.h>` directives emitted in documentation.

#### Schema:

A single `string` or an array of `strings`.

#### Example:

```toml
[sources]
strip_includes  = 'include/'
```

#### ℹ&#xFE0F; Notes:

This property is applied _after_ [`sources.strip_paths`]; the final rendered version of `#include` directives is a
combination of both options.

#### Related Doxygen options:

[STRIP_FROM_INC_PATH]

<br><br> <!-- ====================================================================================================== -->

## `sponsor`

URI to a page detailing information about how users may sponsor your project. Puts links on the navbar and in the footer.

#### Schema:

A `URI`.

#### Example:

```toml
sponsor = 'https://this.is.how/users/can/sponsor/me'
```

<br><br> <!-- ====================================================================================================== -->

## `stylesheets`

A list of CSS files to include as `<link>` tags in the `<head>` of each generated HTML page.

#### Schema:

A single `string` or an array of `strings`.

#### Example:

```toml
stylesheets = [
    'my_fancy_styles.css',
    'https://fonts.googleapis.com/css?family=Source+Sans+Pro:400,400i,600,600i%7CSource+Code+Pro:400,400i,600'
]
```

#### ℹ&#xFE0F; Notes:

Any local files will be copied to the output directory as if by adding them to [`extra_files`].

#### Related Doxygen options:

[HTML_EXTRA_STYLESHEET]

<br><br> <!-- ====================================================================================================== -->

## `tagfiles`

Specifies additional tagfiles for Doxygen to use during documentation generation.

#### Schema:

A table of `tagfile` &rArr; `base_uri` mappings. `tagfile` can be local or a fully-qualified external link
to a web resource (in which case it is downloaded and cached locally).

#### Example:

```toml
[tagfiles]
'https://marzer.github.io/tomlplusplus/tomlplusplus.tagfile.xml' = 'https://marzer.github.io/tomlplusplus/'
```

#### ℹ&#xFE0F; Notes:

You don't need to apply the C++ standard library tagfile from cppreference.com; Poxy automatically does this for you.

#### Related Doxygen options:

[TAGFILES]

<br><br> <!-- ====================================================================================================== -->

## `theme`

Specifies the default visual theme to use in the generated HTML pages.

#### Schema:

A `string`. May be one of the following values:

-   `light`
-   `dark`

#### Default:

`dark`

#### Example:

```toml
theme = 'light'
```

#### ℹ&#xFE0F; Notes:

**Since v0.7.0:** this option only controls the _default_ theme to use, with there being a navbar button for users to switch
between light and dark as they please.

#### Related m.css options:

[M_THEME_COLOR]

<br><br> <!-- ====================================================================================================== -->

## `twitter`

The handle to a twitter account to show as a link on the navbar.

#### Schema:

A `string`.

#### Example:

```toml
twitter = 'marzer8789'
```

<br><br> <!-- ====================================================================================================== -->

## `warnings`

A table of nested options relating to the handling of warnings. See the specific entries below.

<br><br> <!-- ====================================================================================================== -->

## `warnings.enabled`

Controls the emission of all warnings.

#### Schema:

A `boolean`.

#### Default:

`true`

#### Example:

```toml
[warnings]
enabled = true
```

#### Related Doxygen options:

[WARNINGS]

<br><br> <!-- ====================================================================================================== -->

## `warnings.treat_as_errors`

Specifies whether warnings should be treated as errors and cause Poxy to exit with an error code.

#### Schema:

A `boolean`.

#### Default:

`false`

#### Example:

```toml
[warnings]
treat_as_errors = true
```

#### ℹ&#xFE0F; Notes:

You can also enable this on the command-line using `--werror`.
The command-line option always takes precedence over config files.

#### Related Doxygen options:

[WARN_AS_ERROR]

<br><br> <!-- ====================================================================================================== -->

## `warnings.undocumented`

Specifies if undocumented classes, types, defines etc. should cause Doxygen to emit warnings.

#### Schema:

A `boolean`.

#### Default:

`true`

#### Example:

```toml
[warnings]
undocumented = false
```

#### Related Doxygen options:

[WARN_IF_UNDOCUMENTED]

<!-- =============================================================================================================== -->

[c++ feature test macros]: https://en.cppreference.com/w/cpp/feature_test
[`aliases`]: #aliases
[`author`]: #author
[`autolinks`]: #autolinks
[`badges`]: #badges
[`blog`]: #blog
[`blog.enabled`]: #blogenabled
[`blog.dir`]: #blogdir
[`blog.title`]: #blogtitle
[`blog.id`]: #blogid
[`blog.navbar`]: #blognavbar
[`blog.drafts`]: #blogdrafts
[`blog.tags`]: #blogtags
[`blog.feed`]: #blogfeed
[`blog.feed_limit`]: #blogfeed_limit
[`changelog`]: #changelog
[`code_blocks.enums`]: #code_blocksenums
[`code_blocks.functions`]: #code_blocksfunctions
[`code_blocks.macros`]: #code_blocksmacros
[`code_blocks.namespaces`]: #code_blocksnamespaces
[`code_blocks.types`]: #code_blockstypes
[`code_blocks`]: #code_blocks
[`cpp`]: #cpp
[`defines`]: #macros
[`description`]: #description
[`dot`]: #dot
[`examples.paths`]: #examplespaths
[`examples.patterns`]: #examplespatterns
[`examples.recursive_paths`]: #examplesrecursive_paths
[`examples`]: #examples
[`excluded_symbols`]: #excluded_symbols
[`extra_files`]: #extra_files
[`favicon`]: #favicon
[`generate_tagfile`]: #generate_tagfile
[`github`]: #github
[`gitlab`]: #gitlab
[`html_header`]: #html_header
[`images.paths`]: #imagespaths
[`images.recursive_paths`]: #imagesrecursive_paths
[`images`]: #images
[`implementation_headers`]: #implementation_headers
[`inline_namespaces`]: #inline_namespaces
[`internal_docs`]: #internal_docs
[`license`]: #license
[`lightbox`]: #lightbox
[`logo`]: #logo
[`jquery`]: #jquery
[`macros`]: #macros
[`main_page`]: #main_page
[`meta_tags`]: #meta_tags
[`name`]: #name
[`navbar`]: #navbar
[`private_repo`]: #private_repo
[`robots`]: #robots
[`scripts`]: #scripts
[`show_includes`]: #show_includes
[`site_url`]: #site_url
[`sitemap`]: #sitemap
[`sources.extract_all`]: #sourcesextract_all
[`sources.paths`]: #sourcespaths
[`sources.patterns`]: #sourcespatterns
[`sources.recursive_paths`]: #sourcesrecursive_paths
[`sources.strip_includes`]: #sourcesstrip_includes
[`sources.strip_paths`]: #sourcesstrip_paths
[`sources`]: #sources
[`sponsor`]: #sponsor
[`stylesheets`]: #stylesheets
[`tagfiles`]: #tagfiles
[`theme`]: #theme
[`twitter`]: #twitter
[`warnings`]: #warnings
[`warnings.enabled`]: #warningsenabled
[`warnings.treat_as_errors`]: #warningstreat_as_errors
[`warnings.undocumented`]: #warningsundocumented
[aliases]: #aliases
[author]: #author
[autolinks]: #autolinks
[badges]: #badges
[blog]: #blog
[blog.enabled]: #blogenabled
[blog.dir]: #blogdir
[blog.title]: #blogtitle
[blog.id]: #blogid
[blog.navbar]: #blognavbar
[blog.drafts]: #blogdrafts
[blog.tags]: #blogtags
[blog.feed]: #blogfeed
[blog.feed_limit]: #blogfeed_limit
[changelog]: #changelog
[code_blocks.enums]: #code_blocksenums
[code_blocks.functions]: #code_blocksfunctions
[code_blocks.macros]: #code_blocksmacros
[code_blocks.namespaces]: #code_blocksnamespaces
[code_blocks.types]: #code_blockstypes
[code_blocks]: #code_blocks
[cpp]: #cpp
[defines]: #macros
[description]: #description
[dot]: #dot
[examples.paths]: #examplespaths
[examples.patterns]: #examplespatterns
[examples.recursive_paths]: #examplesrecursive_paths
[examples]: #examples
[excluded_symbols]: #excluded_symbols
[exclude_symbols]: https://www.doxygen.nl/manual/config.html#cfg_exclude_symbols
[extra_files]: #extra_files
[favicon]: #favicon
[generate_tagfile]: #generate_tagfile
[github]: #github
[gitlab]: #gitlab
[html_header]: #html_header
[images.paths]: #imagespaths
[images.recursive_paths]: #imagesrecursive_paths
[images]: #images
[implementation_headers]: #implementation_headers
[inline_namespaces]: #inline_namespaces
[internal_docs]: #internal_docs
[jquery]: #jquery
[license]: #license
[lightbox]: #lightbox
[logo]: #logo
[macros]: #macros
[main_page]: #main_page
[meta_tags]: #meta_tags
[name]: #name
[navbar]: #navbar
[pages]: #pages
[post]: #post
[private_repo]: #private_repo
[robots]: #robots
[scripts]: #scripts
[show_includes]: #show_includes
[site_url]: #site_url
[sitemap]: #sitemap
[sources.extract_all]: #sourcesextract_all
[sources.paths]: #sourcespaths
[sources.patterns]: #sourcespatterns
[sources.recursive_paths]: #sourcesrecursive_paths
[sources.strip_includes]: #sourcesstrip_includes
[sources.strip_paths]: #sourcesstrip_paths
[sources]: #sources
[sponsor]: #sponsor
[stylesheets]: #stylesheets
[tagfiles]: #tagfiles
[theme]: #theme
[twitter]: #twitter
[warnings]: #warnings
[warnings.enabled]: #warningsenabled
[warnings.treat_as_errors]: #warningstreat_as_errors
[warnings.undocumented]: #warningsundocumented
[aliases]: https://www.doxygen.nl/manual/config.html#cfg_aliases
[enabled_sections]: https://www.doxygen.nl/manual/config.html#cfg_enabled_sections
[example_path]: https://www.doxygen.nl/manual/config.html#cfg_example_path
[example_patterns]: https://www.doxygen.nl/manual/config.html#cfg_example_patterns
[example_recursive]: https://www.doxygen.nl/manual/config.html#cfg_example_recursive
[extract_all]: https://www.doxygen.nl/manual/config.html#cfg_extract_all
[file_patterns]: https://www.doxygen.nl/manual/config.html#cfg_file_patterns
[generate_tagfile]: https://www.doxygen.nl/manual/config.html#cfg_generate_tagfile
[html_extra_files]: https://www.doxygen.nl/manual/config.html#cfg_html_extra_files
[html_extra_stylesheet]: https://www.doxygen.nl/manual/config.html#cfg_html_extra_stylesheet
[image_path]: https://www.doxygen.nl/manual/config.html#cfg_image_path
[image_path]: https://www.doxygen.nl/manual/config.html#cfg_image_path
[input]: https://www.doxygen.nl/manual/config.html#cfg_input
[internal_docs]: https://www.doxygen.nl/manual/config.html#cfg_internal_docs
[predefined]: https://www.doxygen.nl/manual/config.html#cfg_predefined
[project_brief]: https://www.doxygen.nl/manual/config.html#cfg_project_brief
[project_logo]: https://www.doxygen.nl/manual/config.html#cfg_project_logo
[project_name]: https://www.doxygen.nl/manual/config.html#cfg_project_name
[recursive]: https://www.doxygen.nl/manual/config.html#cfg_recursive
[strip_from_inc_path]: https://www.doxygen.nl/manual/config.html#cfg_strip_from_inc_path
[strip_from_path]: https://www.doxygen.nl/manual/config.html#cfg_strip_from_path
[tagfiles]: https://www.doxygen.nl/manual/config.html#cfg_tagfiles
[warn_as_error]: https://www.doxygen.nl/manual/config.html#cfg_warn_as_error
[warn_if_undocumented]: https://www.doxygen.nl/manual/config.html#cfg_warn_if_undocumented
[warnings]: https://www.doxygen.nl/manual/config.html#cfg_warnings
[m_favicon]: https://mcss.mosra.cz/documentation/doxygen/#configuration
[m_links_navbar1]: https://mcss.mosra.cz/documentation/doxygen/#navbar-links
[m_links_navbar2]: https://mcss.mosra.cz/documentation/doxygen/#navbar-links
[m_show_undocumented]: https://mcss.mosra.cz/documentation/doxygen/#showing-undocumented-symbols-and-files
[m_theme_color]: https://mcss.mosra.cz/documentation/doxygen/#theme-selection
[USE_MDFILE_AS_MAINPAGE]: https://www.doxygen.nl/manual/config.html#cfg_use_mdfile_as_mainpage
