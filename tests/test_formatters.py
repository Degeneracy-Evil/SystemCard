from systemcard.formatters import UNKNOWN, bytes_value, text


def test_text_uses_a_consistent_unknown_marker() -> None:
    assert text(None) == UNKNOWN
    assert text("") == UNKNOWN
    assert text("ready") == "ready"


def test_bytes_value_formats_binary_units() -> None:
    assert bytes_value(None) == UNKNOWN
    assert bytes_value(1024**3) == "1.0 GiB"
