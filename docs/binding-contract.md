# Native binding contract

`systemcard._native.collect(scope="default", sections=[])` returns JSON-compatible
Python values through Sysal's public System::collect() and to_json() APIs.
Scopes are default, basic, full; invalid scopes or sections fail before collection.
An empty section list uses the scope preset. full requests raw evidence, but the
returned public snapshot omits raw and includes meta.

All selected collections include Platform for the card header. Additional flags:

| Section | Collect flags |
| --- | --- |
| system | Platform |
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
