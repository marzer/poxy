#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE.txt for the full license text.
# SPDX-License-Identifier: MIT

# set up based on this: https://thucnc.medium.com/how-to-publish-your-own-python-package-to-pypi-4318868210f9
# windows:
# py setup.py sdist bdist_wheel && twine upload dist/* && rmdir /S /Q dist

import sys
from setuptools import setup, find_packages
from pathlib import Path

def enum_subdirs(root):
	root = Path(root).resolve()
	assert root.is_dir()
	subdirs = []
	for p in root.iterdir():
		if p.is_dir():
			subdirs.append(p)
			subdirs = subdirs + enum_subdirs(p)
	return subdirs

package_dir = str(Path(Path(__file__).parent, r'poxy').resolve())
data_subdirs = enum_subdirs(Path(package_dir, r'data'))
data_subdirs = [str(d)[len(package_dir):].strip('\\/').replace('\\', '/') for d in data_subdirs]
for excl in (r'/doc/', r'/test/', r'/test_doxygen', r'/test_python', r'/pelican-theme', r'__pycache__'):
	data_subdirs = [d for d in data_subdirs if d.find(excl) == -1]
data_subdirs = [rf'{d}/*' for d in data_subdirs]

README = ''
if Path('README.md').exists():
	with open('README.md', encoding='utf-8') as file:
		README = file.read()

HISTORY = ''
if Path('HISTORY.md').exists():
	with open('HISTORY.md', encoding='utf-8') as file:
		HISTORY = file.read()

setup_args = dict(
	name=r'poxy',
	version=r'0.1.2',
	description=r'Documentation generator for C++.',
	long_description_content_type=r'text/markdown',
	long_description=f'{README}\n\n{HISTORY}'.strip(),
	license=r'MIT',
	packages=find_packages(),
	author=r'Mark Gillard',
	author_email=r'mark.gillard@outlook.com.au',
	keywords=[
		r'c++',
		r'doxygen',
		r'documentation'
	 ],
	url=r'https://github.com/marzer/poxy',
	download_url=r'https://pypi.org/project/poxy/',
	classifiers=[
		r'Development Status :: 3 - Alpha',
		r'License :: OSI Approved :: MIT License',
		r'Programming Language :: C++',
		r'Topic :: Documentation',
		r'Topic :: Software Development :: Documentation',
		r'Topic :: Utilities'
	],
	project_urls={
		r'Source': r'https://github.com/marzer/poxy',
		r'Tracker': r'https://github.com/marzer/poxy/issues'
	},
	python_requires=r'>=3',
	package_data={
		r'poxy' : [ r'data/*', *data_subdirs ]
	},
	exclude_package_data={
		r'poxy': [
			r'.git*',
			r'.istanbul.yaml',
			r'*.rst',
			r'*.pyc',
			r'data/mcss/doc/*',
			r'data/mcss/documentation/test/*',
			r'data/mcss/documentation/test_doxygen/*',
			r'data/mcss/documentation/test_python/*',
			r'data/mcss/package/*',
		]
	},
	entry_points = {
		r'console_scripts' : [ r'poxy = poxy.__main__:main' ]
	}
)

install_requires = None
with open('requirements.txt', encoding='utf-8') as file:
	install_requires = file.read().strip().split()

if __name__ == '__main__':
	setup(**setup_args, install_requires=install_requires)
