import json

from src.interface.app import _with_nav
from src.interface.world_state import load_series


def test_nav_is_added_once():
    html = _with_nav('<style></style><div class="topbar-main"></div>', "world")
    assert html.count('<div class="tabs">') == 1
    assert 'href="/logs"' in html
    assert 'href="/"' in html


def test_nav_marks_active_tab():
    html = _with_nav('<div class="topbar-main"></div>', "logs")
    assert '<a href="/logs" class="active">Logs</a>' in html
    assert '<a href="/" class="">World</a>' in html


def test_series_math(tmp_path):
    run_dir = tmp_path / "demo" / "run-1"
    run_dir.mkdir(parents=True)
    for tick, hp, xp, gold in [(0, 5, 0, 1), (2, 3, 10, 4)]:
        payload = {"characters": {"hero": {"stats": {"hp": hp, "xp": xp, "gold": gold}}}}
        (run_dir / f"world_state_{tick}.json").write_text(json.dumps(payload), encoding="utf-8")
    assert load_series(tmp_path, "demo", "run-1")["hero"] == [
        {"tick": 0, "hp": 5, "xp": 0, "gold": 1},
        {"tick": 2, "hp": 3, "xp": 10, "gold": 4},
    ]
