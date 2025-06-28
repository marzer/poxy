# poxy

Documentation generator for C++ based on Doxygen and [mosra/m.css](https://mcss.mosra.cz/).

[![Sponsor](https://img.shields.io/static/v1?label=sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86&style=flat-square)][sponsor]
[![Gitter](https://badges.gitter.im/marzer/poxy.svg)][gitter]

-   [Overview](#overview)
-   [Example](#example)
-   [Installation](#installation)
-   [Usage](#usage)
-   [Config file options](#config-file-options)
-   [Migrating from Doxygen](#migrating-from-doxygen)
-   [Why the name "Poxy"?](#why-the-name-poxy)
-   [License and Attribution](#license-and-attribution)

<br><br>

## Overview

[mosra/m.css] is a Doxygen-based documentation generator that significantly improves on Doxygen's default output
by controlling some of Doxygen's more unruly options, supplying it's own slick HTML+CSS generation and adding
a fantastic live search feature. **Poxy** builds upon both by:

-   Moving the configuration out into a TOML file
-   Preprocessing the Doxygen XML to fix a bunch of Doxygen _~~bugs~~_ quirks
-   Postprocessing the generated HTML to improve syntax highlighting and add a few other improvements
-   Allowing source, image and example directories to be recursive or shallow on a per-directory basis
-   Automatically defining C++ language feature macros based on your project's target C++ version
-   Automatically integrating the cppreference.com doxygen tagfile
-   Providing a number of additional built-in doxygen `@alias` commands
-   Giving more control over the HTML inline using square-bracket `[tags][/tags]`
-   Adding a switchable light theme
-   Adding support for C++20 concepts
-   Self-hosting fonts to reduce external HTTP requests
-   Inlining SVGs so they can take advantage of [`currentColor`]
-   Quite a bit more!

<br><br>

## Example

The homepage + documentation for [toml++] is built using poxy:

-   homepage: [marzer.github.io/tomlplusplus](https://marzer.github.io/tomlplusplus/)
-   config file: [`poxy.toml`](https://github.com/marzer/tomlplusplus/blob/master/docs/poxy.toml)

<br><br>

## Installation

### Prerequisites:

-   Python 3.7+
-   Doxygen 1.8.20+ (must be visible on system path)
-   Linux only: `sudo apt install dvisvgm`

### Then:

```
pip install poxy
```

<br><br>

## Usage

Poxy is a command-line application.

```
usage: poxy [-h] [-v] [--html | --no-html] [--ppinclude <regex>] [--ppexclude <regex>]
            [--theme {light,dark,custom}] [--threads N] [--version] [--xml | --no-xml]
            [--werror | --no-werror] [--bug-report] [--git-tags]
            [--squash-patches | --no-squash-patches] [--min-version <version>]
            [config]

  _ __   _____  ___   _
 | '_ \ / _ \ \/ / | | |
 | |_) | (_) >  <| |_| |
 | .__/ \___/_/\_\\__, |
 | |               __/ |
 |_|              |___/  v0.17.0 - github.com/marzer/poxy

Generate fancy C++ documentation.

positional arguments:
  config                path to poxy.toml or a directory containing it (default: .)

options:
  -h, --help            show this help message and exit
  -v, --verbose         enable very noisy diagnostic output
  --html, --no-html     specify whether HTML output is required
  --ppinclude <regex>   pattern matching HTML file names to post-process (default: all)
  --ppexclude <regex>   pattern matching HTML file names to exclude from post-processing (default: None)
  --theme {light,dark,custom}
                        sets the default visual theme (default: read from config)
  --threads N           set the number of threads to use (default: automatic)
  --version             print the version and exit
  --xml, --no-xml       specify whether XML output is required
  --werror, --no-werror
                        treat warnings as errors (default: read from config)
  --bug-report          captures all output in a zip file for easier bug reporting.
  --git-tags            add git-tag-based semver version switcher to the generated HTML
  --squash-patches, --no-squash-patches
                        when using --git-tags and two version tags differ by a patch number,
                        generate docs for the highest one only (default: True)
  --min-version <version>
                        sets the minimum version number to emit when using --git-tags,
                        or a negative integer to mean "the last N versions". (default: None)
```

The basic three-step to using Poxy is similar to Doxygen:

1. Create your `poxy.toml` (Poxy's answer to the `Doxyfile`)
2. Invoke Poxy on it: `poxy path/to/poxy.toml` (or simply `poxy` if the cwd contains the config file)
3. See your HTML documentation `<cwd>/html`

<br><br>

## Config file options

For a self-contained `poxy.toml` example to copy and paste from,
see [the one used by toml++](https://github.com/marzer/tomlplusplus/blob/master/docs/poxy.toml).

For a full list of options, with full descriptions, schemas and usage examples, see the [Configuration options] wiki page.

<br><br>

## Migrating from Doxygen

Generally the relevant `Doxyfile` options will have a corresponding `poxy.toml` option
(or be replaced by something more specific) so migration is largely a transcription and box-ticking exercise,
though there are a few gotchas:

#### **⚠&#xFE0F; The majority of Doxygen's options are controlled by Poxy**

Many of Doxygen's various knobs and switches are manually overridden by Poxy, and are not configurable.
**This is intentional!** Doxygen tends to break in hilarious and fantastic ways from one release to the next;
reducing it to a very 'locked-down' back-end minimizes the damage future regressions can do, allowing me to
keep most debugging python-side.

If there is some Doxygen feature you would like exposed in Poxy, please create a [feature request].

#### **⚠&#xFE0F; All relative input paths are relative to the config file, _not_ CWD**

This is in contrast to Doxygen, which has all paths be relative to the Doxygen process' current working directory
regardless of where the Doxyfile was. I've always personally found that to be nothing but a source of error,
so Poxy does away with it.

#### **⚠&#xFE0F; Output is always emitted to CWD**

Poxy always emits HTML to `<cwd>/html` and XML to `<cwd>/xml`. You cannot use your config file to specify where any
output will be placed - use your command-line environment for this purpose instead by changing the CWD.
This is to eliminate nasty surprises brought on by goofy config file decisions and help with portability.

#### **⚠&#xFE0F; Poxy config files are self-contained**

There is no equivalent to Doxygen's `@INCLUDE`. If your project is structured in such a way that a
multi-level Doxyfile hierarchy is necessary, Poxy isn't for you.

<br><br>

## Why the name "Poxy"?

Originally it was simply called "dox", but there's already a C++ documentation project with that name,
so I smashed "python" and "dox" together and this is what I came up with.

Also "poxy" can be slang for cheap, inferior, poor quality, etc., which I thought was funny.

<br><br>

## License and Attribution

This project is published under the terms of the [MIT license](https://github.com/marzer/poxy/blob/main/LICENSE.txt).

Significant credit must go to Vladimír Vondruš ([mosra]) and his amazing [m.css] Doxygen theme.
Poxy bundles a fork of m.css, used per the [MIT/Expat license](https://github.com/marzer/poxy/blob/main/poxy/data/m.css/COPYING)
(which can also be found in the installed python package).

[m.css]: https://mcss.mosra.cz/documentation/doxygen/
[mosra]: https://github.com/mosra
[mosra/m.css]: https://mcss.mosra.cz/documentation/doxygen/
[toml++]: https://marzer.github.io/tomlplusplus/
[c++ feature test macros]: https://en.cppreference.com/w/cpp/feature_test
[configuration options]: https://github.com/marzer/poxy/wiki/Configuration-options
[feature request]: https://github.com/marzer/poxy/issues/new
[`currentcolor`]: https://gomakethings.com/currentcolor-and-svgs
[gitter]: https://gitter.im/marzer/poxy
[sponsor]: https://github.com/sponsors/marzer
