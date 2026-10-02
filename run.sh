#!/usr/bin/env bash
# Run a published version or a package supplied via SYSTEMCARD_SPEC.
set -euo pipefail

if [[ -n "${SYSTEMCARD_SPEC:-}" && -n "${SYSTEMCARD_VERSION:-}" ]]; then
    echo "Set either SYSTEMCARD_SPEC or SYSTEMCARD_VERSION, not both." >&2
    exit 2
fi
spec="${SYSTEMCARD_SPEC:-systemcard}"
runner="${SYSTEMCARD_RUNNER:-auto}"
case "$runner" in auto|uvx|pipx|venv) ;; *) echo "SYSTEMCARD_RUNNER must be auto, uvx, pipx, or venv." >&2; exit 2 ;; esac
if [[ -n "${SYSTEMCARD_VERSION:-}" ]]; then
    spec="systemcard==${SYSTEMCARD_VERSION}"
fi

if [[ "$runner" = auto || "$runner" = uvx ]] && command -v uvx >/dev/null 2>&1; then
    exec uvx --from "$spec" systemcard "$@"
fi
if [[ "$runner" = auto || "$runner" = pipx ]] && command -v pipx >/dev/null 2>&1; then
    exec pipx run --spec "$spec" systemcard "$@"
fi
if [[ "$runner" = uvx || "$runner" = pipx ]]; then
    echo "Requested runner is not installed: $runner" >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "SystemCard needs Python 3.6.8+ or uvx/pipx." >&2
    exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 6, 8) else "SystemCard requires Python 3.6.8+")'
environment="$(mktemp -d "${TMPDIR:-/tmp}/systemcard.XXXXXXXX")"
trap 'rm -rf -- "$environment"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
python3 -m venv "$environment"
pip_spec="pip"
case "$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')" in
    3.6) pip_spec="pip==21.3.1" ;;
    3.7) pip_spec="pip<24.1" ;;
esac
"$environment/bin/python" -m pip install --upgrade "$pip_spec" >&2
"$environment/bin/python" -m pip install "$spec" >&2
"$environment/bin/systemcard" "$@"
