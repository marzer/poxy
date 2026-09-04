# Markdown Pages

A project whose front page comes from a markdown file.

- [Overview](#overview)
- [Usage](#usage)

## Overview

The main page stays markdown, so it exercises the input filter rather than the page compiler.

## Usage

```cpp
widget w{ 42 };
w.reset();
```

Entities such as &amp; and &#x2764; must survive the round trip.
