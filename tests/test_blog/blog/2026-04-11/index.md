+++
title = "More Media"
+++

A second post carrying its own `diagram.png`. Doxygen resolves images by basename, so before poxy staged
these per-post the two files collided and only one of them reached the output.

![a red square](diagram.png)

An image already inside a link keeps its own destination, and gets no lightbox wrapper:

[![a linked red square](diagram.png)](https://example.com/)

An svg is injected into the document instead, so it gets no wrapper either:

![a green circle](circle.svg)
