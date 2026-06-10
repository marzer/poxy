# Square-bracket [tags]

Doxygen's support for raw inline HTML is limited and easy to mangle. To work around this, poxy lets you
embed a small set of square-bracket tags in documentation comments. They pass through Doxygen and m.css
untouched and are applied afterwards by poxy's HTML post-processor, giving you reliable inline control
over the generated markup: CSS classes, element wrappers, ids, entities and emoji.

Tags are ignored inside `@code` / `<pre>` / `<code>` blocks, so code samples are never disturbed.

- [Wrappers](#wrappers)
- [CSS classes](#css-classes)
- [Targeting the parent element](#targeting-the-parent-element)
- [Ids and tag names](#ids-and-tag-names)
- [Entities and emoji](#entities-and-emoji)

<br>

## Wrappers

A paired tag wraps its content in the matching HTML element, with optional attributes:

```
[span class="m-text m-dim"]quiet text[/span]
[center]centred[/center]
```

Available wrappers: `aside`, `b`, `center`, `code`, `div`, `em`, `h1`–`h6`, `i`, `li`, `ol`, `p`,
`pre`, `span`, `strong`, `u`, `ul`.

<br>

## CSS classes

The most useful tags attach [m.css] CSS classes to the surrounding element. This is how you colour a
paragraph as a note, turn something into a label, and so on.

| Tag                    | Effect                            |
| ---------------------- | --------------------------------- |
| `[set_class names]`    | replace the element's classes     |
| `[add_class names]`    | add to the element's classes      |
| `[remove_class names]` | remove from the element's classes |

```
[set_class m-note m-info]This paragraph becomes a blue info note.
```

m.css provides a colour palette you can apply with these: `m-default`, `m-primary`, `m-success`,
`m-warning`, `m-danger`, `m-info`, `m-dim`, `m-special`, alongside container classes such as `m-note`,
`m-block`, `m-label` and `m-button`. See the m.css [documentation][m.css] for the full set.

Several built-in [aliases](aliases.md) are thin wrappers over these tags (for example `@inline_note`
expands to `[set_class m-note m-info]`).

<br>

## Targeting the parent element

Your text is usually wrapped in a `<p>` that is itself inside some container, so the element you want to
style is often an ancestor rather than the immediate one. The `parent_` and `parent_parent_` prefixes
walk up one or two levels:

```
[parent_set_class m-block m-warning]
[parent_parent_add_class m-text-center]
```

Every class operation has these variants: `parent_set_class` / `set_parent_class`,
`parent_add_class` / `add_parent_class`, `parent_remove_class` / `remove_parent_class`, and the
`parent_parent_` forms. The two spellings (prefix vs. suffix) are equivalent.

<br>

## Ids and tag names

| Tag                | Effect                        |
| ------------------ | ----------------------------- |
| `[set_id value]`   | set the element's `id`        |
| `[set_name value]` | change the element's tag name |

The `parent_` and `parent_parent_` variants apply here too (`parent_set_id`, `parent_set_name`, ...).

<br>

## Entities and emoji

| Tag             | Result                                                                   |
| --------------- | ------------------------------------------------------------------------ |
| `[entity name]` | the named HTML entity, e.g. `[entity nbsp]` &rarr; a non-breaking space  |
| `[entity hex]`  | a numeric character reference, e.g. `[entity 2764]`                      |
| `[emoji name]`  | an emoji by its GitHub name, e.g. `[emoji tada]` is the same as `:tada:` |

`[htmlentity ...]` is accepted as a synonym for `[entity ...]`.

[m.css]: https://mcss.mosra.cz/documentation/doxygen/
