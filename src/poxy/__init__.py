#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

from .main import main, main_blog_post
from .version import VERSION, VERSION_STRING

__all__ = ['main', 'main_blog_post', 'VERSION', 'VERSION_STRING']

__version__ = VERSION_STRING

if __name__ == '__main__':
    main()
