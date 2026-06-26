#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Re-blesses the golden snapshot outputs. Kept as a thin wrapper around `pytest --regenerate` so the
regeneration path and the comparison path share exactly one implementation (tests/test_snapshots.py).
This is what `poxy --update-tests` invokes.
"""

import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    cmd = [
        sys.executable,
        '-m',
        'pytest',
        str(Path(__file__).parent / 'test_snapshots.py'),
        '--regenerate',
        '-q',
        *sys.argv[1:],
    ]
    sys.exit(subprocess.run(cmd).returncode)
