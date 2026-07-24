#!/usr/bin/env python3
"""Run the pydraw test suite, one module at a time in the foreground.

Tk owns process-global state, so GUI modules must not share an interpreter.
They must also never be started as background or detached processes: Tk needs
the foreground window-system session. ``subprocess.run`` intentionally blocks
until each module exits before the next module starts.

The explicit manifest is deliberate. Scratch programs placed under ``tests/``
must never become part of CI merely because their filename happens to match a
glob.

Usage:
    python tests/run_tests.py                 # all tests
    python tests/run_tests.py headless        # no Tk window
    python tests/run_tests.py gui             # GUI API/integration tests
    python tests/run_tests.py e2e             # complete user workflows
    python tests/run_tests.py line text -v    # selected modules, verbose
"""

import os
import sys
import subprocess

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)

SUITES = {
    'headless': (
        'color_test',
        'location_test',
        'sleep_test',
    ),
    'gui': (
        'algorithms_test',
        'compound_test',
        'image_test',
        'input_test',
        'line_test',
        'objects_test',
        'pen_test',
        'scene_test',
        'screen_test',
        'text_test',
    ),
    'e2e': (
        'workflow_e2e_test',
    ),
}

# `python -m unittest` returns this when a module contains no tests (Py 3.12+).
NO_TESTS_EXIT = 5


def discover():
    """Return each declared module once, in suite order."""
    return list(dict.fromkeys(
        module
        for suite in SUITES.values()
        for module in suite
    ))


def select(filters):
    """Resolve category names and short module names."""
    if not filters or filters == ['all']:
        return discover()

    selected = []
    unknown = []
    available = set(discover())
    for value in filters:
        if value in SUITES:
            selected.extend(SUITES[value])
            continue

        module = value if value.endswith('_test') else value + '_test'
        if module not in available and value.endswith('_e2e'):
            module += '_test'
        if module in available:
            selected.append(module)
        else:
            unknown.append(value)

    if unknown:
        choices = ', '.join((*SUITES, *discover()))
        raise ValueError(
            f'Unknown suite/module: {", ".join(unknown)}\n'
            f'Available: {choices}'
        )
    return list(dict.fromkeys(selected))


def describe_returncode(returncode):
    if returncode < 0:
        return f'signal {-returncode}'
    if returncode == NO_TESTS_EXIT:
        return 'no tests collected'
    return f'exit {returncode}'


def main(argv):
    flags = [a for a in argv if a.startswith('-')]
    filters = [a for a in argv if not a.startswith('-')]

    try:
        modules = select(filters)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    env = dict(os.environ)
    env['PYTHONPATH'] = REPO_ROOT + os.pathsep + env.get('PYTHONPATH', '')
    env['PYTHONUNBUFFERED'] = '1'

    results = {}
    for mod in modules:
        print(f'\n===== {mod} =====', flush=True)
        # Foreground only. Do not replace this with Popen or shell backgrounding.
        proc = subprocess.run(
            [sys.executable, '-m', 'unittest', f'tests.{mod}'] + flags,
            cwd=REPO_ROOT, env=env)
        results[mod] = proc.returncode

    passed = [m for m, rc in results.items() if rc == 0]
    failed = [m for m, rc in results.items() if rc != 0]

    print('\n' + '=' * 60)
    print(f'SUMMARY: {len(passed)}/{len(results)} suites passed')
    if failed:
        for module in failed:
            print(f'FAILED:  {module} ({describe_returncode(results[module])})')

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
