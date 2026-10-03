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
| memory | Memory, Execution, Cpu, Pci |
| accelerators | Accelerator, Execution, Cpu, Pci |
| network | Network, Execution, Cpu |
| storage | Storage, StorageHealth |
| software | Software |
| execution | Execution, Cpu, Accelerator |
| topology | Cpu, Memory, Network, Storage, Pci |
| sensors | Sensors |
| health | Sensors, Memory, Storage, Pci, StorageHealth |

Execution dependencies include Cpu so its explicit visible CPU IDs can be checked
against an actual CPU inventory, including when only network or memory is displayed.
They preserve resource visibility and cgroup limits. Pci supports
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

## PCIe connections

Sysal 0.0.17 adds explicit direct upstream addresses, bound PCI driver names,
PF addresses for VFs, kernel local CPU lists, and maximum/enabled VF counts.
Network and storage detail views join controllers by exact PCI address, retain
current and maximum links separately, and follow only reported upstream addresses.
Paths mark where reports stop, where a device report is missing, or where a cycle
occurs; they do not claim a complete motherboard topology or application throughput.
The topology view lists devices with connection, link, slot, or SR-IOV reports;
the underlying JSON retains the complete PCI inventory.
Kernel local CPUs are not evidence for filling an unknown NUMA node. Missing
capability data is unknown, and zero enabled VFs is retained as a valid report.
No link negotiation difference is reinterpreted as a health finding.

## Hardware relationships and source observations

Network collection also reports `network.rdma`: sysfs discovery status and RDMA
devices, with node type, GUIDs, firmware, bound driver, PCI/NUMA, and reported ports.
Port reports retain logical/physical state, explicit InfiniBand/Ethernet link layer,
the kernel's complete rate string, optional rate in bps, LIDs, SM fields and the
capability mask. Ethernet does not prove RoCE or iWARP, and reported rates are not
application throughput or maximum device capability.
Backing device interfaces are distinct from explicit port interfaces supplied by
GID ndev reports; a device with no netdev is retained. Discovery status describes
class directory enumeration, not completion of every attribute or device health.
Missing/permission failures remain visible through `--sources`, and old snapshots
without RDMA reports remain compatible. No fabric probe, performance counter read,
port modification, or extra software dependency is introduced.

`--section topology` displays explicit NUMA/CPU package, PCI attachment, partition,
block dependency and interface relationships. It is an opt-in view assembled from
public fields; no relationship is inferred from a device, bank or slot name.
Memory selection requests PCI to resolve EDAC controller NUMA associations when
available. EDAC controller indices are independent of CPU and NUMA indices.

Storage includes partitions and device-mapper/md layers, explicit parent/slave
relationships, and all mountinfo records from the current mount namespace.
Mounts are associated by exact major/minor and retain decoded paths, filesystem
root and mount options. Capacity summaries avoid counting partition/virtual layers
again; hardware RAID still describes the exposed logical disk.

Network capability and firmware fields come from optional read-only ethtool
queries. Supported, advertised and peer modes are distinct from current link speed.
Partial query output remains usable; permanent MAC is never substituted from the
current interface address. Bridge/bond/master/lower/VLAN relationships use explicit
sysfs/proc records.

Memory reports firmware array ECC/location/maximum capacity separately from EDAC
controller counters and per-DIMM correction modes. Inventory completeness is only
known when the firmware reports a slot count; matching this count does not prove
that firmware describes every physical slot correctly.

`meta.observations` contains hardware source origins and collection status without
raw payloads. `--sources` appends this information to the selected cards, including
observed missing-file, permission, unsupported-query, missing-tool and timeout
reasons. A successful read does not promise that every field was supplied. A missing
reason remains unknown, especially for older snapshots. No collection auto-elevates
permissions or changes device settings.

## Sensors and hardware findings

Default collection now includes Sensors. Sensors selection reads only Platform and
Sensors; health includes Memory/Storage/Pci dependencies. Compact default collection
also requests Sensors while retaining compact presentation.

Public sensors contain temperatures (signed millidegrees Celsius), fans (RPM) and
powers (microwatts). Input and average are separate, and limits/flags remain optional.
Nonstandard temperature units are marked unsupported. Missing firmware labels and
associations stay unknown; duplicate-looking chips are distinguished by explicit PCI.
Legacy CPU thermal zones retain their public schema and are labelled as thermal zones,
without claiming that their maximum is CPU temperature.

hardware_health contains sensor_alerts, storage_alerts, memory_events and coverage.
Sysal derives these findings from already collected typed models. Python does no
threshold comparison or driver-status interpretation. Driver flags may be latched;
EDAC events are cumulative since initialization/reset. No findings does not establish
normal operation. Default output adds a compact findings card only when findings exist;
full evidence is available through --section health and --sources. Unsupported or
unreadable power/fan/EDAC data cannot be replaced by a claim of normal operation.

## Read-only storage health

`storage.health` contains controller/disk reports and explicit block-device associations.
NVMe queries are controller-wide; counters are not repeated or summed per namespace.
NVMe counters use exact unsigned decimal strings (up to 128 bits); `temperature` is
signed milliCelsius, data unit counts are in units of 1000 * 512 bytes, and
`percentage_used` is a vendor endurance estimate that can exceed 100.
ATA attributes retain tool-provided normalized values, thresholds, failure period
and vendor raw display text. SCSI uncorrected counts are historical cumulative values.

`hardware_health.drive_findings` carries typed C++ findings, keeping current flags,
endurance estimates and historical events separate. SMART overall passed does not
guarantee a fault-free device. No usable reports means unknown, including permission
failures, absent tools, unsupported hardware and skipped low-power devices.
`--section storage --sources` explains individual query outcomes.

Queries use optional smartctl (JSON-capable 7.x), with nvme-cli only when smartctl
is absent for NVMe. No installation, privilege escalation, SMART enabling, self-test,
configuration change, media scan or hardware RAID port probing is performed. ATA
power checks skip standby and unsupported checks; SCSI standby checks depend on
driver support. Compact collection does not add these device queries.

## Presentation levels

Default output shows summary cards without detail tables; selecting a section
expands its hardware fields. `--compact` keeps the existing four collection domains
and optional sensor findings. Presentation ordering does not change Sysal flags.
DetailTable may declare a grouping column for device field/value records; the
renderer preserves row order within each device, hides all-missing columns, and
retains zero and false reports. Native JSON remains unchanged.
