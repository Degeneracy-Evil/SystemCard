"""Translate presentation requests into public Sysal domains and policies."""

from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple

if TYPE_CHECKING:
    from systemcard._native import Domain, FilesystemQuery, SensorDevices


class CollectionPlan(NamedTuple):
    domains: List["Domain"]
    filesystems: "FilesystemQuery"
    sensors: "SensorDevices"


def build_plan(scope: str = "default", sections: Optional[List[str]] = None) -> CollectionPlan:
    if scope not in {"default", "basic", "full"}:
        raise ValueError("scope must be one of: default, basic, full")
    from systemcard._native import Domain, FilesystemQuery, SensorDevices

    section_domains: Dict[str, Tuple[Domain, ...]] = {
        "system": (Domain.PLATFORM, Domain.PCI),
        "cpu": (Domain.CPU, Domain.EXECUTION),
        "memory": (Domain.MEMORY, Domain.EXECUTION, Domain.CPU, Domain.PCI),
        "accelerators": (Domain.ACCELERATOR, Domain.EXECUTION, Domain.CPU, Domain.PCI),
        "network": (Domain.NETWORK, Domain.EXECUTION, Domain.CPU),
        "storage": (Domain.STORAGE,),
        "sensors": (Domain.SENSORS,),
        "health": (Domain.SENSORS, Domain.MEMORY, Domain.STORAGE, Domain.PCI, Domain.STORAGE_HEALTH),
        "topology": (Domain.CPU, Domain.MEMORY, Domain.NETWORK, Domain.STORAGE, Domain.PCI, Domain.EXECUTION),
        "software": (Domain.SOFTWARE,),
        "execution": (Domain.EXECUTION, Domain.CPU, Domain.ACCELERATOR),
    }
    domains: List[Domain] = [Domain.PLATFORM]
    if sections:
        for section in sections:
            if section not in section_domains:
                raise ValueError("unknown collection section: " + section)
            for domain in section_domains[section]:
                if domain not in domains:
                    domains.append(domain)
    elif scope == "basic":
        domains.extend((Domain.CPU, Domain.MEMORY, Domain.EXECUTION))
    else:
        domains.extend(
            (
                Domain.CPU,
                Domain.MEMORY,
                Domain.ACCELERATOR,
                Domain.NETWORK,
                Domain.STORAGE,
                Domain.PCI,
                Domain.SOFTWARE,
                Domain.EXECUTION,
                Domain.SENSORS,
                Domain.STORAGE_HEALTH,
            )
        )
    if scope == "full":
        domains.append(Domain.RAW)
    return CollectionPlan(domains, FilesystemQuery.LOCAL, SensorDevices.EXCLUDE_DISPLAY)
