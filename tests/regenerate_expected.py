#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

from utils import *
from pathlib import Path



def regenerate_expected_outputs():
	test_root = Path(Path(__file__).parent).resolve()

	for subdir in enumerate_directories(test_root, filter = lambda p: Path(p, 'poxy.toml').is_file()):
		delete_directory(Path(subdir, 'html'), logger=True)
		delete_directory(Path(subdir, 'xml'), logger=True)
		delete_directory(Path(subdir, 'expected_html'), logger=True)
		delete_directory(Path(subdir, 'expected_xml'), logger=True)

		print(rf"Regenerating {subdir}...")
		run_poxy(subdir, '--nocleanup')
		Path(subdir, 'html').rename(Path(subdir, 'expected_html'))
		Path(subdir, 'xml').rename(Path(subdir, 'expected_xml'))



if __name__ == '__main__':
	with ScopeTimer('Regenerating test outputs'):
		regenerate_expected_outputs()
