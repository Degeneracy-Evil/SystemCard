# SystemCard

SystemCard is a terminal system information card powered by [Sysal](https://github.com/Degeneracy-Evil/sysal).
It presents machine and current-process-visible resources in a concise Rich terminal interface.

## Local development

Install the project and development toolchain with uv:

```bash
uv sync --locked --dev
uv run --locked systemcard
```

The local build requires CMake, a C++20 compiler, Python 3.12 or newer, and network access for the first build. CMake downloads the pinned [Sysal v0.0.8 release package](https://github.com/Degeneracy-Evil/sysal/releases/tag/v0.0.8), verifies its SHA-256 digest, and statically links `libsysal.a` into the native extension.

Run the complete project checks with:

```bash
uv run --locked python scripts/check.py
uv run --locked systemcard --section system --no-color
```

The check entry point follows the [base-py](https://github.com/Degeneracy-Evil/base-py) conventions: Ruff format validation and linting, mypy strict mode, and pytest with branch coverage reports. There is no hard coverage threshold; checks do not modify tracked files or the index.

Enable the staged snapshot hook explicitly:

```bash
git config core.hooksPath .githooks
```

The hook checks whitespace and Python formatting without changing or staging files. Apply fixes explicitly with
`uv run --locked ruff check --fix .` and `uv run --locked ruff format .`.
Dependency changes update `uv.lock` explicitly; normal development and CI use locked environments.
Use `systemcard` or `uv run --locked python -m systemcard` as the entry point.

## Compatibility

Release wheels target Linux x86_64 systems with glibc 2.17 or newer (CentOS 7 / RHEL 7 and newer compatible distributions). The wheel workflow builds CPython 3.12, 3.13, and 3.14 artifacts in the manylinux2014 image, repairs them with auditwheel, and runs a real collection smoke test against each installed wheel.
