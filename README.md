# SystemCard

SystemCard is a terminal system information card powered by [Sysal](https://github.com/Degeneracy-Evil/sysal).
It presents machine and current-process-visible resources in a concise Rich terminal interface.

## Installation status

The first PyPI release is being prepared. For now, compatible Linux machines can
install a matching wheel downloaded from the repository's **Wheels** or
**Release** workflow artifacts using `python -m pip install /path/to/wheel.whl`.
See [the release guide](docs/releasing.md) for publishing and installation steps.

## Local development

Install the project and development toolchain with uv:

```bash
uv sync --locked --dev
uv run --locked systemcard
```

Development uses Python 3.12 and the locked uv environment. The local build requires CMake 3.24+, a C++20 compiler, Python 3.12 for development tools, and network access for the first build. CMake downloads the pinned [Sysal v0.0.18 release package](https://github.com/Degeneracy-Evil/sysal/releases/tag/v0.0.18), verifies its SHA-256 digest, and statically links `libsysal.a` into the native extension.

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

Release wheels target Linux x86_64 systems with glibc 2.17 or newer (CentOS 7 / RHEL 7 and newer compatible distributions). The minimum runtime version is Python 3.6.8, matching the CentOS 7 system `python3`. The wheel workflow builds CPython 3.6 through 3.14 artifacts in the manylinux2014 image, repairs them with auditwheel, and runs a real collection smoke test against each installed wheel. A separate CentOS 7 job installs the Python 3.6 wheel and exercises collection and rendering with its actual Python 3.6.8.

CentOS 7 ships an older pip that does not recognize manylinux2014 wheels. Upgrade pip without changing the system interpreter before installation:

```bash
python3 -m pip install --upgrade 'pip==21.3.1'
python3 -m pip install /path/to/systemcard-0.1.0-cp36-cp36m-manylinux*.whl
```

Python 3.6/3.7 uses Rich 12 and a legacy build adapter; newer interpreters retain the modern build backend. The project metadata is shared by both build paths.

## Selective collection and bootstrap

```bash
systemcard --section cpu,memory --no-color
systemcard --section accelerators
systemcard --compact
SYSTEMCARD_SPEC=/path/to/systemcard.whl bash run.sh --compact
```

The display adapts to terminal width: one column below 110 characters, two columns
from 110, and three from 166. On wider terminals, summary cards share aligned rows
and detailed device tables follow at full width. `--compact` shows only the summary
cards unless explicit sections are requested. Tables switch to individual records
when their columns would be cramped, and narrow summaries put labels above values.
Each invocation uses the current terminal width. After the command exits, resizing
the terminal may reflow its scrollback; run the command again to lay it out at the
new width.

Sections are validated before collection and collect only their domains plus required
identity, visibility and NUMA dependencies. CPU and memory cards show cgroup limits
separately from machine resources; GPU cards distinguish physical GPUs and MIG instances.
CPU summaries include family/model/stepping, microcode, online CPU counts, SMT state
and the frequency driver. `--section cpu` also shows per-thread kernel capabilities,
cache sharing, hardware frequency bounds, policy limits and logical CPU topology.
See [launch options](LAUNCH.md) and the [binding contract](docs/binding-contract.md).

## Hardware inventory

Default output summarizes CPU, machine/motherboard/chassis, memory, storage and
network information. Select a section to see the identities and configuration:

```bash
uv run --locked systemcard --section system
uv run --locked systemcard --section memory
uv run --locked systemcard --section storage
uv run --locked systemcard --section network
```

Details come from local kernel, driver and firmware reports. Unreadable fields
remain unknown; there are no performance benchmarks or model specification guesses.
CPU process node, IPC and undocumented IMC details are not inferred from model names.

## Hardware topology and sources

```bash
uv run --locked systemcard --section topology
uv run --locked systemcard --section network --sources
uv run --locked systemcard --section memory,storage
```

The topology view follows explicit NUMA, PCI, partition and interface relationships.
Storage details include layered block devices and every mount in the current
namespace. Network details add driver/firmware versions, supported link modes and
bridge/bond/VLAN relationships. Memory details show available EDAC controllers and
firmware ECC reports; missing controller associations or inventory completeness
remain unknown. `--sources` shows collection origins and observed failure reasons;
a successful query does not mean that the source supplied every field.

## Sensors and hardware findings

```bash
uv run --locked systemcard --section sensors
uv run --locked systemcard --section health
uv run --locked systemcard --section sensors --sources
```

Sensor details preserve kernel names, channels, units, limits and reported flags.
Hardware findings distinguish sensor alarms, md RAID degradation and historical EDAC
counts. Missing evidence remains unknown. Default output adds a concise findings
summary when findings exist; it never labels the entire machine healthy from their absence.

Storage health uses optional `smartctl` / `nvme-cli` read-only reports.
`uv run --locked systemcard --section storage --sources --no-color` shows
per-device availability and protocol-specific reports; `--section health`
separates current warnings, endurance estimates and historical errors.
Permission failures stay unknown; SystemCard never elevates privileges or changes device settings.

## Hardware overview and details

The default view contains summary cards, with machine, CPU, memory, whole disks
and physical interfaces first. Device tables, partitions, mounts and complete
identity fields appear when selecting a section. Whole-disk totals exclude
partitions and virtual block layers; physical-interface counts use explicit
kernel identity. Unknown classifications remain visible.

```bash
uv run --locked systemcard
uv run --locked systemcard --section cpu,memory
uv run --locked systemcard --section storage,network
uv run --locked systemcard --section health
```

Detailed field tables group properties by device and omit columns with no reports.
Current findings precede endurance estimates and historical error counters.
Drive-query permission or tool failures are summarized in storage and health cards;
use `--sources` for the underlying observations.
