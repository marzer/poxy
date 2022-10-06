#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT

import re
from utils import *
from pathlib import Path
try:
	import pytomlpp as toml  # fast; based on toml++ (C++)
except:
	try:
		import tomllib as toml  # PEP 680
	except:
		import tomli as toml



def regenerate_expected_outputs():
	test_root = Path(Path(__file__).parent).resolve()

	for subdir in enumerate_directories(test_root, filter=lambda p: Path(p, r'poxy.toml').is_file()):

		html_dir = Path(subdir, r'html')
		xml_dir = Path(subdir, r'xml')
		expected_html_dir = Path(subdir, r'expected_html')
		expected_xml_dir = Path(subdir, r'expected_xml')

		delete_directory(html_dir, logger=True)
		delete_directory(xml_dir, logger=True)
		delete_directory(expected_html_dir, logger=True)
		delete_directory(expected_xml_dir, logger=True)

		# read in test config
		config = {}
		config_path = Path(subdir, r'test.toml')
		if config_path.exists():
			config = toml.loads(read_all_text_from_file(config_path, logger=True))
		output_html = config[r'html'] if r'html' in config else True
		output_xml = config[r'xml'] if r'xml' in config else False
		args = [
			r'--noassets',  #
			rf'--{"no-" if not output_html else ""}html',
			rf'--{"no-" if not output_xml else ""}xml'
		]

		# run poxy
		print(rf"Regenerating {subdir}...")
		run_poxy(subdir, *args)

		# delete garbage
		garbage = (
			r'*.xslt', r'*.xsd', r'Doxyfile.xml', r'*tagfile.xml', r'favicon*', r'search-v2.js',
			*(coerce_collection(config[r'garbage']) if r'garbage' in config else [])
		)
		garbage = (
			*(enumerate_files(html_dir, any=garbage) if output_html else []),
			*(enumerate_files(xml_dir, any=garbage) if output_xml else [])
		)
		for file in garbage:
			delete_file(file, logger=True)

		# process html files
		if not output_html:
			delete_directory(html_dir, logger=True)
		else:
			for path in enumerate_files(html_dir, any=(r'*.html')):
				text = read_all_text_from_file(path)
				text = text.replace(r'href="poxy/poxy.css"', r'href="../../../poxy/data/css/poxy.css"')
				text = text.replace(r'src="poxy/poxy.js"', r'src="../../../poxy/data/poxy.js"')
				text = text.replace(r'src="search-v2.js"', r'src="../../../poxy/data/m.css/documentation/search.js"')
				text = re.sub(r'Poxy v[0-9]+[.][0-9]+[.][0-9]+', r'Poxy v0.0.0', text)
				print(rf"Writing {path}")
				with open(path, r'w', encoding=r'utf-8', newline='\n') as f:
					f.write(text)
			html_dir.rename(expected_html_dir)

		# process xml files
		if not output_xml:
			delete_directory(xml_dir, logger=True)
		else:
			for path in enumerate_files(xml_dir, any=(r'*.xml')):
				text = read_all_text_from_file(path)
				text = re.sub(r'version="\s*[0-9]+[.][0-9]+[.][0-9]+\s*"', r'version="0.0.0"', text)
				print(rf"Writing {path}")
				with open(path, r'w', encoding=r'utf-8', newline='\n') as f:
					f.write(text)
			xml_dir.rename(expected_xml_dir)



if __name__ == '__main__':
	with ScopeTimer(r'Regenerating test outputs'):
		regenerate_expected_outputs()
