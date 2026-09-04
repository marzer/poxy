#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Unit tests for blog post discovery, front matter parsing and asset link rewriting (poxy.blog).
"""

import datetime
from pathlib import Path

import pytest

from poxy import blog, config
from poxy.utils import Error


def test_parse_post_stem_reads_the_leading_date():
    assert blog.parse_post_stem('2026-01-15_hello_world') == (datetime.date(2026, 1, 15), 'hello_world')


def test_parse_post_stem_accepts_the_legacy_separators_and_prefix():
    # the separator class carries unicode dashes; anything that parsed before must keep parsing
    for stem in ('blog-2026-01-15-hello', '2026.01.15.hello', '2026_01_15_hello', '2026–01–15–hello'):
        date, title = blog.parse_post_stem(stem)
        assert date == datetime.date(2026, 1, 15)
        assert title == 'hello'


def test_parse_post_stem_allows_punctuation_in_the_title_part():
    assert blog.parse_post_stem('2026-01-15_hello, world!')[1] == 'hello, world!'


def test_parse_post_stem_accepts_a_bare_date():
    # the directory form: the title lives in the post, so the name is the date alone
    assert blog.parse_post_stem('2026-01-15') == (datetime.date(2026, 1, 15), '')
    with pytest.raises(Error):
        blog.parse_post_stem('2026-01-15_')  # a separator with nothing after it is neither form


def test_parse_post_stem_rejects_a_missing_or_invalid_date():
    # a malformed name stays a hard error: downgrading it would silently drop the post from the site
    with pytest.raises(Error):
        blog.parse_post_stem('hello_world')
    with pytest.raises(Error):
        blog.parse_post_stem('2026-13-45_hello')


def test_post_id_and_output_dir():
    date = datetime.date(2026, 1, 15)
    assert blog.post_id(date, 'hello_world') == 'blog_2026_01_15_hello_world'
    assert blog.post_id(date, '') == 'blog_2026_01_15_post'
    assert blog.post_output_dir('2026-01-15') == 'blog/2026-01-15'


def test_format_date_is_locale_independent():
    # strftime('%B') would vary by build machine and break the goldens
    assert blog.format_date(datetime.date(2026, 3, 2)) == '2 March 2026'
    assert blog.format_date(datetime.date(2026, 12, 31)) == '31 December 2026'


def test_split_front_matter_extracts_a_leading_toml_block():
    fm, body = blog.split_front_matter('+++\ntitle = "Hi"\n+++\n\nBody.\n')
    assert fm == 'title = "Hi"'
    assert body == 'Body.\n'


def test_split_front_matter_is_a_no_op_without_a_leading_fence():
    for text in ('# A README\n\n+++\nnot front matter\n+++\n', 'plain body\n', '---\ntitle: yaml\n---\n'):
        fm, body = blog.split_front_matter(text)
        assert fm is None
        assert body == text


def test_split_front_matter_leaves_an_unterminated_fence_alone():
    text = '+++\ntitle = "Hi"\n\nbody with no closing fence\n'
    assert blog.split_front_matter(text) == (None, text)


def test_parse_front_matter_accepts_the_documented_keys():
    data = blog.parse_front_matter(
        'title = "Hi"\ndate = 2026-01-15\nslug = "s"\ndraft = true\ntags = ["a", "b"]\n', Path('x.md')
    )
    assert data['title'] == 'Hi'
    assert data['date'] == datetime.date(2026, 1, 15)
    assert data['draft'] is True
    assert data['tags'] == ['a', 'b']


def test_parse_front_matter_rejects_unknown_keys_and_bad_types():
    with pytest.raises(Error):
        blog.parse_front_matter('titel = "typo"\n', Path('x.md'))
    with pytest.raises(Error):
        blog.parse_front_matter('draft = "yes"\n', Path('x.md'))


def test_parse_front_matter_reports_malformed_toml_against_the_file():
    with pytest.raises(Error, match='x.md'):
        blog.parse_front_matter('title = "unterminated\n', Path('x.md'))


def test_yaml_front_matter_is_detected_so_it_can_be_rejected_with_a_clear_message():
    assert blog.has_yaml_front_matter('---\ntitle: Hi\n---\n')
    assert not blog.has_yaml_front_matter('+++\ntitle = "Hi"\n+++\n')


def test_rewrite_asset_links_points_local_images_at_the_staged_copy():
    out = blog.rewrite_asset_links(
        '![alt](diagram.png)\n', [{'name': 'diagram.png', 'path': Path('diagram.png')}], 'blog/2026-01-15_post'
    )
    assert out == '@htmlonly<img class="m-image" src="blog/2026-01-15_post/diagram.png" alt="alt" />@endhtmlonly\n'


def test_rewrite_asset_links_leaves_unknown_local_targets_to_doxygen():
    body = '![alt](not_an_asset.png)\n'
    assert blog.rewrite_asset_links(body, [{'name': 'diagram.png', 'path': Path('diagram.png')}], 'blog/p') == body


def test_rewrite_asset_links_routes_external_images_around_doxygen():
    # m.css warns for every image it is not itself staging, external ones included
    out = blog.rewrite_asset_links('![a](https://example.com/x.png)\n', [], 'blog/p')
    assert 'src="https://example.com/x.png"' in out
    assert out.startswith('@htmlonly<img')


def test_rewrite_asset_links_ignores_fenced_code():
    body = '```\n![alt](diagram.png)\n```\n'
    assert blog.rewrite_asset_links(body, [{'name': 'diagram.png', 'path': Path('diagram.png')}], 'blog/p') == body


def test_rewrite_asset_links_escapes_alt_and_title():
    out = blog.rewrite_asset_links(
        '![a "quoted" & <alt>](diagram.png "a <title>")\n',
        [{'name': 'diagram.png', 'path': Path('diagram.png')}],
        'blog/p',
    )
    assert 'alt="a &quot;quoted&quot; &amp; &lt;alt&gt;"' in out
    assert 'title="a &lt;title&gt;"' in out


def test_rewrite_asset_links_resolves_a_nested_asset_by_its_relative_path():
    assets = [{'name': 'sub/nested.svg', 'path': Path('sub/nested.svg')}]
    out = blog.rewrite_asset_links('![a](sub/nested.svg)\n', assets, 'blog/p')
    assert 'src="blog/p/sub/nested.svg"' in out


def test_rewrite_asset_links_keeps_the_anchor_around_a_linked_image():
    assets = [{'name': 'diagram.png', 'path': Path('diagram.png')}]
    out = blog.rewrite_asset_links('[![alt](diagram.png)](https://example.com)\n', assets, 'blog/p')
    assert out.startswith('@htmlonly<a href="https://example.com"><img ')
    assert out.rstrip().endswith('</a>@endhtmlonly')


def test_enumerate_posts_finds_both_the_file_and_directory_forms(tmp_path):
    (tmp_path / '2026-01-15_single.md').write_text('# A\n', encoding='utf-8')
    folder = tmp_path / '2026-02-20'
    folder.mkdir()
    (folder / 'index.md').write_text('# B\n', encoding='utf-8')
    (folder / 'diagram.png').write_bytes(b'\x89PNG')

    found = list(blog.enumerate_posts(tmp_path))
    assert [(s.name, d.name if d else None) for s, d in found] == [
        ('2026-01-15_single.md', None),
        ('index.md', '2026-02-20'),
    ]


def test_enumerate_posts_yields_every_post_in_a_day_directory(tmp_path):
    folder = tmp_path / '2026-02-20'
    folder.mkdir()
    (folder / 'index.md').write_text('# B\n', encoding='utf-8')
    (folder / 'another.md').write_text('# C\n', encoding='utf-8')
    (folder / 'diagram.png').write_bytes(b'\x89PNG')
    assert [s.name for s, _ in blog.enumerate_posts(tmp_path)] == ['another.md', 'index.md']


def test_enumerate_posts_rejects_a_titled_directory(tmp_path):
    # the title belongs in the post; a dated-and-titled directory is the one shape that means nothing
    folder = tmp_path / '2026-01-15_titled'
    folder.mkdir()
    (folder / 'index.md').write_text('# A\n', encoding='utf-8')
    with pytest.raises(Error, match='date alone'):
        list(blog.enumerate_posts(tmp_path))


def test_enumerate_posts_rejects_a_day_directory_with_no_posts(tmp_path):
    (tmp_path / '2026-01-15').mkdir()
    with pytest.raises(Error, match='no markdown'):
        list(blog.enumerate_posts(tmp_path))


def test_enumerate_posts_ignores_a_directory_that_does_not_name_a_post(tmp_path):
    # somebody's scratch space or a shared image folder, not a broken post
    (tmp_path / 'shared_images').mkdir()
    (tmp_path / '2026-01-15_real.md').write_text('# A\n', encoding='utf-8')
    assert [s.name for s, _ in blog.enumerate_posts(tmp_path)] == ['2026-01-15_real.md']


def test_enumerate_posts_yields_nothing_for_a_missing_directory(tmp_path):
    assert list(blog.enumerate_posts(tmp_path / 'nope')) == []


def test_post_assets_excludes_every_post_and_recurses(tmp_path):
    folder = tmp_path / '2026-02-20'
    (folder / 'sub').mkdir(parents=True)
    (folder / 'index.md').write_text('# B\n', encoding='utf-8')
    (folder / 'another.markdown').write_text('# C\n', encoding='utf-8')
    (folder / 'diagram.png').write_bytes(b'\x89PNG')
    (folder / 'sub' / 'nested.svg').write_text('<svg/>', encoding='utf-8')

    assert [a['name'] for a in blog.post_assets(folder)] == ['diagram.png', 'sub/nested.svg']
    assert blog.post_assets(None) == []


def test_blog_config_defaults():
    cfg = config.Blog({})
    assert (cfg.enabled, cfg.dir, cfg.title, cfg.id) == (True, 'blog', 'Blog', 'blog')
    assert (cfg.navbar, cfg.drafts, cfg.tags, cfg.feed, cfg.feed_limit) == (True, False, True, True, 20)


def test_blog_config_reads_every_key():
    cfg = config.Blog(
        {
            'blog': {
                'enabled': False,
                'dir': ' posts ',
                'title': 'News',
                'id': 'news',
                'navbar': False,
                'drafts': True,
                'tags': False,
                'feed': False,
                'feed_limit': 5,
            }
        }
    )
    assert (cfg.enabled, cfg.dir, cfg.title, cfg.id) == (False, 'posts', 'News', 'news')
    assert (cfg.navbar, cfg.drafts, cfg.tags, cfg.feed, cfg.feed_limit) == (False, True, False, False, 5)


def test_blog_config_clamps_a_nonsensical_feed_limit():
    assert config.Blog({'blog': {'feed_limit': 0}}).feed_limit == 1
    assert config.Blog({'blog': {'feed_limit': -3}}).feed_limit == 1


def test_extract_excerpt_takes_the_first_paragraph():
    assert blog.extract_excerpt('First paragraph here.\n\nSecond one.\n') == 'First paragraph here.'


def test_extract_excerpt_prefers_the_more_marker():
    body = 'Lead in.\n\nStill the lead.\n\n<!--more-->\n\nBelow the fold.\n'
    assert blog.extract_excerpt(body) == 'Lead in.'


def test_extract_excerpt_skips_headings_fences_and_doxygen_commands():
    body = '# Title\n\n@tableofcontents\n\n```cpp\nint x = 1;\n```\n\nThe real opening line.\n'
    assert blog.extract_excerpt(body) == 'The real opening line.'


def test_extract_excerpt_reduces_markup_to_plain_text():
    body = 'A [link](https://example.com), some `code` and **bold** text.\n'
    assert blog.extract_excerpt(body) == 'A link, some code and bold text.'


def test_extract_excerpt_drops_images():
    assert blog.extract_excerpt('![a diagram](x.png) Text after.\n') == 'Text after.'


def test_extract_excerpt_truncates_on_a_word_boundary():
    out = blog.extract_excerpt(('word ' * 100).strip(), limit=40)
    assert out.endswith('...')
    assert len(out) <= 43
    assert 'wor...' not in out


def test_alias_stem_keeps_the_old_url_verbatim():
    # a doxygen-named page is exactly the sort of old URL an alias exists to rescue, and slugifying it
    # would put the redirect somewhere nobody ever linked to
    old = 'md_blog_22021-05-31__compilation__speed__humps__std__tuple'
    assert blog.alias_stem(old) == old
    assert blog.alias_stem(f'{old}.html') == old
    assert blog.alias_stem('  spaced.HTML  ') == 'spaced'


def test_alias_stem_rejects_anything_that_is_not_a_page_name():
    for bad in ('', '   ', '.', '..', 'a/b', '../escape', 'has space', 'quote"', 'a\\b', '.html'):
        assert blog.alias_stem(bad) == ''


def test_tag_size_buckets_span_one_to_five():
    assert blog.tag_size_bucket(1, 1, 9) == 1
    assert blog.tag_size_bucket(9, 1, 9) == 5
    assert blog.tag_size_bucket(3, 1, 9) == 2
    # a single tag has min == max, which must not divide by zero
    assert blog.tag_size_bucket(4, 4, 4) == 1


def _post(id, date, title, tags=(), excerpt=''):
    return {r'id': id, r'date': date, r'title': title, r'tags': list(tags), r'excerpt': excerpt, r'aliases': []}


def test_collect_tags_merges_spellings_case_insensitively():
    posts = [
        _post('b', datetime.date(2026, 2, 1), 'B', tags=['C++']),
        _post('a', datetime.date(2026, 1, 1), 'A', tags=['c++']),
    ]
    tags = blog.collect_tags(posts)
    assert list(tags) == ['cpp']
    # posts arrive newest first, so the display form is the most recent spelling
    assert tags['cpp']['display'] == 'C++'
    assert len(tags['cpp']['posts']) == 2


def test_collect_tags_drops_tags_that_slugify_to_nothing():
    assert blog.collect_tags([_post('a', datetime.date(2026, 1, 1), 'A', tags=['???'])]) == {}


def test_render_rss_is_well_formed_and_carries_no_build_timestamp():
    import xml.etree.ElementTree as ET

    posts = [_post('blog_2026_01_15_a', datetime.date(2026, 1, 15), 'A & B', tags=['c++'], excerpt='Sum <mary>')]
    feed = blog.render_rss('https://example.com/docs', 'Proj', 'Desc', 'An Author', posts)
    root = ET.fromstring(feed)
    item = root.find('channel/item')
    assert item is not None
    assert item.findtext('title') == 'A & B'
    assert item.findtext('link') == 'https://example.com/docs/blog_2026_01_15_a.html'
    assert item.findtext('description') == 'Sum <mary>'
    # a tag: URI, so changing a post's URL does not re-deliver it to every subscriber
    assert item.findtext('guid') == 'tag:example.com,2026-01-15:blog_2026_01_15_a'
    assert 'lastBuildDate' not in feed
    # RFC 822 via email.utils, never strftime, whose names are locale-dependent
    assert item.findtext('pubDate') == 'Thu, 15 Jan 2026 00:00:00 GMT'


def test_render_rss_omits_the_creator_when_no_author_is_configured():
    # <author> proper requires an email address, which poxy has no way to know
    posts = [_post('a', datetime.date(2026, 1, 15), 'A')]
    feed = blog.render_rss('https://example.com', 'Proj', '', '', posts)
    assert 'dc:creator' not in feed
    assert '<author>' not in feed


def test_render_rss_honours_the_limit():
    posts = [_post(f'p{i}', datetime.date(2026, 1, 1 + i), f'P{i}') for i in range(10)]
    assert blog.render_rss('https://e.com', 'P', '', '', posts, limit=3).count('<item>') == 3


def test_render_sitemap_dates_posts_only():
    import xml.etree.ElementTree as ET

    posts = [_post('blog_a', datetime.date(2026, 1, 15), 'A')]
    xml = blog.render_sitemap('https://example.com/docs', ['index.html', 'blog_a.html'], posts)
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = {u.findtext('s:loc', namespaces=ns): u.findtext('s:lastmod', namespaces=ns) for u in ET.fromstring(xml)}
    assert urls['https://example.com/docs/index.html'] is None
    assert urls['https://example.com/docs/blog_a.html'] == '2026-01-15'


def test_render_alias_stub_redirects_and_deindexes():
    stub = blog.render_alias_stub('blog_2026_01_15_a.html', 'A & B')
    assert 'url=blog_2026_01_15_a.html' in stub
    assert 'rel="canonical"' in stub
    assert 'noindex' in stub
    assert 'A &amp; B' in stub
