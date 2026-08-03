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
    assert len(model.cards) == 7
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
