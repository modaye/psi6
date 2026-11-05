"""多视图文档标签：增删、交还控件、重排、空态、状态与持久化。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QStackedWidget, QTabWidget
from pytestqt.qtbot import QtBot

from psi6.runtime.config import ConfigStore
from psi6.ui.empty_state import EmptyState
from psi6.ui.tab_view import TabView


def _view(qtbot: QtBot, **kwargs: object) -> TabView:
    tabs = TabView(**kwargs)  # type: ignore[arg-type]
    qtbot.addWidget(tabs)
    return tabs


def _labels(count: int) -> list[QLabel]:
    return [QLabel(f"文档 {index}") for index in range(count)]


def test_add_tab_tracks_keys_titles_and_current(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(3)
    for index, label in enumerate(labels):
        tabs.add_tab(f"doc-{index}", f"标题 {index}", label)

    assert tabs.keys() == ["doc-0", "doc-1", "doc-2"]
    assert tabs.count() == 3
    assert tabs.current_key() == "doc-0"
    assert tabs.title("doc-1") == "标题 1"
    assert tabs.widget("doc-2") is labels[2]
    assert tabs.widget("missing") is None
    assert tabs.title("missing") == ""

    tabs.set_title("doc-1", "改名")
    assert tabs.title("doc-1") == "改名"
    tabs.set_current("doc-2")
    assert tabs.current_key() == "doc-2"


def test_duplicate_key_only_switches_without_inserting(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(2)
    tabs.add_tab("a", "A", labels[0])
    tabs.add_tab("b", "B", labels[1])
    duplicate = QLabel("重复的 A")
    tabs.add_tab("a", "A 又来了", duplicate)

    assert tabs.keys() == ["a", "b"]
    assert tabs.count() == 2
    assert tabs.widget("a") is labels[0]
    assert tabs.current_key() == "a"
    # 重复打开不接管新控件，也不把它塞进页签。
    assert duplicate.parent() is None


def test_close_tab_hands_the_widget_back(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(2)
    tabs.add_tab("a", "A", labels[0])
    tabs.add_tab("b", "B", labels[1])
    closed: list[str] = []
    tabs.tab_closed.connect(closed.append)

    assert tabs.close_tab("a") is True
    assert tabs.keys() == ["b"]
    assert tabs.current_key() == "b"
    assert tabs.widget("a") is None
    # 关闭只是解除父子关系，控件本体交还调用方，不销毁。
    assert labels[0].parent() is None
    assert not labels[0].isVisible()
    assert labels[1].parent() is not None
    assert closed == ["a"]
    assert tabs.close_tab("a") is False


def test_close_all_falls_back_to_empty_state(qtbot: QtBot) -> None:
    tabs = _view(qtbot, empty_title="没有文档", empty_hint="点新建打开")
    labels = _labels(2)
    tabs.add_tab("a", "A", labels[0])
    tabs.add_tab("b", "B", labels[1])
    tabs.close_all()

    assert tabs.count() == 0
    assert tabs.current_key() == ""
    assert tabs.state() == {"keys": [], "current": ""}
    empty = tabs.findChild(EmptyState)
    assert empty is not None
    stack = tabs.findChild(QStackedWidget)
    assert stack is not None
    assert stack.currentWidget() is empty
    qtab = tabs.findChild(QTabWidget)
    assert qtab is not None
    assert qtab.count() == 0
    # 重新打开文档后回到页签页，空态不再占屏。
    tabs.add_tab("c", "C", QLabel("C"))
    assert stack.currentWidget() is qtab


def test_close_request_signal_closes_the_matching_key(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(2)
    tabs.add_tab("a", "A", labels[0])
    tabs.add_tab("b", "B", labels[1])
    qtab = tabs.findChild(QTabWidget)
    assert qtab is not None
    qtab.tabCloseRequested.emit(1)
    assert tabs.keys() == ["a"]


def test_moving_a_tab_keeps_key_order_and_emits(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(3)
    for index, label in enumerate(labels):
        tabs.add_tab(f"doc-{index}", f"标题 {index}", label)
    moves: list[tuple[int, int]] = []
    tabs.tab_moved.connect(lambda source, target: moves.append((source, target)))

    qtab = tabs.findChild(QTabWidget)
    assert qtab is not None
    qtab.tabBar().moveTab(0, 2)

    assert tabs.keys() == ["doc-1", "doc-2", "doc-0"]
    assert moves == [(0, 2)]
    assert tabs.title("doc-0") == "标题 0"


def test_state_reorders_existing_tabs_and_restores_current(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(3)
    for index, label in enumerate(labels):
        tabs.add_tab(f"doc-{index}", f"标题 {index}", label)

    saved = tabs.state()
    assert saved == {"keys": ["doc-0", "doc-1", "doc-2"], "current": "doc-0"}
    saved["keys"] = list(reversed(saved["keys"]))
    saved["current"] = "doc-1"

    other = _view(qtbot)
    other_labels = _labels(3)
    for index, label in enumerate(other_labels):
        other.add_tab(f"doc-{index}", f"标题 {index}", label)
    other.set_state(saved)

    assert other.keys() == ["doc-2", "doc-1", "doc-0"]
    assert other.current_key() == "doc-1"
    assert other.title("doc-2") == "标题 2"


def test_set_state_ignores_unknown_keys_and_keeps_extra_tabs(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(3)
    for index, label in enumerate(labels):
        tabs.add_tab(f"doc-{index}", f"标题 {index}", label)

    tabs.set_state({"keys": ["ghost", "doc-2", "doc-2"], "current": "ghost"})
    # 未知 key 忽略，重复的 key 去重，当前没写进状态的标签追加到末尾。
    assert tabs.keys() == ["doc-2", "doc-0", "doc-1"]
    assert tabs.count() == 3
    # current 指向不存在的 key 时安全跳过，仍停在原来那份文档上。
    assert tabs.current_key() == "doc-0"


def test_set_state_ignores_invalid_payload(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    labels = _labels(2)
    tabs.add_tab("a", "A", labels[0])
    tabs.add_tab("b", "B", labels[1])

    tabs.set_state({"current": "b"})
    tabs.set_state({"keys": "not-a-list", "current": 42})
    tabs.set_state({})
    assert tabs.keys() == ["a", "b"]
    assert tabs.current_key() == "a"


def test_state_returns_a_fresh_snapshot(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    tabs.add_tab("a", "A", QLabel("A"))
    snapshot = tabs.state()
    snapshot["keys"].append("bogus")
    assert tabs.keys() == ["a"]


def test_save_and_restore_state_via_config_store(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    tabs = _view(qtbot, state_file="docs.json")
    labels = _labels(2)
    tabs.add_tab("a", "A", labels[0])
    tabs.add_tab("b", "B", labels[1])
    tabs.set_current("b")
    tabs.save_state(store, "wb")

    assert store.load_data("wb", "docs.json") == {
        "keys": ["a", "b"],
        "current": "b",
    }

    other = _view(qtbot, state_file="docs.json")
    other.add_tab("a", "A", QLabel("A"))
    other.add_tab("b", "B", QLabel("B"))
    assert other.restore_state(store, "wb") is True
    assert other.keys() == ["a", "b"]
    assert other.current_key() == "b"


def test_restore_state_without_file_is_a_noop(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    tabs = _view(qtbot)
    tabs.add_tab("a", "A", QLabel("A"))
    assert tabs.restore_state(store, "wb") is False
    assert tabs.keys() == ["a"]


def test_restore_state_survives_corrupt_json(qtbot: QtBot, tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    path = store.data_path("wb", "tabs.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{broken", encoding="utf-8")

    tabs = _view(qtbot)
    tabs.add_tab("a", "A", QLabel("A"))
    assert tabs.restore_state(store, "wb") is False
    assert tabs.keys() == ["a"]


def test_signals_fire_for_open_close_move_and_reorder(qtbot: QtBot) -> None:
    tabs = _view(qtbot)
    current: list[str] = []
    layouts: list[bool] = []
    tabs.current_changed.connect(current.append)
    tabs.layout_changed.connect(lambda: layouts.append(True))

    labels = _labels(2)
    tabs.add_tab("a", "A", labels[0])
    tabs.add_tab("b", "B", labels[1])
    tabs.set_current("b")
    tabs.set_state({"keys": ["b", "a"], "current": "a"})
    tabs.close_tab("b")

    assert current[0] == "a"
    assert "b" in current
    assert current[-1] == "a"
    assert len(layouts) >= 4


def test_closable_and_movable_flags_are_forwarded(qtbot: QtBot) -> None:
    tabs = _view(qtbot, closable=False, movable=False)
    qtab = tabs.findChild(QTabWidget)
    assert qtab is not None
    assert qtab.tabsClosable() is False
    assert qtab.isMovable() is False
    # 关闭按钮关掉不影响程序化 close_tab。
    tabs.add_tab("a", "A", QLabel("A"))
    assert tabs.close_tab("a") is True
    assert tabs.count() == 0
