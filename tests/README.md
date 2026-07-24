# Testing pydraw

Run the complete suite from the repository root:

```sh
./venv/bin/python tests/run_tests.py
```

The runner separates the suite by purpose:

- `headless`: value objects and deterministic timing logic; no Tk window.
- `gui`: API contracts exercised against a real Tk canvas.
- `e2e`: complete user workflows from Tk events through pydraw state and
  rendered canvas output.

Pass a category or module name to run a smaller set:

```sh
./venv/bin/python tests/run_tests.py headless
./venv/bin/python tests/run_tests.py gui
./venv/bin/python tests/run_tests.py e2e
./venv/bin/python tests/run_tests.py line text -v
```

## Tk process rule

Always run Tk tests in the foreground. Never append `&`, detach them, or launch
them through a background worker. Each GUI module runs synchronously in its own
foreground subprocess because Tk keeps process-global root state. A plain
`python -m unittest discover` puts multiple Screen-owning modules in one
interpreter and is therefore unsupported.

The explicit module manifest in `run_tests.py` is the source of truth for
automated tests. Manual demos and scratch programs are not test coverage and
must not be added to the manifest.
