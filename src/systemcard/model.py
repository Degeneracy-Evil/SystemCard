"""Transform normalized snapshots into renderer-friendly cards."""

from typing import Any, Callable, Counter, Dict, List, Mapping, Optional, Tuple, Union

from systemcard.formatters import (
    UNKNOWN,
    bit_rate,
    bytes_value,
    cpu_list,
    enum_text,
    frequency,
    pci_address,
    temperature,
    text,
    yes_no,
)
from systemcard.health import has_findings, health_card
from systemcard.presentation_types import Card as Card
from systemcard.presentation_types import DetailTable as DetailTable
from systemcard.presentation_types import DisplayModel as DisplayModel
from systemcard.schema import (
    SECTIONS,
    integer_value,
    number_value,
)
from systemcard.schema import (
    integer_or as _integer,
)
from systemcard.schema import (
    list_value as _items,
)
from systemcard.schema import (
    mapping_items as _mappings,
)
from systemcard.schema import (
    mapping_value as _mapping,
)
from systemcard.sensors import sensors_card
from systemcard.sources import with_sources
from systemcard.storage_health import storage_health_tables
from systemcard.topology import topology_card

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


def _joined(values: object, separator: str = ", ") -> str:
    rendered = [text(value) for value in _items(values) if text(value) != UNKNOWN]
    return separator.join(rendered) or UNKNOWN


def _limited(items: List[Mapping[str, Any]], detailed: bool, limit: int) -> List[Mapping[str, Any]]:
    return items if detailed else items[:limit]


def _system_card(platform: Mapping[str, Any], pci: Mapping[str, Any], detailed: bool) -> Card:
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
    bits = integer_value(architecture.get("bits"))
    if bits is not None:
        arch = f"{arch} ({bits}-bit, {text(architecture.get('byte_order'))}-endian)"
    rows: List[Tuple[str, str]] = [
        ("Host", text(host.get("hostname"))),
        ("Operating system", distribution),
        ("Kernel", text(kernel.get("release"))),
        ("Architecture", arch),
        ("Hardware", hardware),
        ("Firmware", f"{bios} · {'UEFI' if firmware.get('uefi') is True else 'Legacy/unknown'}"),
    ]
    board = _mapping(platform.get("baseboard"))
    chassis = _mapping(platform.get("chassis"))
    if board:
        rows.append(("Motherboard", _joined([board.get("vendor"), board.get("name"), board.get("version")], " ")))
    if chassis:
        rows.append(
            (
                "Chassis",
                _joined(
                    [
                        chassis.get("vendor"),
                        f"SMBIOS type {chassis['type']}" if chassis.get("type") is not None else None,
                    ],
                    " · ",
                ),
            )
        )
    tables: List[DetailTable] = []
    if detailed:
        groups = (
            (
                "Machine identity",
                host,
                (
                    ("vendor", "Vendor"),
                    ("product_name", "Model"),
                    ("product_family", "Family"),
                    ("product_version", "Product version"),
                    ("product_sku", "SKU"),
                    ("serial", "Serial"),
                    ("product_uuid", "Product UUID"),
                    ("machine_id", "OS machine-id"),
                ),
            ),
            (
                "Motherboard identity",
                board,
                (
                    ("vendor", "Vendor"),
                    ("name", "Model"),
                    ("version", "Version"),
                    ("serial", "Serial"),
                    ("asset_tag", "Asset tag"),
                ),
            ),
            (
                "Chassis identity",
                chassis,
                (
                    ("vendor", "Vendor"),
                    ("type", "SMBIOS type code"),
                    ("version", "Version"),
                    ("serial", "Serial"),
                    ("asset_tag", "Asset tag"),
                ),
            ),
            (
                "Firmware identity",
                firmware,
                (
                    ("bios_vendor", "Vendor"),
                    ("bios_version", "Version"),
                    ("bios_date", "Date"),
                    ("bios_release", "BIOS revision"),
                    ("ec_firmware_release", "EC firmware revision"),
                ),
            ),
        )
        for title, source, fields in groups:
            values = tuple((label, text(source.get(key))) for key, label in fields if text(source.get(key)) != UNKNOWN)
            if values:
                tables.append(DetailTable(title, ("Field", "Value"), values))
    if detailed:
        slots = [
            item for item in _mappings(pci.get("devices")) if item.get("physical_slot") or item.get("firmware_label")
        ]
        if slots:
            tables.append(
                DetailTable(
                    "PCI slots and firmware labels",
                    ("Slot", "PCI", "Device", "Label", "Current link", "Maximum link"),
                    tuple(
                        (
                            text(item.get("physical_slot")),
                            pci_address(item.get("address")),
                            text(item.get("device_name")),
                            text(item.get("firmware_label")),
                            f"{text(item.get('current_link_speed'))} · x{text(item.get('current_link_width'))}",
                            f"{text(item.get('max_link_speed'))} · x{text(item.get('max_link_width'))}",
                        )
                        for item in slots
                    ),
                )
            )
    return Card("system", "System", tuple(rows), tuple(tables))


def _cpu_quota(cgroup: Mapping[str, Any]) -> str:
    raw_quota = cgroup.get("cpu_quota_us")
    if raw_quota is None:
        return "Unlimited" if cgroup.get("cpu_limit_known") is True else UNKNOWN
    quota = integer_value(raw_quota)
    period = integer_value(cgroup.get("cpu_period_us"))
    if quota is None or period is None or quota <= 0 or period <= 0:
        return UNKNOWN
    rendered = f"{quota / period:g} CPUs"
    return rendered if cgroup.get("cpu_limit_known") is True else f"≤ {rendered} (partial)"


def _memory_limit(cgroup: Mapping[str, Any]) -> str:
    raw_limit = cgroup.get("memory_limit")
    if raw_limit is None:
        return "Unlimited" if cgroup.get("memory_limit_known") is True else UNKNOWN
    limit = integer_value(raw_limit)
    if limit is None or limit < 0:
        return UNKNOWN
    rendered = bytes_value(limit)
    return rendered if cgroup.get("memory_limit_known") is True else f"≤ {rendered} (partial)"


def _cpu_hardware_tables(cpu: Mapping[str, Any], logical: List[Mapping[str, Any]], detailed: bool) -> List[DetailTable]:
    tables: List[DetailTable] = []
    identity_fields = (
        ("family", "Family"),
        ("model", "Model number"),
        ("stepping", "Stepping"),
        ("microcode", "Microcode"),
        ("implementer", "ARM implementer"),
        ("part", "ARM part"),
        ("variant", "ARM variant"),
        ("revision", "ARM revision"),
        ("architecture", "Reported architecture"),
    )
    identities: Dict[Tuple[Tuple[str, str], ...], List[int]] = {}
    features: Dict[Tuple[str, ...], List[int]] = {}
    for item in logical:
        number = integer_value(item.get("id"))
        if number is None:
            continue
        identity = _mapping(item.get("identification"))
        fields = tuple(
            (label, text(identity.get(key))) for key, label in identity_fields if text(identity.get(key)) != UNKNOWN
        )
        if fields:
            identities.setdefault(fields, []).append(number)
        flags = tuple(str(flag) for flag in _items(identity.get("features")) if isinstance(flag, str) and flag)
        if flags:
            features.setdefault(flags, []).append(number)
    if identities:
        rows: Tuple[Tuple[str, ...], ...] = tuple(
            (cpu_list(ids), label, value) for fields, ids in identities.items() for label, value in fields
        )
        tables.append(DetailTable("Identification", ("CPUs", "Field", "Value"), rows))
    if detailed and features:
        tables.append(
            DetailTable(
                "Kernel capabilities",
                ("CPUs", "Features"),
                tuple((cpu_list(ids), " ".join(flags)) for flags, ids in features.items()),
            )
        )
    caches = _mappings(cpu.get("caches"))
    if detailed and any(item.get("shared_cpus") for item in caches):
        rows = tuple(
            (
                f"L{_integer(item.get('level'))}",
                enum_text(CACHE_TYPES, item.get("type")),
                text(item.get("cache_id")),
                bytes_value(item.get("size")),
                text(item.get("sets")),
                cpu_list(item.get("shared_cpus")),
            )
            for item in caches
        )
        tables.append(DetailTable("Cache sharing", ("Level", "Type", "ID", "Size", "Sets", "CPUs"), rows))
    policies = _mappings(cpu.get("frequency_policies"))
    if policies:
        rows = tuple(
            (
                str(item.get("index", "—")),
                cpu_list(item.get("related_cpus")),
                frequency(item.get("hardware_min_frequency")),
                frequency(item.get("hardware_max_frequency")),
                frequency(item.get("scaling_min_frequency")),
                frequency(item.get("scaling_max_frequency")),
                frequency(item.get("scaling_current_frequency")),
                text(item.get("driver")),
                text(item.get("governor")),
            )
            for item in _limited(policies, detailed, 4)
        )
        tables.append(
            DetailTable(
                "Frequency policies (kernel reports)",
                ("Policy", "CPUs", "HW min", "HW max", "Policy min", "Policy max", "Reported", "Driver", "Governor"),
                rows,
                omitted=max(0, len(policies) - len(rows)),
            )
        )
        if detailed:
            rows = tuple(
                (
                    str(item.get("index", "—")),
                    cpu_list(item.get("affected_cpus")),
                    frequency(item.get("base_frequency")),
                    frequency(item.get("hardware_current_frequency")),
                    text(item.get("energy_performance_preference")),
                )
                for item in policies
            )
            tables.append(
                DetailTable(
                    "Frequency policy details",
                    ("Policy", "Affected CPUs", "Base", "HW reported", "Energy preference"),
                    rows,
                )
            )
    if detailed and "online_cpu_ids" in cpu:
        rows = tuple(
            (
                str(item.get("id", "—")),
                str(item.get("package_id", "—")),
                str(item.get("core_id", "—")),
                text(item.get("numa_node")),
                yes_no(item.get("online")),
                yes_no(item.get("visible_to_current_process")),
            )
            for item in logical
        )
        tables.append(
            DetailTable("Logical CPU topology", ("CPU", "Package", "Core", "NUMA", "Online", "Visible"), rows)
        )
    return tables


def _cpu_card(
    cpu: Mapping[str, Any], detailed: bool, show_tables: bool, cgroup: Mapping[str, Any], architecture: str
) -> Card:
    packages = _mappings(cpu.get("packages"))
    cores = _mappings(cpu.get("cores"))
    logical = _mappings(cpu.get("logical_cpus"))
    visible = sum(item.get("visible_to_current_process") is True for item in logical)
    numa_nodes = _mappings(cpu.get("numa_nodes"))
    model_names = list(dict.fromkeys(text(item.get("model_name")) for item in packages))
    base_frequencies: List[int] = []
    max_frequencies: List[int] = []
    for item in packages:
        base_frequency = integer_value(item.get("base_frequency"))
        max_frequency = integer_value(item.get("max_frequency"))
        if base_frequency is not None:
            base_frequencies.append(base_frequency)
        if max_frequency is not None:
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
    thermal_values: List[Union[int, float]] = []
    for item in thermals:
        thermal_value = number_value(item.get("temp"))
        if thermal_value is not None:
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

    cache_counts: Counter[Tuple[int, int, int, int, int]] = Counter()
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
    if show_tables and detailed:
        tables.extend(_cpu_hardware_tables(cpu, logical, detailed))
    hardware_rows: List[Tuple[str, str]] = []
    if cpu.get("caches") and all(item.get("shared_cpus") for item in _mappings(cpu.get("caches"))):
        hardware_rows.extend(
            (f"L{level} {enum_text(CACHE_TYPES, kind).lower()} cache", f"{bytes_value(size)} · {count} instances")
            for (level, kind, size, _ways, _line), count in sorted(cache_counts.items())
        )
    for key, label in (
        ("family", "Family"),
        ("model", "Model number"),
        ("stepping", "Stepping"),
        ("microcode", "Microcode"),
    ):
        values = sorted({text(_mapping(item.get("identification")).get(key)) for item in logical})
        if values and values != [UNKNOWN]:
            hardware_rows.append((label, " / ".join(values)))
    if "online_cpu_ids" in cpu or "present_cpu_ids" in cpu:
        online = str(len(_items(cpu["online_cpu_ids"]))) if "online_cpu_ids" in cpu else UNKNOWN
        present = str(len(_items(cpu["present_cpu_ids"]))) if "present_cpu_ids" in cpu else UNKNOWN
        hardware_rows.append(("CPU state", f"{online} online · {present} present"))
    if "smt_active" in cpu or cpu.get("smt_control"):
        active = cpu.get("smt_active")
        state = "Active" if active is True else "Inactive" if active is False else UNKNOWN
        hardware_rows.append(("SMT", f"{state} · control {text(cpu.get('smt_control'))}"))
    if "boost_enabled" in cpu:
        hardware_rows.append(("Boost enabled", yes_no(cpu.get("boost_enabled"))))
    policies = _mappings(cpu.get("frequency_policies"))
    drivers = sorted({str(item["driver"]) for item in policies if item.get("driver")})
    if drivers:
        hardware_rows.append(("Frequency driver", " / ".join(drivers)))
    return Card(
        "cpu",
        "CPU",
        (
            ("Model", " / ".join(model_names) or UNKNOWN),
            ("Architecture", architecture),
            ("Topology", f"{len(packages)} packages · {len(cores)} cores · {len(logical)} logical"),
            ("Process visibility", f"{visible} of {len(logical)} logical CPUs"),
            ("CPU quota", _cpu_quota(cgroup)),
            ("NUMA", f"{len(numa_nodes)} nodes"),
            ("Frequency", frequency_range),
            ("Governor", text(cpu.get("governor"))),
            ("ISA", isa),
            ("Thermal zone maximum", temperature(max(thermal_values)) if thermal_values else UNKNOWN),
            *hardware_rows,
        ),
        tuple((tables if detailed else tables[:1]) if show_tables else ()),
    )


def _memory_card(memory: Mapping[str, Any], detailed: bool, show_tables: bool, cgroup: Mapping[str, Any]) -> Card:
    total = number_value(memory.get("total_memory"))
    available = number_value(memory.get("available_memory"))
    used = total - available if total is not None and available is not None else None
    dimms = _mappings(memory.get("dimms"))
    populated = [item for item in dimms if item.get("present") is True]
    shown = _limited(populated, detailed, 8)
    dimm_rows = tuple(
        (
            text(item.get("locator")),
            text(item.get("bank_locator")),
            bytes_value(item.get("size")),
            f"{item['speed_mts']} MT/s" if integer_value(item.get("speed_mts")) is not None else UNKNOWN,
            text(item.get("manufacturer")),
            text(item.get("part_number")),
        )
        for item in shown
    )
    tables: Tuple[DetailTable, ...] = ()
    if dimm_rows and show_tables:
        tables = (
            DetailTable(
                "Populated DIMMs",
                ("Slot", "Bank", "Size", "Speed", "Vendor", "Part number"),
                dimm_rows,
                len(populated) - len(shown),
            ),
        )
    if detailed:
        module_rows = tuple(
            (
                text(item.get("locator")),
                text(item.get("memory_type")),
                text(item.get("form_factor")),
                text(item.get("rank")),
                f"{text(item.get('data_width'))} / {text(item.get('total_width'))}",
                f"{item['configured_speed_mts']} MT/s" if item.get("configured_speed_mts") is not None else UNKNOWN,
                f"{item['configured_voltage_mv']} mV" if item.get("configured_voltage_mv") is not None else UNKNOWN,
                _joined([item.get("type_detail"), item.get("edac_mode"), item.get("device_width")], " · "),
            )
            for item in populated
        )
        if module_rows:
            tables += (
                DetailTable(
                    "DIMM configuration",
                    ("Slot", "Type", "Form", "Ranks", "Data / total bits", "Configured", "Voltage", "Mode"),
                    module_rows,
                ),
            )
        identifiers = tuple(
            (text(item.get("locator")), text(item.get("serial")), text(item.get("asset_tag")))
            for item in populated
            if item.get("serial") or item.get("asset_tag")
        )
        if identifiers:
            tables += (DetailTable("DIMM identity", ("Slot", "Serial", "Asset tag"), identifiers),)
        numa = _mappings(memory.get("numa_memory"))
        if numa:
            tables += (
                DetailTable(
                    "NUMA memory",
                    ("Node", "Total", "Free", "Available"),
                    tuple(
                        (
                            text(item.get("node")),
                            bytes_value(item.get("total")),
                            bytes_value(item.get("free")),
                            bytes_value(item.get("available")),
                        )
                        for item in numa
                    ),
                ),
            )
        empty = [item for item in dimms if item.get("present") is False]
        if empty:
            tables += (
                DetailTable(
                    "Unpopulated slots",
                    ("Slot", "Bank"),
                    tuple((text(item.get("locator")), text(item.get("bank_locator"))) for item in empty),
                ),
            )
    inventory_rows: List[Tuple[str, str]] = []
    inventory_source = memory.get("dimm_inventory_source")
    if inventory_source:
        expected = text(memory.get("reported_slot_count"))
        complete = memory.get("reported_slots_complete")
        coverage = (
            "complete against firmware report"
            if complete is True
            else "partial"
            if complete is False
            else "completeness unknown"
        )
        inventory_rows.append(
            ("Slot inventory", f"{inventory_source} · {len(dimms)} observed · {expected} reported · {coverage}")
        )
    if memory.get("reported_array_error_correction"):
        inventory_rows.append(("Firmware ECC report", text(memory.get("reported_array_error_correction"))))
    if detailed and (memory.get("reported_array_location") or memory.get("reported_array_max_capacity") is not None):
        tables += (
            DetailTable(
                "Firmware memory array report",
                ("Location", "Maximum capacity", "Error correction"),
                (
                    (
                        text(memory.get("reported_array_location")),
                        bytes_value(memory.get("reported_array_max_capacity")),
                        text(memory.get("reported_array_error_correction")),
                    ),
                ),
            ),
        )
    if detailed:
        controllers = _mappings(memory.get("controllers"))
        if controllers:
            tables += (
                DetailTable(
                    "EDAC controllers (counters since reset)",
                    ("ID", "Name", "Capacity", "NUMA", "PCI", "Corrected", "Uncorrected"),
                    tuple(
                        (
                            text(item.get("index")),
                            text(item.get("name")),
                            bytes_value(item.get("capacity")),
                            text(item.get("numa_node")),
                            pci_address(item.get("pci_address")),
                            text(item.get("corrected_errors")),
                            text(item.get("uncorrected_errors")),
                        )
                        for item in controllers
                    ),
                ),
            )
        relations = tuple(
            (text(item.get("locator")), text(item.get("controller_index")), text(item.get("numa_node")))
            for item in dimms
            if item.get("controller_index") is not None
        )
        if relations:
            tables += (DetailTable("DIMM controller placement", ("Slot", "Controller", "NUMA"), relations),)
    return Card(
        "memory",
        "Memory",
        (
            ("Host total", bytes_value(total)),
            ("Cgroup limit", _memory_limit(cgroup)),
            ("Cgroup current", bytes_value(cgroup.get("memory_current"))),
            ("Used / available", f"{bytes_value(used)} / {bytes_value(available)}"),
            ("Technology", text(memory.get("memory_type"))),
            (
                "Configured speed",
                f"{memory['configured_speed_mts']} MT/s"
                if integer_value(memory.get("configured_speed_mts")) is not None
                else UNKNOWN,
            ),
            (
                "DIMM population",
                f"{_integer(memory.get('populated_dimms'), len(populated))} of {_integer(memory.get('dimm_count'), len(dimms))} slots",
            ),
            *inventory_rows,
        ),
        tables,
    )


def _accelerator_card(accelerators: Mapping[str, Any], show_tables: bool) -> Card:
    devices = _mappings(accelerators.get("devices"))
    visible = sum(item.get("visible_to_current_process") is True for item in devices)
    physical = [item for item in devices if not item.get("parent_uuid")]
    kinds = Counter(enum_text(ACCELERATOR_KINDS, item.get("kind")) for item in physical)
    breakdown = " · ".join(f"{count} {kind}" for kind, count in kinds.items()) or "No accelerators detected"
    if len(physical) < len(devices):
        breakdown += f" · {len(devices) - len(physical)} MIG instances"
    rows = tuple(
        (
            str(item.get("id", index)),
            enum_text(ACCELERATOR_KINDS, item.get("kind")),
            text(item.get("name")) + (" (MIG)" if item.get("parent_uuid") else ""),
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
    columns: Tuple[str, ...]
    rows: Tuple[Tuple[str, ...], ...]
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
    tables: List[DetailTable] = [DetailTable("Interfaces", columns, rows, len(source) - len(shown))]
    if detailed:
        fields = (
            ("device_name", "Device"),
            ("vendor", "PCI vendor ID"),
            ("driver", "Driver"),
            ("driver_version", "Driver version"),
            ("firmware_version", "Firmware"),
            ("permanent_mac", "Permanent address"),
            ("interface_kind", "Interface kind"),
            ("bond_mode", "Bond mode"),
            ("vlan_id", "VLAN ID"),
            ("vlan_parent", "VLAN parent"),
            ("master", "Master"),
            ("mtu", "MTU (bytes)"),
            ("duplex", "Duplex"),
            ("physical_port_name", "Physical port"),
            ("numa_node", "NUMA node"),
            ("interface_index", "Interface index"),
        )
        hardware_rows = tuple(
            (text(item.get("name")), label, text(item.get(key)))
            for item in shown
            for key, label in fields
            if text(item.get(key)) != UNKNOWN
        ) + tuple(
            (text(item.get("name")), "Carrier", yes_no(item.get("carrier"))) for item in shown if "carrier" in item
        )
        if hardware_rows:
            tables.append(
                DetailTable("Interface hardware and configuration", ("Interface", "Field", "Value"), hardware_rows)
            )
    if detailed:
        autoneg = tuple(
            (text(item.get("name")), "Auto-negotiation", yes_no(item.get("autonegotiation")))
            for item in shown
            if "autonegotiation" in item
        )
        if autoneg:
            tables.append(DetailTable("Link negotiation", ("Interface", "Field", "Value"), autoneg))
        modes = tuple(
            (
                text(item.get("name")),
                _joined(item.get("supported_link_modes"), "\n"),
                _joined(item.get("advertised_link_modes"), "\n"),
                _joined(item.get("peer_link_modes"), "\n"),
            )
            for item in shown
            if item.get("supported_link_modes") or item.get("advertised_link_modes") or item.get("peer_link_modes")
        )
        if modes:
            tables.append(
                DetailTable(
                    "Link modes (capability / advertisements)",
                    ("Interface", "Supported", "Advertised", "Peer advertised"),
                    modes,
                )
            )
        links = tuple(
            (
                text(item.get("name")),
                text(item.get("master")),
                _joined(item.get("lower_interfaces")),
                text(item.get("vlan_parent")),
                text(item.get("vlan_id")),
            )
            for item in shown
            if item.get("master") or item.get("lower_interfaces") or item.get("vlan_parent")
        )
        if links:
            tables.append(
                DetailTable(
                    "Interface topology", ("Interface", "Master", "Lower interfaces", "VLAN parent", "VLAN ID"), links
                )
            )
    return Card(
        "network",
        "Network",
        (
            ("Interfaces", f"{len(interfaces)} total · {len(up)} up"),
            ("Process visibility", f"{visible} of {len(interfaces)} interfaces"),
        ),
        tuple(tables),
    )


def _storage_card(storage: Mapping[str, Any], detailed: bool) -> Card:
    devices = _mappings(storage.get("devices"))
    useful = [
        item
        for item in devices
        if (item.get("kind") != 3 and item.get("layer") != "partition") or item.get("mount_point")
    ]
    source = devices if detailed else (useful if useful else devices)
    shown = _limited(source, detailed, 12)
    physical = [item for item in devices if item.get("layer") == "disk"]
    total = sum(
        _integer(item.get("capacity")) for item in (physical if any("layer" in item for item in devices) else useful)
    )
    rows: Tuple[Tuple[str, ...], ...] = tuple(
        (
            text(item.get("name")),
            text(item.get("layer"))
            if item.get("layer") in {"partition", "device-mapper", "md", "virtual"}
            else enum_text(STORAGE_KINDS, item.get("kind")),
            bytes_value(item.get("capacity")),
            text(item.get("fs_type")),
            text(item.get("mount_point")),
            pci_address(item.get("pci_address")),
        )
        for item in shown
    )
    columns: Tuple[str, ...] = ("Name", "Kind", "Capacity", "FS", "Mount", "PCI")
    if any(item.get("model") for item in shown):
        columns += ("Model",)
        rows = tuple((*row, text(item.get("model"))) for row, item in zip(rows, shown))
    tables: List[DetailTable] = [
        DetailTable(
            "Block devices",
            columns,
            rows,
            len(source) - len(shown),
        )
    ]
    if detailed:
        fields = (
            ("model", "Model"),
            ("vendor", "Vendor"),
            ("serial", "Serial"),
            ("firmware_revision", "Firmware"),
            ("wwid", "WWID"),
            ("transport", "Transport"),
            ("controller_name", "PCI controller"),
            ("numa_node", "NUMA node"),
            ("scheduler", "I/O scheduler"),
            ("mapper_name", "Mapper name"),
            ("mapper_uuid", "Mapper UUID"),
            ("raid_level", "RAID level"),
            ("raid_state", "RAID state"),
            ("raid_disks", "RAID members"),
            ("raid_degraded", "RAID degraded count"),
            ("logical_block_size", "Logical block (bytes)"),
            ("physical_block_size", "Physical block (bytes)"),
            ("minimum_io_size", "Minimum I/O (bytes)"),
            ("optimal_io_size", "Optimal I/O (bytes)"),
        )
        hardware_rows = tuple(
            (text(item.get("name")), label, text(item.get(key)))
            for item in shown
            for key, label in fields
            if text(item.get(key)) != UNKNOWN
        ) + tuple(
            (text(item.get("name")), label, yes_no(item.get(key)))
            for item in shown
            for key, label in (("rotational", "Rotational"), ("read_only", "Read only"), ("removable", "Removable"))
            if key in item
        )
        if hardware_rows:
            tables.append(
                DetailTable("Storage hardware and configuration", ("Device", "Field", "Value"), hardware_rows)
            )
    if detailed:
        relations = tuple(
            (
                text(item.get("name")),
                text(item.get("layer")),
                text(item.get("parent")),
                text(item.get("partition_number")),
                _joined(item.get("slaves")),
            )
            for item in shown
            if item.get("parent") or item.get("slaves") or item.get("mapper_name") or item.get("raid_level")
        )
        if relations:
            tables.append(
                DetailTable(
                    "Block topology", ("Device", "Layer", "Partition parent", "Partition", "Lower devices"), relations
                )
            )
        mounts = _mappings(storage.get("mounts"))
        if mounts:
            tables.append(
                DetailTable(
                    "Mounts (current namespace)",
                    ("ID", "Device/source", "Filesystem", "Mount point", "FS root", "Read only"),
                    tuple(
                        (
                            text(item.get("mount_id")),
                            text(item.get("block_device") or item.get("source")),
                            text(item.get("filesystem")),
                            text(item.get("path")),
                            text(item.get("root")),
                            yes_no(item.get("read_only")),
                        )
                        for item in mounts
                    ),
                )
            )
    tables.extend(storage_health_tables(storage, detailed))
    return Card(
        "storage",
        "Storage",
        (("Devices", f"{len(useful)} physical/mounted · {len(devices)} total"), ("Raw capacity", bytes_value(total))),
        tuple(tables),
    )


def _software_card(software: Mapping[str, Any]) -> Card:
    drivers = _mappings(software.get("drivers"))
    runtimes = _mappings(software.get("runtimes"))
    compilers = _mappings(software.get("compilers"))
    cuda = _mapping(software.get("cuda"))
    rocm = _mapping(software.get("rocm"))
    level_zero = _mapping(software.get("level_zero"))
    libraries = _mappings(software.get("libraries"))
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
    if libraries:
        tables.append(
            DetailTable(
                "Libraries",
                ("Name", "Kind", "Version", "Path"),
                tuple(
                    (text(item.get("name")), text(item.get("kind")), text(item.get("version")), text(item.get("path")))
                    for item in libraries
                ),
            )
        )
    return Card(
        "software",
        "Software",
        (
            ("CUDA", f"{text(cuda.get('version'))} · driver {text(cuda.get('driver_version'))}"),
            ("CUDA home", text(cuda.get("home"))),
            ("ROCm", text(rocm.get("version"))),
            ("ROCm home", text(rocm.get("rocm_path"))),
            ("Level Zero", text(level_zero.get("version"))),
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
            ("CPU quota", _cpu_quota(cgroup)),
            ("Memory limit", _memory_limit(cgroup)),
            ("Memory current", bytes_value(cgroup.get("memory_current"))),
            ("CPU set", text(cpuset.get("cpus_effective"))),
            ("Memory nodes", text(cpuset.get("mems_effective"))),
            ("Visible resources", f"{visible_cpu_count} CPUs · {visible_accelerator_count} accelerators"),
        ),
    )


def build(
    snapshot: Mapping[str, Any],
    compact: bool = False,
    sections: Optional[List[str]] = None,
    sources: bool = False,
) -> DisplayModel:
    """Build a resilient presentation model from a public Sysal JSON snapshot."""
    info = _mapping(snapshot.get("info"))
    platform = _mapping(info.get("platform"))
    hostname = text(_mapping(platform.get("host")).get("hostname"))
    detailed = bool(sections)
    show_tables = not compact or detailed
    cgroup = _mapping(_mapping(info.get("execution")).get("cgroup"))

    def execution_card() -> Card:
        visible_cpu_count = sum(
            item.get("visible_to_current_process") is True
            for item in _mappings(_mapping(info.get("cpu")).get("logical_cpus"))
        )
        visible_accelerator_count = sum(
            item.get("visible_to_current_process") is True
            for item in _mappings(_mapping(info.get("accelerators")).get("devices"))
        )
        return _execution_card(_mapping(info.get("execution")), visible_cpu_count, visible_accelerator_count)

    builders: Dict[str, Callable[[], Card]] = {
        "system": lambda: _system_card(platform, _mapping(info.get("pci")), detailed),
        "cpu": lambda: _cpu_card(
            _mapping(info.get("cpu")),
            detailed,
            show_tables,
            cgroup,
            text(_mapping(platform.get("architecture")).get("name")),
        ),
        "memory": lambda: _memory_card(_mapping(info.get("memory")), detailed, show_tables, cgroup),
        "accelerators": lambda: _accelerator_card(_mapping(info.get("accelerators")), show_tables),
        "network": lambda: _network_card(_mapping(info.get("network")), detailed),
        "storage": lambda: _storage_card(_mapping(info.get("storage")), detailed),
        "software": lambda: _software_card(_mapping(info.get("software"))),
        "execution": execution_card,
        "topology": lambda: topology_card(info),
        "sensors": lambda: sensors_card(info),
        "health": lambda: health_card(info),
    }
    wanted = (
        tuple(section for section in SECTIONS if section in sections)
        if sections
        else (
            SECTIONS[:4]
            if compact
            else tuple(section for section in SECTIONS if section not in {"topology", "sensors", "health"})
        )
    )
    cards = tuple(builders[section]() for section in wanted)
    if sections is None and has_findings(info):
        cards += (health_card(info, detailed=False),)
    if sources:
        cards = tuple(with_sources(card, _mapping(snapshot.get("meta")), info) for card in cards)
    warnings = tuple(str(item) for item in _items(snapshot.get("warnings")) if item)
    meta = _mapping(snapshot.get("meta"))
    footer_parts = []
    if text(meta.get("sysal_version")) != UNKNOWN:
        footer_parts.append(f"Sysal {text(meta.get('sysal_version'))}")
    duration = number_value(meta.get("collect_duration"))
    if duration is not None:
        footer_parts.append(f"collected in {duration * 1000:.0f} ms")
    return DisplayModel("SystemCard", hostname, tuple(cards), warnings, " · ".join(footer_parts))
