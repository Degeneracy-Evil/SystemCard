"""Kernel storage controllers, protocol devices and their explicit attachments."""

from typing import Any, List, Mapping

from systemcard.formatters import UNKNOWN, pci_address, text
from systemcard.presentation_helpers import joined
from systemcard.presentation_types import DetailTable
from systemcard.schema import integer_value, mapping_items, mapping_value

PCI_STORAGE_CLASSES = {
    0x0100: "SCSI",
    0x0101: "IDE",
    0x0102: "Floppy",
    0x0103: "IPI",
    0x0104: "RAID",
    0x0106: "SATA",
    0x0107: "SAS",
    0x0108: "Non-volatile memory",
    0x0180: "Other storage",
}


def _pci_class(value: object) -> str:
    code = integer_value(value)
    if code is None:
        return UNKNOWN
    if code == 0x010601:
        return "SATA / AHCI"
    if code == 0x010802:
        return "NVMe"
    return PCI_STORAGE_CLASSES.get(code >> 8, f"0x{code:06x}")


def _scsi_address(value: object) -> str:
    address = mapping_value(value)
    return ":".join(text(address.get(key)) for key in ("host", "channel", "target", "lun")) if address else UNKNOWN


def storage_connection_tables(storage: Mapping[str, Any], detailed: bool = False) -> List[DetailTable]:
    tables: List[DetailTable] = []
    controllers = mapping_items(storage.get("controllers"))
    if controllers:
        tables.append(
            DetailTable(
                "PCI storage controller functions",
                ("PCI", "Model", "Class", "Driver", "NUMA"),
                tuple(
                    (
                        pci_address(item.get("pci_address")),
                        text(item.get("model")),
                        _pci_class(item.get("class_code")),
                        text(item.get("driver")),
                        text(item.get("numa_node")),
                    )
                    for item in controllers
                ),
            )
        )
    nvme = mapping_items(storage.get("nvme_controllers"))
    if nvme:
        tables.append(
            DetailTable(
                "NVMe kernel controllers",
                ("Controller", "Model", "Transport", "State", "PCI", "NUMA"),
                tuple(
                    (
                        text(item.get("name")),
                        text(item.get("model")),
                        text(item.get("transport")),
                        text(item.get("state")),
                        pci_address(item.get("pci_address")),
                        text(item.get("numa_node")),
                    )
                    for item in nvme
                ),
            )
        )
    hosts = mapping_items(storage.get("scsi_hosts"))
    if hosts:
        tables.append(
            DetailTable(
                "SCSI kernel hosts (multiple hosts may share a controller)",
                ("Host", "Driver (proc_name)", "State", "PCI", "NUMA", "ATA port"),
                tuple(
                    (
                        f"host{text(item.get('number'))}",
                        text(item.get("proc_name")),
                        text(item.get("state")),
                        pci_address(item.get("pci_address")),
                        text(item.get("numa_node")),
                        text(item.get("ata_port")),
                    )
                    for item in hosts
                ),
            )
        )
    devices = mapping_items(storage.get("devices"))
    namespaces = [(item, mapping_value(item.get("nvme_namespace"))) for item in devices if item.get("nvme_namespace")]
    if namespaces:
        tables.append(
            DetailTable(
                "NVMe namespace attachments (NSID is local to its subsystem)",
                ("Block device", "Namespace ID", "Controllers"),
                tuple(
                    (text(item.get("name")), text(ns.get("id")), joined(ns.get("controllers")))
                    for item, ns in namespaces
                ),
            )
        )
    scsi_devices = [(item, mapping_value(item.get("scsi_device"))) for item in devices if item.get("scsi_device")]
    if scsi_devices:
        tables.append(
            DetailTable(
                "SCSI block devices (H:C:T:L; RAID volumes may be logical)",
                ("Block device", "SCSI address", "Peripheral type", "State"),
                tuple(
                    (
                        text(item.get("name")),
                        _scsi_address(scsi.get("address")),
                        text(scsi.get("peripheral_type")),
                        text(scsi.get("state")),
                    )
                    for item, scsi in scsi_devices
                ),
            )
        )
    if not detailed:
        return tables
    fields = (
        ("serial", "Serial"),
        ("firmware_revision", "Firmware"),
        ("controller_id", "Protocol controller ID"),
        ("address", "Transport address"),
        ("subsystem_nqn", "Subsystem NQN"),
    )
    rows = tuple(
        (text(item.get("name")), label, report)
        for item in nvme
        for key, label in fields
        for report in (text(item.get(key)),)
        if report != UNKNOWN
    )
    if rows:
        tables.append(DetailTable("NVMe controller identity", ("Controller", "Field", "Value"), rows, group_by=0))
    identities = tuple(
        (text(item.get("name")), label, report)
        for item, ns in namespaces
        for key, label in (("nguid", "NGUID"), ("eui", "EUI-64"))
        for report in (text(ns.get(key)),)
        if report != UNKNOWN
    )
    if identities:
        tables.append(
            DetailTable("NVMe namespace identity", ("Block device", "Field", "Value"), identities, group_by=0)
        )
    modes = tuple(
        (f"host{text(item.get('number'))}", text(item.get("supported_mode")), text(item.get("active_mode")))
        for item in hosts
        if item.get("supported_mode") or item.get("active_mode")
    )
    if modes:
        tables.append(DetailTable("SCSI host modes", ("Host", "Supported", "Active"), modes))
    return tables
