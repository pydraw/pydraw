#!/usr/bin/env python3
"""
Run the pydraw unittest suite.

Each test module is executed in its OWN subprocess. This is required: every
pydraw test creates a tkinter Screen, and tkinter keeps a single global root.
Running several Screen-creating modules in one interpreter - as a plain
`python -m unittest discover` does - tears that root down mid-run and produces
spurious "application has been destroyed" failures. Isolating each module in a
fresh subprocess sidesteps the problem entirely.

The suite runs against the pydraw SOURCE in this repo: the repo root is placed
at the front of PYTHONPATH so an installed site-package copy never shadows it.

Usage:
    python tests/run_tests.py                # run the whole suite
    python tests/run_tests.py line text      # run only line_test.py / text_test.py
    python tests/run_tests.py -v             # verbose (flags pass through to unittest)
"""

import os
import sys
import glob
import subprocess

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)

# Non-suite scratch/demo files in tests/ that are not meant to run in CI.
SKIP = set()

# `python -m unittest` returns this when a module contains no tests (Py 3.12+).
NO_TESTS_EXIT = 5


def discover():
    """Return the sorted names of runnable *_test.py modules (minus SKIP)."""
    modules = []
    for path in sorted(glob.glob(os.path.join(TESTS_DIR, '*_test.py'))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name not in SKIP:
            modules.append(name)
    return modules


def main(argv):
    flags = [a for a in argv if a.startswith('-')]
    filters = [a for a in argv if not a.startswith('-')]

    modules = discover()

    if filters:
        # Accept either 'line' or 'line_test'.
        wanted = {f if f.endswith('_test') else f + '_test' for f in filters}
        modules = [m for m in modules if m in wanted]
        if not modules:
            print(f'No matching test modules for: {" ".join(filters)}')
            return 1

    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT + os.pathsep + env.get('PYTHONPATH', '')

    results = {}
    for mod in modules:
        print(f'\n===== {mod} =====', flush=True)
        proc = subprocess.run(
            [sys.executable, '-m', 'unittest', f'tests.{mod}'] + flags,
            cwd=REPO_ROOT, env=env)
        results[mod] = proc.returncode

    passed = [m for m, rc in results.items() if rc == 0]
    empty = [m for m, rc in results.items() if rc == NO_TESTS_EXIT]
    failed = [m for m, rc in results.items() if rc not in (0, NO_TESTS_EXIT)]

    print('\n' + '=' * 60)
    print(f'SUMMARY: {len(passed)}/{len(passed) + len(failed)} suites passed')
    if failed:
        print('FAILED:  ' + ', '.join(failed))
    if empty:
        print('no tests: ' + ', '.join(empty))
    if SKIP:
        print('skipped (non-suite scratch files): ' + ', '.join(sorted(SKIP)))

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
