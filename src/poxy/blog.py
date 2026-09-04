#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Blog post discovery, front matter parsing and post page synthesis.

A post is either a single 'YYYY-MM-DD_title.md' file or a 'YYYY-MM-DD_title/' directory holding an
index.md alongside its images and other media. Posts are compiled into synthetic .dox pages (see
poxy.dox) so their URLs do not depend on the doxygen version or the build path.
"""

import datetime
import email.utils
import html
import re
import urllib.parse
from pathlib import Path

from schema import Optional, Or, Schema, SchemaError

from .mdfilter import fence_mask, slugify
from .schemas import Stripped, ValueOrArray
from .utils import Error, coerce_path

__all__ = [
    r'MARKDOWN_SUFFIXES',
    r'alias_stem',
    r'collect_tags',
    r'extract_excerpt',
    r'format_date',
    r'front_matter_schema',
    r'parse_post_stem',
    r'post_id',
    r'post_output_dir',
    r'render_alias_stub',
    r'render_not_found',
    r'render_rss',
    r'render_sitemap',
    r'rewrite_asset_links',
    r'split_front_matter',
    r'tag_page_id',
    r'tag_size_bucket',
]

# the separator class is kept verbatim from the original implementation, unicode dashes included, so
# that every filename which parses today keeps parsing
_SEP = r'[-֊‐‑‒–—―−_ ,;.]+'
_POST_STEM = re.compile(rf'^(?:blog{_SEP})?((?:[0-9]{{4}}){_SEP}(?:[0-9]{{2}}){_SEP}(?:[0-9]{{2}}))(?:{_SEP}(.+))?$')
_SEP_SUB = re.compile(_SEP)

_FRONT_MATTER_FENCE = r'+++'
_YAML_FENCE = r'---'

# markdown image/link targets that are already absolute or external are never rewritten
_EXTERNAL = re.compile(r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//|#|/)')
_MD_IMAGE = re.compile(r'!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)(?:\s+"(?P<title>[^"]*)")?\)')
_MD_LINKED_IMAGE = re.compile(rf'\[{_MD_IMAGE.pattern}\]\((?P<href>[^)\s]+)\)')

_ALIAS_STEM = re.compile(r'(?i)^[a-z0-9._-]+$')
_MORE_MARKER = re.compile(r'<!--\s*more\s*-->', re.I)
_ATX_HEADING = re.compile(r'^[ \t]*#{1,6}[ \t]')
_DOX_COMMAND = re.compile(r'^[ \t]*[@\\][a-zA-Z]')
_MD_LINK_TEXT = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_MD_MARKUP_RUN = re.compile(r'[*`~]+')

MARKDOWN_SUFFIXES = (r'.md', r'.markdown')

front_matter_schema = Schema(
    {
        Optional(r'title'): Stripped(str, allow_empty=False, name=r'title'),
        Optional(r'date'): Or(datetime.date, datetime.datetime),
        Optional(r'slug'): Stripped(str, allow_empty=False, name=r'slug'),
        Optional(r'draft'): bool,
        Optional(r'description'): Stripped(str, name=r'description'),
        Optional(r'tags'): ValueOrArray(str, name=r'tags'),
        Optional(r'aliases'): ValueOrArray(str, name=r'aliases'),
    }
)


def parse_post_stem(stem: str):
    """Splits a 'YYYY-MM-DD_some_title' or bare 'YYYY-MM-DD' stem into (date, title_part), the latter ''
    when absent. Raises on anything else."""
    m = _POST_STEM.fullmatch(stem)
    if not m:
        raise Error(
            rf"blog post name '{stem}' was not formatted correctly; "
            + r"it should be of the form 'YYYY-MM-DD_this_is_a_post' (or 'YYYY-MM-DD' for a directory)."
        )
    try:
        date = datetime.datetime.strptime(_SEP_SUB.sub(r'-', m[1]), r'%Y-%m-%d').date()
    except Exception as exc:
        raise Error(rf"failed to parse date from blog post name '{stem}': {str(exc)}") from exc
    return date, m[2] or ''


def post_id(date: datetime.date, slug: str) -> str:
    return rf'blog_{date:%Y_%m_%d}_{slug or "post"}'


def post_output_dir(post_dir_name: str) -> str:
    """Output-relative directory holding a day's post media, mirroring the source directory name."""
    return rf'blog/{post_dir_name}'


_MONTHS = (
    r'January',
    r'February',
    r'March',
    r'April',
    r'May',
    r'June',
    r'July',
    r'August',
    r'September',
    r'October',
    r'November',
    r'December',
)


def format_date(date: datetime.date) -> str:
    """Human-readable post date. Spelled out from a table because strftime('%B') is locale-dependent,
    which would make the generated HTML differ between build machines."""
    return rf'{date.day} {_MONTHS[date.month - 1]} {date.year}'


def split_front_matter(text: str):
    """Splits a leading '+++' TOML front matter block off a post body -> (front_matter|None, body)."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if not text.startswith(_FRONT_MATTER_FENCE):
        return None, text
    lines = text.split('\n')
    if lines[0].strip() != _FRONT_MATTER_FENCE:
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONT_MATTER_FENCE:
            return '\n'.join(lines[1:i]), '\n'.join(lines[i + 1 :]).lstrip('\n')
    return None, text


def parse_front_matter(text: str, source: Path) -> dict:
    try:
        import tomllib as toml
    except ImportError:
        import tomli as toml  # pyright: ignore[reportMissingImports]

    try:
        data = toml.loads(text)
    except Exception as exc:
        raise Error(rf'{source}: could not parse front matter: {str(exc)}') from exc
    try:
        data = front_matter_schema.validate(data)
    except SchemaError as exc:
        raise Error(rf'{source}: invalid front matter: {str(exc)}') from exc

    if r'date' in data and isinstance(data[r'date'], datetime.datetime):
        data[r'date'] = data[r'date'].date()
    return data


def has_yaml_front_matter(text: str) -> bool:
    return text.lstrip().startswith(_YAML_FENCE)


def rewrite_asset_links(body: str, assets, url_prefix: str) -> str:
    """Points a post's markdown image references at the media poxy stages beside the built page.

    Emitted as @htmlonly rather than left as markdown because doxygen resolves an image by basename
    against IMAGE_PATH, so two posts each carrying a 'diagram.png' silently collide and one of them
    never reaches the output at all. External images take the same route only to dodge m.css's
    "not found in XML_OUTPUT" warning, which it emits for every image it is not itself staging.
    """
    # keyed on the post-relative path, which is the layout the assets are staged under, so a
    # reference to 'sub/nested.svg' resolves as readily as one to 'diagram.png'
    names = {a[r'name'] for a in assets}
    lines = body.split('\n')
    mask = fence_mask(lines)

    def img(m) -> str:
        src = m[r'src']
        external = bool(_EXTERNAL.match(src))
        if not external and src.lstrip(r'./') not in names:
            return ''
        src = src if external else rf'{url_prefix}/{src.lstrip(r"./")}'
        attrs = rf'class="m-image" src="{html.escape(src, quote=True)}"'
        attrs += rf' alt="{html.escape(m[r"alt"] or "", quote=True)}"'
        if m[r'title']:
            attrs += rf' title="{html.escape(m[r"title"], quote=True)}"'
        return rf'<img {attrs} />'

    def sub(m) -> str:
        tag = img(m)
        return m[0] if not tag else rf'@htmlonly{tag}@endhtmlonly'

    def sub_linked(m) -> str:
        tag = img(m)
        if not tag:
            return m[0]
        href = html.escape(m[r'href'], quote=True)
        return rf'@htmlonly<a href="{href}">{tag}</a>@endhtmlonly'

    for i, line in enumerate(lines):
        if mask[i]:
            continue
        # linked images first: the inner image pattern would otherwise match and strand the markdown link
        lines[i] = _MD_LINKED_IMAGE.sub(sub_linked, line)
        lines[i] = _MD_IMAGE.sub(sub, lines[i])
    return '\n'.join(lines)


def enumerate_posts(blog_dir: Path):
    """Yields (source_md, post_dir|None) for every post under blog_dir, sorted by name.

    A post is a 'YYYY-MM-DD_title.md' file, or any markdown file inside a 'YYYY-MM-DD/' directory, which
    holds that day's posts and their media. Directories named any other way are left alone.
    """
    blog_dir = coerce_path(blog_dir)
    if not blog_dir.is_dir():
        return
    for entry in sorted(blog_dir.iterdir(), key=lambda p: p.name):
        if entry.is_dir():
            m = _POST_STEM.fullmatch(entry.name)
            # a directory that does not start with a date is somebody's scratch space, not a broken post
            if not m:
                continue
            if m[2]:
                raise Error(
                    rf"blog post directory {entry} should be named for its date alone ('YYYY-MM-DD'); "
                    + r'a post takes its title from its front matter or first heading'
                )
            sources = sorted(p for p in entry.iterdir() if p.is_file() and p.suffix.lower() in MARKDOWN_SUFFIXES)
            if not sources:
                raise Error(rf'blog post directory {entry} contains no markdown')
            for source in sources:
                yield source, entry
        elif entry.suffix.lower() in MARKDOWN_SUFFIXES:
            yield entry, None


def alias_stem(value: str) -> str:
    """Normalises a declared alias to the page name its redirect stub is written at, or '' if it could
    not be one.

    Deliberately not slugified: an alias is an old URL, and a slug of it would point the redirect at an
    address nobody ever linked to. A trailing '.html' is accepted and dropped.
    """
    stem = str(value).strip()
    if stem.lower().endswith(r'.html'):
        stem = stem[: -len(r'.html')]
    if stem in ('', r'.', r'..') or not _ALIAS_STEM.fullmatch(stem):
        return ''
    return stem


def post_assets(post_dir):
    """Every file in a day's directory other than the posts themselves, as {name, path} sorted for a
    deterministic build. 'name' is the directory-relative path, which is how a post references it and
    how it is staged in the output."""
    if post_dir is None:
        return []
    files = (f for f in post_dir.rglob(r'*') if f.is_file() and f.suffix.lower() not in MARKDOWN_SUFFIXES)
    return sorted(({r'name': f.relative_to(post_dir).as_posix(), r'path': f} for f in files), key=lambda a: a[r'name'])


def extract_excerpt(body: str, limit: int = 280) -> str:
    """A plain-text summary of a post: the text above a '<!--more-->' marker, else the first paragraph.

    Works on the source markdown rather than the rendered HTML, which by that point carries mdfilter's
    sentinels, m.css's injected <wbr> elements and doxygen's own entity mangling.
    """
    m = _MORE_MARKER.search(body)
    if m:
        body = body[: m.start()]

    lines = body.split('\n')
    mask = fence_mask(lines)
    kept = []
    for i, line in enumerate(lines):
        if mask[i] or _ATX_HEADING.match(line) or _DOX_COMMAND.match(line):
            if kept:
                break
            continue
        if not line.strip():
            if kept:
                break
            continue
        kept.append(line.strip())

    text = ' '.join(kept)
    text = _MD_IMAGE.sub('', text)
    text = _MD_LINK_TEXT.sub(r'\1', text)
    text = _MD_MARKUP_RUN.sub('', text)
    text = re.sub(r'\s+', r' ', text).strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(' ', 1)[0].rstrip(r'.,;:!?-')
    return rf'{clipped}...'


def tag_page_id(slug: str) -> str:
    return rf'blog_tag_{slug}'


def tag_size_bucket(count: int, lowest: int, highest: int) -> int:
    """m.css's tag cloud sizes are .m-tag-1 through .m-tag-5."""
    return 1 + (4 * (count - lowest)) // max(1, highest - lowest)


def collect_tags(posts):
    """Maps tag slug -> {display, posts}, merging spellings case-insensitively.

    Posts arrive newest first, so the display form is the most recent spelling the author used.
    """
    tags = {}
    for post in posts:
        for tag in post[r'tags']:
            slug = slugify(tag)
            if not slug:
                continue
            entry = tags.setdefault(slug, {r'display': tag, r'posts': []})
            entry[r'posts'].append(post)
    return dict(sorted(tags.items()))


def _rfc822(date: datetime.date) -> str:
    # email.utils rather than strftime, whose weekday and month names are locale-dependent
    return email.utils.format_datetime(
        datetime.datetime(date.year, date.month, date.day, tzinfo=datetime.timezone.utc), usegmt=True
    )


def _feed_guid(site_url: str, post) -> str:
    """A tag: URI, not the post URL, so changing a post's URL does not re-deliver it to every subscriber."""
    host = urllib.parse.urlparse(site_url).netloc or r'poxy'
    return rf'tag:{host},{post["date"]:%Y-%m-%d}:{post["id"]}'


def render_rss(site_url: str, name: str, description: str, author: str, posts, limit: int = 20) -> str:
    """An RSS 2.0 feed of the most recent posts.

    RSS rather than Atom because poxy's 'author' option is optional, and Atom requires a feed-level
    author unless every entry carries one, so an Atom feed from a minimal poxy.toml would be invalid.
    Carries no build timestamp, so an unchanged blog produces a byte-identical file every run.
    """
    posts = list(posts)[:limit]
    esc = lambda s: html.escape(str(s), quote=False)

    lines = [
        r'<?xml version="1.0" encoding="utf-8"?>',
        r'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        + r'xmlns:dc="http://purl.org/dc/elements/1.1/">',
        r'	<channel>',
        rf'		<title>{esc(name)}</title>',
        rf'		<link>{esc(site_url)}/</link>',
        rf'		<description>{esc(description)}</description>',
        rf'		<atom:link href="{esc(site_url)}/feed.xml" rel="self" type="application/rss+xml" />',
    ]
    if posts:
        lines.append(rf'		<pubDate>{_rfc822(posts[0][r"date"])}</pubDate>')
    for post in posts:
        url = rf'{site_url}/{post["id"]}.html'
        lines.append(r'		<item>')
        lines.append(rf'			<title>{esc(post[r"title"])}</title>')
        lines.append(rf'			<link>{esc(url)}</link>')
        lines.append(rf'			<guid isPermaLink="false">{esc(_feed_guid(site_url, post))}</guid>')
        lines.append(rf'			<pubDate>{_rfc822(post[r"date"])}</pubDate>')
        if post[r'excerpt']:
            lines.append(rf'			<description>{esc(post[r"excerpt"])}</description>')
        if author:
            # <author> is required by the spec to be an email address, which poxy does not have
            lines.append(rf'			<dc:creator>{esc(author)}</dc:creator>')
        for tag in post[r'tags']:
            lines.append(rf'			<category>{esc(tag)}</category>')
        lines.append(r'		</item>')
    lines += [r'	</channel>', r'</rss>', '']
    return '\n'.join(lines)


def render_sitemap(site_url: str, page_names, posts) -> str:
    """A sitemap of every generated page. lastmod comes from post dates only, never file mtimes,
    which are worthless in CI where a fresh clone stamps every file identically."""
    dates = {rf'{p["id"]}.html': p[r'date'] for p in posts}
    lines = [r'<?xml version="1.0" encoding="utf-8"?>', r'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name in sorted(set(page_names)):
        lines.append(r'	<url>')
        lines.append(rf'		<loc>{html.escape(rf"{site_url}/{name}", quote=False)}</loc>')
        if name in dates:
            lines.append(rf'		<lastmod>{dates[name]:%Y-%m-%d}</lastmod>')
        lines.append(r'	</url>')
    lines += [r'</urlset>', '']
    return '\n'.join(lines)


def render_not_found(name: str, site_url: str) -> str:
    """A 404 page. Cannot go through the .dox mechanism because the file must be named '404.html'
    exactly for GitHub Pages, Netlify and Cloudflare Pages to serve it.

    Its references are root-relative, derived from site_url's path: the host serves this one file for
    URLs at any depth, so a relative 'poxy/poxy.css' would 404 alongside it.
    """
    root = urllib.parse.urlparse(site_url).path.rstrip(r'/')
    root = rf'{root}/' if root else r'/'
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex">\n'
        rf'<title>Not found | {html.escape(name)}</title>' + '\n'
        rf'<link rel="stylesheet" href="{html.escape(root, quote=True)}poxy/poxy.css">' + '\n'
        '</head>\n'
        '<body>\n'
        '<div class="m-container">\n'
        '<h1>Not found</h1>\n'
        '<p>That page does not exist. It may have been renamed or removed.</p>\n'
        rf'<p><a href="{html.escape(root, quote=True)}index.html">Back to {html.escape(name)}</a></p>' + '\n'
        '</div>\n'
        '</body>\n'
        '</html>\n'
    )


def render_alias_stub(target: str, title: str) -> str:
    """A redirect page for a post's old URL, so a rename does not strand inbound links."""
    target = html.escape(target, quote=True)
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        rf'<meta http-equiv="refresh" content="0; url={target}">' + '\n'
        rf'<link rel="canonical" href="{target}">' + '\n'
        '<meta name="robots" content="noindex">\n'
        rf'<title>{html.escape(title)}</title>' + '\n'
        '</head>\n'
        '<body>\n'
        rf'<p>This page has moved to <a href="{target}">{html.escape(title)}</a>.</p>' + '\n'
        '</body>\n'
        '</html>\n'
    )
