"""Present software facts from a public Sysal snapshot."""

from typing import Any, List, Mapping

from systemcard.formatters import (
    UNKNOWN,
    text,
    yes_no,
)
from systemcard.presentation_helpers import joined
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import (
    mapping_items as _mappings,
)
from systemcard.schema import (
    mapping_value as _mapping,
)


def _tool_summary(items: List[Mapping[str, Any]]) -> str:
    names = [
        " ".join(text(item.get(key)) for key in ("name", "version") if text(item.get(key)) != UNKNOWN) for item in items
    ]
    names = [name for name in names if name]
    result = joined(names[:4], " / ")
    return result + ("; more in --section software" if len(names) > 4 else "")


def software_card(software: Mapping[str, Any]) -> Card:
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
            ("Compilers", _tool_summary(compilers)),
            ("Runtimes", _tool_summary(runtimes)),
            ("Drivers", _tool_summary(drivers)),
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
