from systemcard.formatters import (
    UNKNOWN,
    bit_rate,
    bytes_value,
    enum_text,
    frequency,
    pci_address,
    percent,
    temperature,
    text,
    yes_no,
)


def test_text_uses_a_consistent_unknown_marker() -> None:
    assert text(None) == UNKNOWN
    assert text("") == UNKNOWN
    assert text("ready") == "ready"


def test_bytes_value_formats_binary_units() -> None:
    assert bytes_value(None) == UNKNOWN
    assert bytes_value(1024**3) == "1.0 GiB"


def test_frequency_formats_ghz_and_mhz() -> None:
    assert frequency(2.2e9) == "2.20 GHz"
    assert frequency(200_000_000) == "200 MHz"
    assert frequency(0) == UNKNOWN
    assert frequency(None) == UNKNOWN


def test_percent_formats_a_ratio() -> None:
    assert percent(0.5) == "0.5%"
    assert percent(100) == "100.0%"
    assert percent(-1) == UNKNOWN
    assert percent(None) == UNKNOWN


def test_enum_text_maps_integers_and_falls_back() -> None:
    mapping = {0: "Gpu", 1: "Npu"}
    assert enum_text(mapping, 0) == "Gpu"
    assert enum_text(mapping, 9) == UNKNOWN
    assert enum_text(mapping, "abc") == UNKNOWN


def test_hardware_formatters() -> None:
    assert bit_rate(100_000_000_000) == "100 Gbps"
    assert bit_rate(1_000_000) == "1 Mbps"
    assert bit_rate(1_000) == "1 Kbps"
    assert bit_rate(100) == "100 bps"
    assert bit_rate(0) == UNKNOWN
    assert temperature(42_500) == "42.5 °C"
    assert temperature(None) == UNKNOWN
    assert yes_no(True) == "Yes"
    assert yes_no(False) == "No"
    assert yes_no(None) == UNKNOWN
    assert pci_address({"domain": 0, "bus": 101, "device": 0, "function": 1}) == "0000:65:00.1"
    assert pci_address({"domain": 0}) == UNKNOWN
    assert pci_address(None) == UNKNOWN
