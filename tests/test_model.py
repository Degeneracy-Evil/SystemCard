from systemcard.model import build


def test_build_handles_a_minimal_snapshot() -> None:
    model = build(
        {
            "info": {
                "platform": {"host": {"hostname": "node-1"}, "os": {"name": "Linux"}},
                "cpu": {"packages": [], "logical_cpus": []},
                "memory": {"total_memory": 1024**3},
                "accelerators": {"devices": []},
                "network": {"interfaces": []},
                "storage": {"devices": []},
                "software": {"drivers": [], "runtimes": []},
            },
            "warnings": ["partial collection"],
        }
    )

    assert model.subtitle == "node-1"
    assert len(model.cards) == 8
    assert model.warnings == ("partial collection",)


def test_compact_model_omits_secondary_cards() -> None:
    model = build({"info": {}, "warnings": []}, compact=True)

    assert [card.title for card in model.cards] == ["System", "CPU", "Memory", "Accelerators"]


def test_sections_filters_cards_by_schema_order() -> None:
    snapshot = {
        "info": {
            "platform": {"host": {"hostname": "node"}, "os": {"name": "Linux"}},
            "cpu": {"packages": [], "logical_cpus": []},
            "memory": {"total_memory": 1024**3},
            "accelerators": {"devices": []},
            "network": {"interfaces": []},
            "storage": {"devices": []},
            "software": {"drivers": [], "runtimes": []},
        },
        "warnings": [],
    }

    model = build(snapshot, sections=["software", "cpu", "bogus"])

    assert [card.section for card in model.cards] == ["cpu", "software"]


def test_sections_override_compact_pruning() -> None:
    model = build({"info": {}, "warnings": []}, compact=True, sections=["network"])

    assert [card.section for card in model.cards] == ["network"]


def test_build_exposes_rich_sysal_details() -> None:
    pci = {"domain": 0, "bus": 101, "device": 0, "function": 0}
    snapshot = {
        "info": {
            "platform": {
                "host": {"hostname": "compute-1", "vendor": "Vendor", "product_name": "Server"},
                "os": {"distribution_version": "Linux 1"},
                "kernel": {"release": "6.0"},
                "architecture": {"name": "x86_64", "bits": 64, "byte_order": "little"},
                "firmware": {"bios_vendor": "BIOS", "bios_version": "1.0", "uefi": True},
            },
            "cpu": {
                "packages": [
                    {
                        "id": 0,
                        "model_name": "Fast CPU",
                        "physical_cores": 8,
                        "logical_threads": 16,
                        "base_frequency": 2_000_000_000,
                        "max_frequency": 3_000_000_000,
                    }
                ],
                "cores": [{}] * 8,
                "logical_cpus": [{"visible_to_current_process": True}] * 16,
                "numa_nodes": [{"id": 0}],
                "governor": "performance",
                "isa_extensions": [6, 7],
                "caches": [
                    {"level": 1, "type": 0, "size": 32768, "ways": 8, "line_size": 64},
                    {"level": 1, "type": 0, "size": 32768, "ways": 8, "line_size": 64},
                ],
                "thermal_zones": [{"name": "zone0", "type": "package", "temp": 55000}],
            },
            "memory": {
                "total_memory": 64 * 1024**3,
                "available_memory": 48 * 1024**3,
                "memory_type": "DDR5",
                "configured_speed_mts": 4800,
                "dimm_count": 4,
                "populated_dimms": 2,
                "dimms": [
                    {
                        "present": True,
                        "locator": "A1",
                        "bank_locator": "NODE 0",
                        "size": 32 * 1024**3,
                        "speed_mts": 4800,
                        "manufacturer": "MemoryCo",
                        "part_number": "ABC",
                    },
                    {"present": False, "locator": "A2"},
                ],
            },
            "accelerators": {
                "devices": [
                    {
                        "id": 0,
                        "kind": 0,
                        "name": "GPU",
                        "memory_size": 80 * 1024**3,
                        "pci_address": pci,
                        "nearest_numa_node": 0,
                        "visible_to_current_process": True,
                    }
                ]
            },
            "network": {
                "interfaces": [
                    {
                        "name": "ib0",
                        "state": 0,
                        "speed": 100_000_000_000,
                        "addresses": ["192.0.2.1"],
                        "mac": "00:11:22:33:44:55",
                        "pci_address": pci,
                        "visible_to_current_process": True,
                    }
                ]
            },
            "storage": {
                "devices": [
                    {
                        "name": "nvme0n1",
                        "kind": 0,
                        "capacity": 1024**4,
                        "fs_type": "xfs",
                        "mount_point": "/data",
                        "pci_address": pci,
                    }
                ]
            },
            "software": {
                "cuda": {"version": "13.0", "driver_version": "590", "home": "/opt/cuda"},
                "mpi": {"implementation": "Open MPI", "version": "5.0"},
                "rdma": {"rdma_core_version": "1.0", "ucx_version": "2.0"},
                "compilers": [{"name": "gcc", "version": "14", "path": "/usr/bin/gcc"}],
                "runtimes": [{"name": "cuda", "version": "13.0", "path": "/opt/cuda"}],
                "drivers": [{"name": "nvidia", "version": "590", "loaded": True}],
            },
            "execution": {
                "process": {"comm": "python", "pid": 10, "ppid": 1, "uid": 1000, "gid": 1000},
                "permission": {"is_root": False},
                "cgroup": {"version": 1, "path": "/job"},
                "cpuset": {"cpus_effective": "0-15", "mems_effective": "0"},
                "visible_logical_cpu_ids": list(range(16)),
                "visible_accelerator_ids": [0],
            },
        },
        "warnings": [],
        "meta": {"sysal_version": "0.0.8", "collect_duration": 0.012},
    }

    model = build(
        snapshot,
        sections=["system", "cpu", "memory", "accelerators", "network", "storage", "software", "execution"],
    )

    assert len(model.cards) == 8
    assert model.footer == "Sysal 0.0.8 · collected in 12 ms"
    assert next(card for card in model.cards if card.section == "cpu").tables[1].title == "Cache topology"
    assert next(card for card in model.cards if card.section == "memory").tables[0].rows[0][0] == "A1"
    assert next(card for card in model.cards if card.section == "accelerators").tables[0].rows[0][2] == "GPU"
