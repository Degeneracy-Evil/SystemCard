# Native binding contract

`systemcard._native.collect(scope="default", sections=[])` returns JSON-compatible
Python values through Sysal's public System::collect() and to_json() APIs.
Scopes are default, basic, full; invalid scopes or sections fail before collection.
An empty section list uses the scope preset. full requests raw evidence, but the
returned public snapshot omits raw and includes meta.

All selected collections include Platform for the card header. Additional flags:

| Section | Collect flags |
| --- | --- |
| system | Platform, Pci |
| cpu | Cpu, Execution |
| memory | Memory, Execution |
| accelerators | Accelerator, Execution, Pci |
| network | Network, Execution |
| storage | Storage |
| software | Software |
| execution | Execution, Cpu, Accelerator |

Execution dependencies preserve resource visibility and cgroup limits. Pci supports
GPU NUMA association. Domains can share prerequisite readers; selection does not
promise that no supporting files or optional libraries are accessed.

The snapshot contains info, warnings and meta. Every nested field is optional.
Cgroup cpu_quota_us/cpu_period_us use microseconds; memory_limit/memory_current use
bytes. A true *_limit_known with a null limit means unlimited; false with a finite value means an observed upper bound from an incomplete hierarchy;
false without a value means unknown.
CPU quota/period is a time quota expressed as cores, separate from CPU affinity.
Memory current belongs to the leaf cgroup, while host memory belongs to the machine.
GPU uuid/parent_uuid identify physical and MIG devices; PCI addresses alone do not
distinguish MIG instances. Missing fields in older snapshots degrade gracefully.

The binding exposes no C++ instances and includes only public include/sysal headers
from the versioned, SHA-256-pinned release package.

Card builders are selected before presentation work. Shared schema readers normalize
mapping/list shapes and reject booleans as numeric quantities; formatters reject
non-finite measurements. No native collection or Sysal implementation logic is
moved into presentation code.

## CPU hardware details

Sysal exposes per-thread `identification` (x86 family/model/stepping, ARM IDs,
microcode and complete kernel capability strings), optional online status, explicit
present/online sets and SMT control/activity. Frequency policy values are Hz:
hardware bounds, policy limits and the kernel's current reports are distinct.
`scaling_current_frequency` may be a requested or reported value. Cache instances
include ID, sets and shared CPU IDs; explicit identical instances are deduplicated.
Missing fields in older snapshots remain unknown. Default CPU output is a summary;
`--section cpu` includes the full hardware details.

## Ordinary hardware details

System cards show motherboard/chassis summaries; selecting system adds machine,
board, chassis and firmware identities, plus PCI slots/firmware labels supplied by
the kernel. UUIDs and serials remain missing when unreadable. An observed EFI
interface confirms UEFI; its absence is not proof of legacy boot.

Memory details include each DIMM's type, configured rate, rank, widths, form,
reported voltage in mV and identity. NUMA free and available are distinct.
Network details include the PCI name, driver, MTU, duplex, carrier and NUMA node.
Storage details include model, serial, firmware, WWID, explicit transport, PCI
controller and block/I/O sizes. Sizes are bytes; network speed is bps and describes
a reported link, not maximum hardware capability. Older snapshots tolerate missing
fields. Network/Storage use auxiliary PCI collection inside Sysal; requested flags
retain their public meaning. RAID device reports describe the exposed logical device.
