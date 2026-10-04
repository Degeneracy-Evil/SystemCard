"""Present cpu facts from a public Sysal snapshot."""

from typing import Any, Counter, Dict, List, Mapping, Optional, Tuple, Union

from systemcard.collection_status import inventory_known
from systemcard.formatters import (
    UNKNOWN,
    bytes_value,
    cpu_list,
    enum_text,
    frequency,
    temperature,
    text,
    yes_no,
)
from systemcard.presentation_types import Card, DetailTable
from systemcard.resource_limits import cpu_quota
from systemcard.schema import (
    integer_value,
    number_value,
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


def _frequency_configuration(policies: List[Mapping[str, Any]]) -> DetailTable:
    """Group identical configuration; keep variable current reports as a range."""
    groups: Dict[
        Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], str, str, str],
        List[Mapping[str, Any]],
    ] = {}
    for policy in policies:
        configuration = (
            integer_value(policy.get("hardware_min_frequency")),
            integer_value(policy.get("hardware_max_frequency")),
            integer_value(policy.get("scaling_min_frequency")),
            integer_value(policy.get("scaling_max_frequency")),
            integer_value(policy.get("base_frequency")),
            text(policy.get("driver")),
            text(policy.get("governor")),
            text(policy.get("energy_performance_preference")),
        )
        groups.setdefault(configuration, []).append(policy)
    rows: List[Tuple[str, ...]] = []
    for (hw_min, hw_max, policy_min, policy_max, base, driver, governor, preference), members in groups.items():
        readings = [integer_value(item.get("scaling_current_frequency")) for item in members]
        known = [value for value in readings if value is not None and value >= 0]
        reported = UNKNOWN
        if known:
            reported = frequency(min(known))
            if min(known) != max(known):
                reported += " - " + frequency(max(known))
            if len(known) != len(members):
                reported += f" (known {len(known)}/{len(members)})"
        rows.append(
            (
                cpu_list([item.get("index") for item in members]),
                cpu_list([number for item in members for number in _items(item.get("related_cpus"))]),
                frequency(hw_min),
                frequency(hw_max),
                frequency(policy_min),
                frequency(policy_max),
                frequency(base),
                reported,
                driver,
                governor,
                preference,
            )
        )
    return DetailTable(
        "Frequency configuration (kernel reports)",
        (
            "Policies",
            "Related CPUs",
            "HW min",
            "HW max",
            "Policy min",
            "Policy max",
            "Base",
            "Reported range",
            "Driver",
            "Governor",
            "Energy preference",
        ),
        tuple(rows),
    )


def _cpu_hardware_tables(cpu: Mapping[str, Any], logical: List[Mapping[str, Any]]) -> List[DetailTable]:
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
        tables.append(DetailTable("Identification", ("CPUs", "Field", "Value"), rows, group_by=0))
    if features:
        tables.append(
            DetailTable(
                "Kernel capabilities",
                ("CPUs", "Features"),
                tuple((cpu_list(ids), " ".join(flags)) for flags, ids in features.items()),
            )
        )
    policies = _mappings(cpu.get("frequency_policies"))
    if policies:
        tables.append(_frequency_configuration(policies))
    return tables


def cpu_card(
    cpu: Mapping[str, Any],
    detailed: bool,
    cgroup: Mapping[str, Any],
    architecture: str,
    meta: Optional[Mapping[str, Any]] = None,
) -> Card:
    packages = _mappings(cpu.get("packages"))
    logical = _mappings(cpu.get("logical_cpus"))
    visible = sum(item.get("visible_to_current_process") is True for item in logical)
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
            text(item.get("physical_cores")),
            text(item.get("logical_threads")),
            frequency(item.get("base_frequency")),
            frequency(item.get("max_frequency")),
        )
        for index, item in enumerate(packages)
    )

    cache_counts: Counter[Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]] = Counter()
    for item in _mappings(cpu.get("caches")):
        cache_counts[
            (
                integer_value(item.get("level")),
                integer_value(item.get("type")),
                integer_value(item.get("size")),
                integer_value(item.get("ways")),
                integer_value(item.get("line_size")),
            )
        ] += 1
    cache_rows = tuple(
        (
            f"L{level}" if level is not None else UNKNOWN,
            enum_text(CACHE_TYPES, kind),
            bytes_value(size),
            text(ways),
            bytes_value(line_size),
            str(count),
        )
        for (level, kind, size, ways, line_size), count in sorted(
            cache_counts.items(), key=lambda entry: tuple(-1 if part is None else part for part in entry[0])
        )
    )
    thermal_rows = tuple(
        (text(item.get("type")), text(item.get("name")), temperature(item.get("temp"))) for item in thermals
    )
    tables = [DetailTable("Packages", ("ID", "Model", "Cores", "Threads", "Base", "Max"), package_rows)]
    if cache_rows:
        tables.append(DetailTable("Cache topology", ("Level", "Type", "Size", "Ways", "Line", "Instances"), cache_rows))
    if thermal_rows:
        tables.append(DetailTable("Thermals", ("Sensor", "Zone", "Temperature"), thermal_rows))
    if detailed:
        tables.extend(_cpu_hardware_tables(cpu, logical))
    hardware_rows: List[Tuple[str, str]] = []
    if cpu.get("caches") and all(item.get("shared_cpus") for item in _mappings(cpu.get("caches"))):
        hardware_rows.extend(
            (f"L{level} {enum_text(CACHE_TYPES, kind).lower()} cache", f"{bytes_value(size)} · {count} instances")
            for (level, kind, size, _ways, _line), count in sorted(
                cache_counts.items(), key=lambda entry: tuple(-1 if part is None else part for part in entry[0])
            )
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
        online = str(len(_items(cpu["online_cpu_ids"]))) if isinstance(cpu.get("online_cpu_ids"), list) else UNKNOWN
        present = str(len(_items(cpu["present_cpu_ids"]))) if isinstance(cpu.get("present_cpu_ids"), list) else UNKNOWN
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
    counts = {
        key: str(len(_items(cpu.get(key)))) if inventory_known(meta or {}, "cpu", cpu.get(key)) else UNKNOWN
        for key in ("packages", "cores", "logical_cpus", "numa_nodes")
    }
    visibility = (
        str(visible)
        if logical and all(isinstance(item.get("visible_to_current_process"), bool) for item in logical)
        else UNKNOWN
    )
    rows = (
        ("Model", " / ".join(model_names) or UNKNOWN),
        ("Architecture", architecture),
        (
            "Topology",
            "{} packages · {} cores · {} logical".format(counts["packages"], counts["cores"], counts["logical_cpus"]),
        ),
        ("Process visibility", "{} of {} logical CPUs".format(visibility, counts["logical_cpus"])),
        ("CPU quota", cpu_quota(cgroup)),
        ("NUMA", f"{counts['numa_nodes']} nodes"),
        ("Frequency", frequency_range),
        ("Governor", text(cpu.get("governor"))),
        ("ISA", isa),
        ("Thermal zone maximum", temperature(max(thermal_values)) if thermal_values else UNKNOWN),
        *hardware_rows,
    )
    if detailed:
        rows += (("Thread / cache links", "--section topology"),)
    if not detailed:
        primary = {"Model", "Topology", "Process visibility", "CPU quota", "NUMA", "Frequency", "SMT"}
        rows = tuple((label, value) for label, value in rows if label in primary or label.endswith(" cache"))
    return Card("cpu", "CPU", rows, tuple(tables) if detailed else ())
