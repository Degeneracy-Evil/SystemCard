# SystemCard

SystemCard is a Python 3.12+ package with a thin C++20 binding to Sysal.

## Environment

```bash
uv sync --locked --dev
git config core.hooksPath .githooks
```

## Key conventions

- Use uv for Python, virtual environments, dependencies, and `uv.lock`; do not add requirements files.
- Keep Python 3.12 as the development and minimum supported version; Ruff and mypy target 3.12.
- Use `--locked` for development checks and runs; update dependencies and the lock explicitly.
- Ruff owns linting, formatting, and import sorting with a 120-character line width.
- mypy runs in strict mode; new Python code needs complete, meaningful type annotations.
- pytest is the only test framework; retain branch coverage reports without a hard coverage gate.
- `uv run --locked python scripts/check.py` only validates and must not modify tracked files or the index.
- Explicit fixes: `uv run --locked ruff check --fix .` and `uv run --locked ruff format .`.
- pre-commit validates staged whitespace and Python/pyi formatting without modifying or staging files.
- Keep the pybind11 layer thin and use only Sysal's public API.
- Sysal comes from the versioned, SHA-256-pinned GitHub Release package configured in CMake.
- Preserve scikit-build-core/CMake packaging, native ABI settings, and manylinux wheel validation.
- Keep LF line endings and do not maintain a manual development log.
- Quality CI runs on the minimum supported Python; wheel smoke tests cover published Python versions.

## Verification

After changing code or project configuration, run:

```bash
uv run --locked python scripts/check.py
uv build
uv run --locked systemcard --section system --no-color
```

The quality gate checks Ruff format, Ruff lint, mypy strict, and pytest. Formatting and repair are explicit operations.
