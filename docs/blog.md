# Blog

Poxy can build a blog alongside your API documentation. Posts are markdown, they live in a `blog`
directory next to your `poxy.toml`, and everything else is derived from them.

- [Quick start](#quick-start)
- [Where posts live](#where-posts-live)
- [Front matter](#front-matter)
- [Images and other media](#images-and-other-media)
- [What gets generated](#what-gets-generated)
- [Drafts](#drafts)
- [Tags](#tags)
- [Feeds and sitemaps](#feeds-and-sitemaps)
- [Renaming a post](#renaming-a-post)

<br><br>

## Quick start

```sh
poxyblog 'Hello, World!'
```

That creates `blog/2026-01-15_hello_world.md` with a front matter block ready to fill in. Write the post
body under it, run `poxy`, and the post appears at `blog_2026_01_15_hello_world.html` with a `Blog` entry
in the navbar.

No configuration is needed. A blog is built whenever the directory exists and holds at least one post.

<br><br>

## Where posts live

A post is either a single markdown file named for its date and a name of your choosing, or an `index.md`
inside a directory named for its date alone:

```
blog/
    2026-01-15_hello_world.md       ->  blog_2026_01_15_hello_world.html
    2026-03-02/                     ->  blog_2026_03_02.html
        index.md
        diagram.png
        benchmark.svg
```

Use the directory form when a post has images or other media, so they sit beside the text they belong to.
The title then comes from the post itself: its front matter, or its first heading.

A day can hold more than one post. Name the others `some_name.md` rather than `index.md`; they share the
directory's media and land at `blog_2026_03_02_some_name.html`.

The name carries the publication date and must start with `YYYY-MM-DD`. A name poxy cannot parse is a
hard error, not a warning. A warning would let a post go quietly missing from the published site, for a
reader to find later.

The file name is also the post's address, so revising a title never moves a published page. Only renaming
the file does, which is a deliberate act you can see in a diff. Two posts that resolve to the same address
are an error naming both files.

`poxyblog` builds the name for you from the title you give it, so a new post still gets a readable URL
without you thinking about it.

<br><br>

## Front matter

An optional TOML block fenced by `+++`, which must begin on the very first line:

```toml
+++
title       = "Shipping v2"
date        = 2026-03-02
slug        = "shipping_v2"
draft       = false
description = "What changed, and what to do about it."
tags        = ["c++", "release notes"]
aliases     = ["old_post_name"]
+++
```

Every field is optional, and a post with no front matter at all still works: the title then comes from the
body's first `#` heading, and the date from the filename.

| field         | effect                                                                       |
| ------------- | ---------------------------------------------------------------------------- |
| `title`       | Overrides the body's `#` heading                                             |
| `date`        | Overrides the date in the filename                                           |
| `slug`        | Overrides the name taken from the filename, changing the output filename     |
| `draft`       | Excludes the post unless drafts are enabled                                  |
| `description` | Used as the excerpt, the page brief, and the feed and social summaries       |
| `tags`        | Generates tag pages and adds tag links to the post                           |
| `aliases`     | Old page names that should redirect here                                     |

An unrecognised key is an error naming the file, so a typo cannot silently do nothing.

YAML front matter is not supported. A post starting with `---` is rejected with a message saying so.

Post bodies are markdown, and Doxygen commands work in them. `@ref my_class` links a post to your API
documentation, which is most of the reason to keep a blog in your docs at all.

Headings get anchors derived from their text, so deep links into a post survive the blog growing around
it. Pin one yourself by writing the anchor explicitly:

```markdown
## Benchmark results {#benchmarks}
```

A `{#label}` on the post's title heading becomes an anchor at the top of the page, so an old `@ref` to it
still resolves.

<br><br>

## Images and other media

Put them in the post's directory and reference them by name:

```markdown
![a flame graph](benchmark.svg)
```

Poxy copies the file to `blog/YYYY-MM-DD/` in the output and points the image at it, so a `diagram.png`
in one post never overwrites another's. Subdirectories work too, referenced by their path relative to the
post: `![](figures/flame.svg)`.

External images need no setup. Poxy routes them through the same rewrite, so a post's images all reach
the page the same way.

An image in a post is scaled to the width of the text, so clicking one opens it full-size in an overlay,
which closes on a click, on the close button, or on escape. [`lightbox`] turns that off; the alt text
becomes the overlay's caption, so it is worth writing.

<br><br>

## What gets generated

| page              | file                                |
| ----------------- | ----------------------------------- |
| post              | `blog_<YYYY>_<MM>_<DD>_<slug>.html` |
| post, day `index` | `blog_<YYYY>_<MM>_<DD>.html`        |
| index             | `blog.html`                         |
| tag               | `blog_tag_<slug>.html`              |
| tag index         | `blog_tags.html`                    |
| feed              | `feed.xml`                          |
| sitemap           | `sitemap.xml`                       |
| not found         | `404.html`                          |

Post URLs are a documented contract: they depend only on the date and the slug, never on the title,
where the project was built, or which Doxygen version built it. Nothing is ever numbered by position, so
adding or removing a post cannot move another one.

The index lists posts newest first with their dates and excerpts. Each post gets a date and tag byline,
a breadcrumb back to the index, and previous and next links.

<br><br>

## Drafts

```toml
+++
title = "Not ready yet"
draft = true
+++
```

A draft is skipped entirely. To preview one locally:

```sh
poxy --drafts
```

Built drafts carry a `Draft` chip and `noindex`, so publishing one by accident does not put it in front
of a search engine.

<br><br>

## Tags

Tags come from front matter. Poxy slugifies them and merges spellings that differ only in case, so
`C++` and `c++` are one tag. Each tag gets a page listing its posts, and `blog_tags.html` lists every
tag as the same chip a post's byline carries, each with its post count.

Tag pages join the search index alongside your C++ symbols. Set [`blog.tags`] to `false` if you would
rather they did not; tags still appear on posts, just without links.

<br><br>

## Feeds and sitemaps

Both need to know where the site will be published:

```toml
site_url = 'https://marzer.github.io/tomlplusplus'
```

With it set, poxy writes an RSS 2.0 feed at `feed.xml`, advertises it for autodiscovery in every page's
`<head>`, links it in the footer, and writes a `sitemap.xml`. Without it, neither is generated, since
both need absolute URLs and a wrong base URL in a published feed is worse than no feed.

Feed entries are identified by a `tag:` URI, not by their URL, so renaming a post does not re-deliver it
to everyone subscribed. The file carries no build timestamp, so an unchanged blog produces
a byte-identical feed every run and does not churn in version control.

<br><br>

## Renaming a post

Retitling a post is free, since the URL comes from the file name. Renaming the file or setting a `slug`
does change the URL. List the old name in `aliases` and poxy writes a redirect page at the old address:

```toml
+++
title   = "Shipping v2"
aliases = ["blog_2026_03_02_shipping_version_2"]
+++
```

An alias is taken as the literal page name, so paste the old URL rather than a tidied-up version of it;
a trailing `.html` is fine. This is what rescues a page Doxygen used to name, whose URL looked nothing
like a slug.

Stubs redirect immediately, declare the new page as canonical, carry `noindex`, and stay out of the
sitemap.

[`blog.tags`]: configuration.md#blogtags
[`lightbox`]: configuration.md#lightbox
