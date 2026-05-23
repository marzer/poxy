#!/usr/bin/env python3
# This file is a part of marzer/poxy and is subject to the the terms of the MIT license.
# Copyright (c) Mark Gillard <mark.gillard@outlook.com.au>
# See https://github.com/marzer/poxy/blob/master/LICENSE for the full license text.
# SPDX-License-Identifier: MIT
"""
Golden-output (convergence) tests.

Each tests/test_* project is built, its output sanitized, then compared file-by-file against the
canonical expected_html / expected_xml trees. Run `pytest --regenerate` to re-bless the goldens
(equivalent to `poxy --update-tests`).

The golden is poxy's *desired, version-independent* output. poxy exists to normalize away doxygen's
version-to-version differences, so CI runs these against the full doxygen matrix and expects every
version to reproduce the same golden. A divergence is a normalization gap in poxy, not a test to relax.

Requires doxygen on PATH; skipped automatically when it isn't found.
"""

import difflib

import pytest
from utils import doxygen_available, enumerate_test_projects, produce_outputs

pytestmark = pytest.mark.skipif(not doxygen_available(), reason='doxygen not found on PATH')

_PROJECTS = list(enumerate_test_projects())


def _bless(expected_dir, files: dict):
    expected_dir.mkdir(parents=True, exist_ok=True)
    for f in expected_dir.iterdir():
        if f.is_file():
            f.unlink()
    for name, text in files.items():
        with open(expected_dir / name, 'w', encoding='utf-8', newline='\n') as out:
            out.write(text)


def _diff(name, expected: str, actual: str) -> str:
    return '\n'.join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=f'expected/{name}',
            tofile=f'actual/{name}',
            lineterm='',
        )
    )


@pytest.fixture(scope='module')
def _outputs(request, tmp_path_factory):
    """builds every project once for the module and caches {project_name: {kind: {file: text}}}."""
    cache = {}
    for project_dir, config in _PROJECTS:
        work = tmp_path_factory.mktemp(project_dir.name)
        cache[project_dir.name] = produce_outputs(project_dir, config, work)
    return cache


@pytest.mark.parametrize('project_dir,config', _PROJECTS, ids=[p.name for p, _ in _PROJECTS] or ['<none>'])
@pytest.mark.parametrize('kind', ('html', 'xml'))
def test_snapshot(project_dir, config, kind, regenerate, _outputs):
    produced = _outputs[project_dir.name].get(kind)
    if produced is None:
        pytest.skip(f'{project_dir.name} does not produce {kind}')

    expected_dir = project_dir / f'expected_{kind}'

    if regenerate:
        _bless(expected_dir, produced)
        return

    assert expected_dir.is_dir(), f'missing {expected_dir} (run pytest --regenerate to create it)'
    expected = {f.name: f.read_text(encoding='utf-8') for f in expected_dir.iterdir() if f.is_file()}

    missing = sorted(set(expected) - set(produced))
    unexpected = sorted(set(produced) - set(expected))
    assert not missing, f'{kind}: expected files not produced: {missing}'
    assert not unexpected, f'{kind}: unexpected files produced: {unexpected}'

    diffs = [
        _diff(name, expected[name], produced[name]) for name in sorted(expected) if expected[name] != produced[name]
    ]
    assert not diffs, '\n\n'.join(diffs)
