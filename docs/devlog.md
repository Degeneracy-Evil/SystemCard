# Development log

### 2026-07-16 Initial SystemCard foundation

- **Change type**: docs / build / src
- **Files**: `DEVELOPMENT.md`, `plan.md`, `.gitmodules`, `CMakeLists.txt`, `pyproject.toml`, `README.md`, `main.py`, `bindings/`, `src/systemcard/`, `docs/`, `.gitignore`
- **Changes**: Updated the Linux compatibility target to glibc 2.17+; recorded the development plan; added a pinned Sysal submodule; established the CMake/pybind11 native adapter, Python CLI skeleton, rendering pipeline, data-contract documentation, and local development configuration.
- **Reason**: Create a low-coupling, locally runnable vertical slice that relies only on Sysal's public API.
- **Verification**: Used `uv pip install rich pybind11 scikit-build-core pytest` and `uv pip install -e .` in the project virtual environment with proxy variables temporarily cleared. Verified `uv run --no-sync systemcard --compact --no-color`, `uv run --no-sync systemcard --no-color`, and `uv run --no-sync python -m systemcard --version` against a real Sysal collection. Unit tests are recorded below.

### 2026-07-16 Basic presentation tests

- **Change type**: test
- **Files**: `tests/test_formatters.py`, `tests/test_model.py`, `tests/test_cli.py`
- **Changes**: Added deterministic tests for formatting, model construction, compact output selection, and CLI success/failure handling.
- **Reason**: Keep presentation behavior testable without coupling most tests to host hardware or Sysal internals.
- **Verification**: `uv run --no-sync pytest`.

### 2026-08-02 Upgrade Sysal to v0.0.6

- **Change type**: build / deps
- **Files**: `third_party/sysal`, `vendor/sysal/lib/libsysal.so`
- **Changes**: Advanced the pinned Sysal submodule from `138d196` (v0.0.4-era) to release tag `v0.0.6` (`2f94a7c`), and rebuilt the vendored `libsysal.so` from that source via `xmake build sysal_shared`. Restored `uv pip install -e .` so the native extension links the freshly built library.
- **Reason**: Catch up with upstream bug fixes between v0.0.4 and v0.0.6 (notably a container environment variable misclassification) while verifying no public-API breakage. Reviewed the diff of all 20 public headers between the pinned and latest revision: changes are exclusively clang-format reformatting, with `Collect`, `System::collect()`, `to_json()`/`SerializationOptions`, and the JSON schema unchanged, so this was a source-compatible upgrade requiring no binding or data-contract edits.
- **Verification**: `uv run --no-sync systemcard --no-color` performed a real collection against the rebuilt v0.0.6 library and rendered normally; `uv run --no-sync pytest` passed (6 tests). Confirmed the installed `systemcard/libsysal.so` in the venv is the freshly built artifact.

### 2026-07-16 Use prebuilt Sysal library

- **Change type**: build / docs
- **Files**: `CMakeLists.txt`, `README.md`, `plan.md`, `vendor/sysal/lib/libsysal.so`
- **Changes**: Removed xmake invocation and Sysal static-library compilation from the SystemCard CMake build. The native extension now links the prebuilt Sysal library vendored in this repository and installs it beside the extension with an `$ORIGIN` runtime path.
- **Reason**: SystemCard is a consumer of Sysal and must not take responsibility for building the library or depending on an absolute path outside this repository.
- **Verification**: Reinstalled with `uv pip install -e .` after temporarily clearing proxy variables. Confirmed `uv run --no-sync systemcard --compact --no-color` collects and renders real system data through the vendored shared library; `uv run --no-sync pytest` passed (6 tests). `uv build --wheel` produced a wheel containing both `systemcard/_native…so` and `systemcard/libsysal.so`, with the extension installation RPATH set to `$ORIGIN`.
