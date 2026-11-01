from typing import Any, ClassVar, Dict, List

class Domain:
    PLATFORM: ClassVar[Domain]
    CPU: ClassVar[Domain]
    MEMORY: ClassVar[Domain]
    ACCELERATOR: ClassVar[Domain]
    NETWORK: ClassVar[Domain]
    STORAGE: ClassVar[Domain]
    PCI: ClassVar[Domain]
    SOFTWARE: ClassVar[Domain]
    EXECUTION: ClassVar[Domain]
    RAW: ClassVar[Domain]
    SENSORS: ClassVar[Domain]
    STORAGE_HEALTH: ClassVar[Domain]

class FilesystemQuery:
    NONE: ClassVar[FilesystemQuery]
    LOCAL: ClassVar[FilesystemQuery]
    ALL_MOUNTED: ClassVar[FilesystemQuery]

class SensorDevices:
    ALL: ClassVar[SensorDevices]
    EXCLUDE_DISPLAY: ClassVar[SensorDevices]

def collect(
    domains: List[Domain], filesystems: FilesystemQuery = ..., sensors: SensorDevices = ...
) -> Dict[str, Any]: ...
