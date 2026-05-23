#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


def pytest_addoption(parser):
    parser.addoption(
        '--regenerate',
        action='store_true',
        default=False,
        help='bless the current poxy output as the expected snapshot instead of comparing against it',
    )


@pytest.fixture(scope='session')
def regenerate(request) -> bool:
    return bool(request.config.getoption('--regenerate'))
