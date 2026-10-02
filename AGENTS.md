# SystemCard

SystemCard supports Python 3.6.8+ at runtime, including the CentOS 7 system interpreter, with a thin C++20 binding to Sysal. Development tools run on Python 3.12.

## Environment

```bash
uv sync --locked --dev
git config core.hooksPath .githooks
```

## Key conventions

- Use uv for Python, virtual environments, dependencies, and `uv.lock`; do not add requirements files.
- Keep Python 3.12 for development tools. Runtime modules must parse and run on Python 3.6.8; use typing aliases and no postponed annotations.
- Keep modern scikit-build-core packaging; Python 3.6/3.7 uses the compatibility backend with setuptools and the same CMake target.
- Runtime dependency markers select Rich 12 and the dataclasses backport for old interpreters.
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
- Quality CI runs on development Python. Wheel tests cover Python 3.6 through 3.14; the CentOS 7 job verifies installation and collection using its system Python 3.6.8.

## Verification

After changing code or project configuration, run:

```bash
uv run --locked python scripts/check.py
uv build
uv run --locked systemcard --section system --no-color
```

The quality gate checks Ruff format, Ruff lint, mypy strict, and pytest. Formatting and repair are explicit operations.

## 临时文件

开发过程中主动生成的临时构建、日志、采集样本和预览统一放在本项目的 `tmp/` 下，
不写入系统 `/tmp`。`tmp/` 不提交到 Git；工具支持指定临时目录时使用项目 `tmp/`。
