# Contributing to Poxy

Firstly: thanks! Any help is greatly appreciated.

For most situations the easiest way for you to contribute is to simply let me know what's going on:

-   Reporting issues or requesting features: [Issues]
-   Chat: [Gitter]

If you'd like to contribute more directly via a pull request, see below.

<br /><br />

## Pull Requests

### Getting started

A prerequisite of working on Poxy with the intention of making a pull request is to have it installed as 'editable' from a clone of the repository:

```sh
git clone <your poxy fork>
cd poxy
pip install --upgrade -r requirements.txt
pip install -e .
```

Once that's done, you may need to use one (or all) of the following hidden developer-only subcommands as you iterate on your changes:

<br /><br />

### Updating m.css

If there are new upstream changes in m.css that you wish to incorporate into the poxy repository:

```sh
poxy --update-mcss <path/to/mcss/root>
```

#### **ℹ&#xFE0F; Notes:**

-   Development iteration on Poxy tends to happen more frequently than it does on the upstream [mosra/m.css] (because the maintainer of that project is very busy), so the one bundled in Poxy is based on my own fork ([marzer/m.css]). I intermittently make pull requests of my own to contribute back, though!

<br /><br />

### Updating the built-in fonts

Poxy pre-caches the Google Fonts used in documentation builds so that end-users do not need to make external HTTP requests for these. These rarely change, but if you need to update them:

```sh
poxy --update-fonts
```

#### **ℹ&#xFE0F; Notes:**

-   `--update-fonts` is implied by `--update-mcss`.

<br /><br />

### Updating the built-in CSS stylesheets

If you've made changes to any of the `.css` files in [data/css]:

```sh
poxy --update-styles
```

This will regenerate the amalgamated `poxy.css` that is shipped with documentation builds.

#### **ℹ&#xFE0F; Notes:**

-   `--update-styles` is implied by `--update-mcss` and `--update-fonts`.
-   While iterating on styles you **⚠&#xFE0F;do not⚠&#xFE0F;** need to fully regenerate the styles + rebuild some documentation to see your changes! That would be monumentally annoying. Instead you should use `theme_test/index.html`, which uses the original version of `poxy.css` (the one that uses `@import`), not the amalgamated one.

<br /><br />

### Updating the Emoji database

Poxy allows users to inject emoji into their documents by name using `[emoji <name>]`, where `<name>` is derived from GitHub's Emoji API (e.g. `[emoji tada]` is equivalent to `:tada:`). This data is stored in the repository in an internal 'emoji database' file which needs needs to be regenerated occasionally (e.g. when new versions of Unicode are published):

```sh
poxy --update-emoji
```

<br /><br />

### Updating the test reference outputs

Each of the 'projects' in `/tests/` has a set of reference outputs in `expected_html` and/or `expected_xml`. These are the 'blessed' versions of whatever the test is assessing, and must be regenerated when changes are made that impact the generated HTML or XML:

```sh
poxy --update-tests
```

<br /><br />

### Developer subcommand usage

#### Combining subcommands

You may need to use a combination of the subcommands together during the same iteration cycle; you can combine them together on the same invocation, e.g.:

```sh
poxy --update-tests --update-styles
```

The order in which you combine them does not matter - they are internally executed such that if subcommand `A` impacts the inputs to subcommand `B`, `A` will occur before `B`.

#### Mixing subcommands with regular Poxy invocations

Using any of the subcommands will cause Poxy to execute their actions and exit immediately, without performing a normal Poxy documentation run. If your iteration needs are such that you need to do both, you can simply combine them on the command line:

```sh
poxy --update-styles && poxy
```

[issues]: https://github.com/marzer/poxy/issues
[gitter]: https://gitter.im/marzer/poxy
[mosra/m.css]: https://github.com/mosra/m.css
[marzer/m.css]: https://github.com/marzer/m.css
[data/css]: https://github.com/marzer/poxy/tree/main/poxy/data/css
