"""Transform normalized snapshots into renderer-friendly cards."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from systemcard.formatters import (
    UNKNOWN,
    bit_rate,
    bytes_value,
    enum_text,
    frequency,
    pci_address,
    temperature,
    text,
    yes_no,
)
from systemcard.schema import SECTIONS

ACCELERATOR_KINDS = {0: "GPU", 1: "NPU", 2: "FPGA", 3: "Other"}
STORAGE_KINDS = {0: "NVMe", 1: "SSD", 2: "HDD", 3: "Other"}
INTERFACE_STATES = {0: "UP", 1: "DOWN", 2: "UNKNOWN"}
CACHE_TYPES = {0: "Data", 1: "Instruction", 2: "Unified", 3: "Other"}
ISA_EXTENSIONS = {
    0: "SSE",
    1: "SSE2",
    2: "SSE3",
    3: "SSSE3",
    4: "SSE4.1",
    5: "SSE4.2",
    6: "AVX",
    7: "AVX2",
    8: "AVX-512F",
    9: "AVX-512CD",
    10: "AVX-512BW",
    11: "AVX-512DQ",
    12: "AVX-512VL",
    13: "AES",
    14: "FMA",
    15: "F16C",
    16: "PCLMULQDQ",
}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _items(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _mappings(value: object) -> list[Mapping[str, Any]]:
    return [_mapping(item) for item in _items(value)]


def _integer(value: object, default: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _joined(values: object, separator: str = ", ") -> str:
    rendered = [text(value) for value in _items(values) if text(value) != UNKNOWN]
    return separator.join(rendered) or UNKNOWN


def _limited(items: list[Mapping[str, Any]], detailed: bool, limit: int) -> list[Mapping[str, Any]]:
    return items if detailed else items[:limit]


@dataclass(frozen=True)
class DetailTable:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    omitted: int = 0


@dataclass(frozen=True)
class Card:
    section: str
    title: str
    rows: tuple[tuple[str, str], ...]
    tables: tuple[DetailTable, ...] = ()


@dataclass(frozen=True)
class DisplayModel:
    title: str
    subtitle: str
    cards: tuple[Card, ...]
    warnings: tuple[str, ...]
    footer: str = ""


def _system_card(platform: Mapping[str, Any]) -> Card:
    host = _mapping(platform.get("host"))
    os_info = _mapping(platform.get("os"))
    kernel = _mapping(platform.get("kernel"))
    architecture = _mapping(platform.get("architecture"))
    firmware = _mapping(platform.get("firmware"))
    distribution = text(os_info.get("distribution_version"))
    if distribution == UNKNOWN:
        distribution = (
            " ".join(part for part in (text(os_info.get("name")), text(os_info.get("version"))) if part != UNKNOWN)
            or UNKNOWN
        )
    else:
        os_name = text(os_info.get("name"))
        if os_name != UNKNOWN and not distribution.lower().startswith(os_name.lower()):
            distribution = f"{os_name} {distribution}"
    hardware = (
        " ".join(part for part in (text(host.get("vendor")), text(host.get("product_name"))) if part != UNKNOWN)
        or UNKNOWN
    )
    bios = (
        " ".join(
            part for part in (text(firmware.get("bios_vendor")), text(firmware.get("bios_version"))) if part != UNKNOWN
        )
        or UNKNOWN
    )
    arch = text(architecture.get("name"))
    bits = architecture.get("bits")
    if isinstance(bits, int):
        arch = f"{arch} ({bits}-bit, {text(architecture.get('byte_order'))}-endian)"
    return Card(
        "system",
        "System",
        (
            ("Host", text(host.get("hostname"))),
            ("Operating system", distribution),
            ("Kernel", text(kernel.get("release"))),
            ("Architecture", arch),
            ("Hardware", hardware),
            ("Firmware", f"{bios} · {'UEFI' if firmware.get('uefi') is True else 'Legacy/unknown'}"),
        ),
    )


def _cpu_card(cpu: Mapping[str, Any], detailed: bool, show_tables: bool) -> Card:
    packages = _mappings(cpu.get("packages"))
    cores = _mappings(cpu.get("cores"))
    logical = _mappings(cpu.get("logical_cpus"))
    visible = sum(item.get("visible_to_current_process") is True for item in logical)
    numa_nodes = _mappings(cpu.get("numa_nodes"))
    model_names = list(dict.fromkeys(text(item.get("model_name")) for item in packages))
    base_frequencies: list[int] = []
    max_frequencies: list[int] = []
    for item in packages:
        base_frequency = item.get("base_frequency")
        max_frequency = item.get("max_frequency")
        if isinstance(base_frequency, int):
            base_frequencies.append(base_frequency)
        if isinstance(max_frequency, int):
            max_frequencies.append(max_frequency)
    frequency_range = UNKNOWN
    if base_frequencies or max_frequencies:
        frequency_range = " / ".join(
            part
            for part in (
                f"base {frequency(max(base_frequencies))}" if base_frequencies else "",
                f"max {frequency(max(max_frequencies))}" if max_frequencies else "",
            )
            if part
        )
    isa = " ".join(enum_text(ISA_EXTENSIONS, item) for item in _items(cpu.get("isa_extensions"))) or UNKNOWN
    thermals = _mappings(cpu.get("thermal_zones"))
    thermal_values: list[int | float] = []
    for item in thermals:
        thermal_value = item.get("temp")
        if isinstance(thermal_value, (int, float)):
            thermal_values.append(thermal_value)

    package_rows = tuple(
        (
            str(item.get("id", index)),
            text(item.get("model_name")),
            str(_integer(item.get("physical_cores"))),
            str(_integer(item.get("logical_threads"))),
            frequency(item.get("base_frequency")),
            frequency(item.get("max_frequency")),
        )
        for index, item in enumerate(packages)
    )

    cache_counts: Counter[tuple[int, int, int, int, int]] = Counter()
    for item in _mappings(cpu.get("caches")):
        cache_counts[
            (
                _integer(item.get("level")),
                _integer(item.get("type"), 3),
                _integer(item.get("size")),
                _integer(item.get("ways")),
                _integer(item.get("line_size")),
            )
        ] += 1
    cache_rows = tuple(
        (
            f"L{level}",
            enum_text(CACHE_TYPES, kind),
            bytes_value(size),
            str(ways) if ways else UNKNOWN,
            bytes_value(line_size),
            str(count),
        )
        for (level, kind, size, ways, line_size), count in sorted(cache_counts.items())
    )
    thermal_rows = tuple(
        (text(item.get("type")), text(item.get("name")), temperature(item.get("temp"))) for item in thermals
    )
    tables = [DetailTable("Packages", ("ID", "Model", "Cores", "Threads", "Base", "Max"), package_rows)]
    if cache_rows:
        tables.append(DetailTable("Cache topology", ("Level", "Type", "Size", "Ways", "Line", "Instances"), cache_rows))
    if thermal_rows:
        tables.append(DetailTable("Thermals", ("Sensor", "Zone", "Temperature"), thermal_rows))
    return Card(
        "cpu",
        "CPU",
        (
            ("Model", " / ".join(model_names) or UNKNOWN),
            ("Topology", f"{len(packages)} packages · {len(cores)} cores · {len(logical)} logical"),
            ("Process visibility", f"{visible} of {len(logical)} logical CPUs"),
            ("NUMA", f"{len(numa_nodes)} nodes"),
            ("Frequency", frequency_range),
            ("Governor", text(cpu.get("governor"))),
            ("ISA", isa),
            ("Temperature", temperature(max(thermal_values)) if thermal_values else UNKNOWN),
        ),
        tuple((tables if detailed else tables[:1]) if show_tables else ()),
    )


def _memory_card(memory: Mapping[str, Any], detailed: bool, show_tables: bool) -> Card:
    total = memory.get("total_memory")
    available = memory.get("available_memory")
    used = total - available if isinstance(total, (int, float)) and isinstance(available, (int, float)) else None
    dimms = _mappings(memory.get("dimms"))
    populated = [item for item in dimms if item.get("present") is True]
    shown = _limited(populated, detailed, 8)
    dimm_rows = tuple(
        (
            text(item.get("locator")),
            text(item.get("bank_locator")),
            bytes_value(item.get("size")),
            f"{item['speed_mts']} MT/s" if isinstance(item.get("speed_mts"), int) else UNKNOWN,
            text(item.get("manufacturer")),
            text(item.get("part_number")),
        )
        for item in shown
    )
    tables: tuple[DetailTable, ...] = ()
    if dimm_rows and show_tables:
        tables = (
            DetailTable(
                "Populated DIMMs",
                ("Slot", "Bank", "Size", "Speed", "Vendor", "Part number"),
                dimm_rows,
                len(populated) - len(shown),
            ),
        )
    return Card(
        "memory",
        "Memory",
        (
            ("Total", bytes_value(total)),
            ("Used / available", f"{bytes_value(used)} / {bytes_value(available)}"),
            ("Technology", text(memory.get("memory_type"))),
            (
                "Configured speed",
                f"{memory['configured_speed_mts']} MT/s"
                if isinstance(memory.get("configured_speed_mts"), int)
                else UNKNOWN,
            ),
            (
                "DIMM population",
                f"{_integer(memory.get('populated_dimms'), len(populated))} of {_integer(memory.get('dimm_count'), len(dimms))} slots",
            ),
        ),
        tables,
    )


def _accelerator_card(accelerators: Mapping[str, Any], show_tables: bool) -> Card:
    devices = _mappings(accelerators.get("devices"))
    visible = sum(item.get("visible_to_current_process") is True for item in devices)
    kinds = Counter(enum_text(ACCELERATOR_KINDS, item.get("kind")) for item in devices)
    breakdown = " · ".join(f"{count} {kind}" for kind, count in kinds.items()) or "No accelerators detected"
    rows = tuple(
        (
            str(item.get("id", index)),
            enum_text(ACCELERATOR_KINDS, item.get("kind")),
            text(item.get("name")),
            bytes_value(item.get("memory_size")),
            pci_address(item.get("pci_address")),
            text(item.get("nearest_numa_node")),
            yes_no(item.get("visible_to_current_process")),
        )
        for index, item in enumerate(devices)
    )
    tables = (
        (DetailTable("Devices", ("ID", "Kind", "Name", "Memory", "PCI", "NUMA", "Visible"), rows),)
        if rows and show_tables
        else ()
    )
    return Card(
        "accelerators",
        "Accelerators",
        (("Summary", breakdown), ("Process visibility", f"{visible} of {len(devices)} devices")),
        tables,
    )


def _network_card(network: Mapping[str, Any], detailed: bool) -> Card:
    interfaces = _mappings(network.get("interfaces"))
    up = [item for item in interfaces if item.get("state") == 0]
    visible = sum(item.get("visible_to_current_process") is True for item in interfaces)
    virtual_prefixes = ("br-", "docker", "veth")
    preferred = [
        item
        for item in interfaces
        if item.get("state") == 0
        and item.get("name") != "lo"
        and (item.get("pci_address") or not str(item.get("name", "")).startswith(virtual_prefixes))
    ]
    source = interfaces if detailed else (preferred if preferred else interfaces)
    shown = _limited(source, detailed, 8)
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    if detailed:
        columns = ("Name", "State", "Speed", "Addresses", "Hardware")
        rows = tuple(
            (
                text(item.get("name")),
                enum_text(INTERFACE_STATES, item.get("state")),
                bit_rate(item.get("speed")),
                _joined(item.get("addresses"), "\n"),
                f"MAC {text(item.get('mac'))}\nPCI {pci_address(item.get('pci_address'))}",
            )
            for item in shown
        )
    else:
        columns = ("Name", "Link", "Addresses", "PCI")
        rows = tuple(
            (
                text(item.get("name")),
                f"{enum_text(INTERFACE_STATES, item.get('state'))} · {bit_rate(item.get('speed'))}",
                _joined(_items(item.get("addresses"))[:2], "\n"),
                pci_address(item.get("pci_address")),
            )
            for item in shown
        )
    return Card(
        "network",
        "Network",
        (
            ("Interfaces", f"{len(interfaces)} total · {len(up)} up"),
            ("Process visibility", f"{visible} of {len(interfaces)} interfaces"),
        ),
        (
            DetailTable(
                "Interfaces",
                columns,
                rows,
                len(source) - len(shown),
            ),
        ),
    )


def _storage_card(storage: Mapping[str, Any], detailed: bool) -> Card:
    devices = _mappings(storage.get("devices"))
    useful = [item for item in devices if item.get("kind") != 3 or item.get("mount_point")]
    shown = _limited(useful if useful else devices, detailed, 12)
    total = sum(_integer(item.get("capacity")) for item in useful)
    rows = tuple(
        (
            text(item.get("name")),
            enum_text(STORAGE_KINDS, item.get("kind")),
            bytes_value(item.get("capacity")),
            text(item.get("fs_type")),
            text(item.get("mount_point")),
            pci_address(item.get("pci_address")),
        )
        for item in shown
    )
    return Card(
        "storage",
        "Storage",
        (("Devices", f"{len(useful)} physical/mounted · {len(devices)} total"), ("Raw capacity", bytes_value(total))),
        (
            DetailTable(
                "Block devices",
                ("Name", "Kind", "Capacity", "FS", "Mount", "PCI"),
                rows,
                len(useful if useful else devices) - len(shown),
            ),
        ),
    )


def _software_card(software: Mapping[str, Any]) -> Card:
    drivers = _mappings(software.get("drivers"))
    runtimes = _mappings(software.get("runtimes"))
    compilers = _mappings(software.get("compilers"))
    cuda = _mapping(software.get("cuda"))
    mpi = _mapping(software.get("mpi"))
    rdma = _mapping(software.get("rdma"))
    tool_rows = tuple(
        ("Compiler", text(item.get("name")), text(item.get("version")), text(item.get("path"))) for item in compilers
    ) + tuple(
        ("Runtime", text(item.get("name")), text(item.get("version")), text(item.get("path"))) for item in runtimes
    )
    driver_rows = tuple(
        (text(item.get("name")), text(item.get("version")), yes_no(item.get("loaded"))) for item in drivers
    )
    tables = []
    if tool_rows:
        tables.append(DetailTable("Toolchain", ("Kind", "Name", "Version", "Path"), tool_rows))
    if driver_rows:
        tables.append(DetailTable("Drivers", ("Name", "Version", "Loaded"), driver_rows))
    return Card(
        "software",
        "Software",
        (
            ("CUDA", f"{text(cuda.get('version'))} · driver {text(cuda.get('driver_version'))}"),
            ("CUDA home", text(cuda.get("home"))),
            ("MPI", f"{text(mpi.get('implementation'))} {text(mpi.get('version'))}"),
            ("RDMA core", text(rdma.get("rdma_core_version"))),
            ("UCX", text(rdma.get("ucx_version"))),
        ),
        tuple(tables),
    )


def _execution_card(execution: Mapping[str, Any], visible_cpu_count: int, visible_accelerator_count: int) -> Card:
    process = _mapping(execution.get("process"))
    permission = _mapping(execution.get("permission"))
    cgroup = _mapping(execution.get("cgroup"))
    cpuset = _mapping(execution.get("cpuset"))
    cgroup_version = enum_text({0: "v1", 1: "v2"}, cgroup.get("version"))
    return Card(
        "execution",
        "Execution context",
        (
            (
                "Process",
                f"{text(process.get('comm'))} · PID {text(process.get('pid'))} · PPID {text(process.get('ppid'))}",
            ),
            (
                "Identity",
                f"UID {text(process.get('uid'))} · GID {text(process.get('gid'))} · root {yes_no(permission.get('is_root'))}",
            ),
            ("Cgroup", f"{cgroup_version} · {text(cgroup.get('path'))}"),
            ("CPU set", text(cpuset.get("cpus_effective"))),
            ("Memory nodes", text(cpuset.get("mems_effective"))),
            ("Visible resources", f"{visible_cpu_count} CPUs · {visible_accelerator_count} accelerators"),
        ),
    )


def build(
    snapshot: Mapping[str, Any],
    compact: bool = False,
    sections: list[str] | None = None,
) -> DisplayModel:
    """Build a resilient presentation model from a public Sysal JSON snapshot."""
    info = _mapping(snapshot.get("info"))
    platform = _mapping(info.get("platform"))
    hostname = text(_mapping(platform.get("host")).get("hostname"))
    detailed = sections is not None
    show_tables = not compact or sections is not None
    cpu = _mapping(info.get("cpu"))
    accelerators = _mapping(info.get("accelerators"))
    visible_cpu_count = sum(
        item.get("visible_to_current_process") is True for item in _mappings(cpu.get("logical_cpus"))
    )
    visible_accelerator_count = sum(
        item.get("visible_to_current_process") is True for item in _mappings(accelerators.get("devices"))
    )
    cards = [
        _system_card(platform),
        _cpu_card(cpu, detailed, show_tables),
        _memory_card(_mapping(info.get("memory")), detailed, show_tables),
        _accelerator_card(accelerators, show_tables),
    ]
    if not compact or sections:
        cards.extend(
            [
                _network_card(_mapping(info.get("network")), detailed),
                _storage_card(_mapping(info.get("storage")), detailed),
                _software_card(_mapping(info.get("software"))),
                _execution_card(_mapping(info.get("execution")), visible_cpu_count, visible_accelerator_count),
            ]
        )
    if sections:
        wanted = tuple(section for section in SECTIONS if section in sections)
        cards = [card for card in cards if card.section in wanted]
    warnings = tuple(str(item) for item in _items(snapshot.get("warnings")) if item)
    meta = _mapping(snapshot.get("meta"))
    footer_parts = []
    if text(meta.get("sysal_version")) != UNKNOWN:
        footer_parts.append(f"Sysal {text(meta.get('sysal_version'))}")
    duration = meta.get("collect_duration")
    if isinstance(duration, (int, float)):
        footer_parts.append(f"collected in {duration * 1000:.0f} ms")
    return DisplayModel("SystemCard", hostname, tuple(cards), warnings, " · ".join(footer_parts))
