from src.agents.time_keeper.agent import estimate_output


def test_estimate_output():
    # Conversion is pure; clamping matters.
    assert estimate_output(None, [0, 1, 30, 9999, -5]) == [0, 1, 30, 1440, 0]  # type: ignore[arg-type]
    assert estimate_output(None, []) == []  # type: ignore[arg-type]
