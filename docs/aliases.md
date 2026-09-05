# Doxygen @alias commands

On top of Doxygen's built-in commands, poxy registers the aliases below. They work in any documentation
comment. Both the `@command` and `\command` spellings are accepted; this page uses `@`.

You can define your own with the [`aliases`](configuration.md#aliases) config option.

- [Code blocks](#code-blocks)
- [Field decorators](#field-decorators)
- [Note boxes](#note-boxes)
- [Links](#links)
- [Figures](#figures)
- [Video embeds](#video-embeds)
- [Tabbed content](#tabbed-content)
- [m.css passthrough](#mcss-passthrough)

<br>

## Code blocks

Shorthands for `@code{.lang}` ... `@endcode`. The `e`-prefixed and `end`-prefixed closers are
equivalent (`@ecpp` and `@endcpp` both close `@cpp`).

| Open          | Close                             | Language                       |
| ------------- | --------------------------------- | ------------------------------ |
| `@cpp`        | `@ecpp` / `@endcpp`               | C++                            |
| `@python`     | `@epython` / `@endpython`         | Python                         |
| `@meson`      | `@emeson` / `@endmeson`           | Meson (Python highlight)       |
| `@cmake`      | `@ecmake` / `@endcmake`           | CMake                          |
| `@javascript` | `@ejavascript` / `@endjavascript` | JavaScript                     |
| `@json`       | `@ejson` / `@endjson`             | JSON (JavaScript highlight)    |
| `@shell`      | `@eshell` / `@endshell`           | shell session                  |
| `@bash`       | `@ebash` / `@endbash`             | Bash                           |
| `@out`        | `@eout` / `@endout`               | command output (shell session) |

```cpp
/// @cpp
/// auto x = make_thing();
/// @ecpp
```

`@detail` is also provided as an alias for `@details`.

<br>

## Field decorators

These flag a member in its detailed description with a coloured block. They are handy for documenting
config structs, message schemas, and similar.

| Alias           | Renders as                                                                          |
| --------------- | ----------------------------------------------------------------------------------- |
| `@required`     | a red "Required field" block                                                        |
| `@optional`     | a blue "Optional field" block                                                       |
| `@availability` | a "Conditional availability" block                                                  |
| `@implementers` | a dimmed "Implementers:" block, for notes aimed at people implementing an interface |
| `@flags_enum`   | a note stating the enum is a flags type with a full set of bitwise operators        |

```cpp
struct config
{
    /// @brief The host to connect to.
    /// @required
    std::string host;

    /// @brief The port. Defaults to 443.
    /// @optional
    int port;
};
```

`@conditional_return{condition}` documents a return value that depends on some condition; the condition
is emphasised and followed by your description:

```cpp
/// @conditional_return{On success} the parsed value.
/// @conditional_return{On failure} a null handle.
```

<br>

## Note boxes

Each of these turns the paragraph it begins into a coloured note box.

| Alias               | Colour           |
| ------------------- | ---------------- |
| `@inline_note`      | info (blue)      |
| `@inline_attention` | warning (yellow) |
| `@inline_warning`   | danger (red)     |
| `@inline_success`   | success (green)  |
| `@inline_remark`    | default (grey)   |

```cpp
/// @details
/// @inline_warning this whole paragraph renders as a red note box.
```

`@inline_subheading{text}` emits a small heading (an `<h4>`) within a description block.

<br>

## Links

| Alias                                   | Result                                                            |
| --------------------------------------- | ----------------------------------------------------------------- |
| `@github{user/repo}`                    | a link to that page on GitHub (link text is the path)             |
| `@github{user/repo,text}`               | the same, with custom link text                                   |
| `@gitlab{path}` / `@gitlab{path,text}`  | the same for GitLab                                               |
| `@godbolt{id}`                          | a "Try this code on Compiler Explorer" link to `godbolt.org/z/id` |

<br>

## Figures

`@figure` wraps Doxygen's `@image html`:

| Alias                    | Equivalent to                |
| ------------------------ | ---------------------------- |
| `@figure{file}`          | `@image html file`           |
| `@figure{file,caption}`  | `@image html file "caption"` |

<br>

## Video embeds

**Since v0.27.0**

| Alias                    | Result                                                    |
| ------------------------ | --------------------------------------------------------- |
| `@youtube{id}`           | that video, embedded, filling the width at 16:9           |
| `@youtube{id,title}`     | the same, with a title for screen readers                 |

The `id` is the `v=` parameter of a watch URL, so `youtu.be/dQw4w9WgXcQ` is `@youtube{dQw4w9WgXcQ}`.
The player is loaded from `youtube-nocookie.com`, and lazily, so a page carrying several costs nothing
until one is scrolled to.

<br>

## Tabbed content

Group related content (most often the same example in several languages) into a tabbed widget. Write
`@tabs` ... `@endtabs` around the block, and start each tab with `@tab{title}`:

```cpp
/// @tabs
///
/// @tab{C++}
/// @cpp
/// auto x = foo();
/// @endcpp
///
/// @tab{Python}
/// @python
/// x = foo()
/// @endpython
///
/// @endtabs
```

The closers `@etabs` and `@endtabs` are equivalent. A panel can hold anything, not just code.

**Separate `@tabs`, `@tab` and `@endtabs` with blank lines.** Doxygen only starts a list or block at the
beginning of a line, so without the blank lines it merges the markers into one paragraph and the widget
cannot be assembled (poxy warns when this happens). The tab switching is pure CSS, so it works with
JavaScript disabled.

<br>

## m.css passthrough

These forward to [m.css]'s own commands; see the m.css [documentation][m.css] for details.

| Alias                                       | Purpose                                            |
| ------------------------------------------- | -------------------------------------------------- |
| `@m_div{class}` / `@m_enddiv`               | wrap content in a `<div>` with the given CSS class |
| `@m_span{class}` / `@m_endspan`             | the same for a `<span>`                            |
| `@m_class{class}`                           | apply a CSS class to the next paragraph or element |
| `@m_footernavigation`                       | add this page to the prev/next footer navigation   |
| `@m_examplenavigation{page,prefix}`         | example-listing navigation                         |
| `@m_keywords{list}`                         | extra search keywords for the page                 |
| `@m_keyword{keyword,title,suffix-length}`   | a single richer search keyword                     |
| `@m_enum_values_as_keywords`                | index an enum's values as search keywords          |

[m.css]: https://mcss.mosra.cz/documentation/doxygen/
