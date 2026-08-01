"""Unit tests for app.core.deep_learning_vision.layout_diff_analyzer."""

from app.core.deep_learning_vision.enums import LayoutChangeType, VisualRiskLevel
from app.core.deep_learning_vision.layout_diff_analyzer import LayoutDiffAnalyzer
from app.core.deep_learning_vision.models import BoundingBox, LayoutElement, LayoutSnapshot


def _element(element_id: str, x: int, y: int, width: int, height: int, text: str = None, tag: str = "div") -> LayoutElement:
    return LayoutElement(element_id=element_id, tag=tag, bounds=BoundingBox(x, y, width, height), text=text)


def test_compare_identical_layouts_reports_no_changes():
    layout = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10)])

    result = LayoutDiffAnalyzer().compare(layout, layout)

    assert result.changes == []
    assert result.risk_level == VisualRiskLevel.LOW


def test_compare_detects_added_element():
    baseline = LayoutSnapshot(elements=[])
    current = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10)])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    assert len(result.changes) == 1
    assert result.changes[0].change_type == LayoutChangeType.ADDED
    assert result.changes[0].element_id == "a"


def test_compare_detects_removed_element():
    baseline = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10)])
    current = LayoutSnapshot(elements=[])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    assert len(result.changes) == 1
    assert result.changes[0].change_type == LayoutChangeType.REMOVED


def test_compare_detects_moved_element():
    baseline = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10)])
    current = LayoutSnapshot(elements=[_element("a", 20, 20, 10, 10)])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    change_types = {c.change_type for c in result.changes}
    assert LayoutChangeType.MOVED in change_types


def test_compare_detects_resized_element():
    baseline = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10)])
    current = LayoutSnapshot(elements=[_element("a", 0, 0, 30, 30)])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    change_types = {c.change_type for c in result.changes}
    assert LayoutChangeType.RESIZED in change_types


def test_compare_detects_modified_text():
    baseline = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10, text="hello")])
    current = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10, text="goodbye")])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    assert len(result.changes) == 1
    assert result.changes[0].change_type == LayoutChangeType.MODIFIED


def test_compare_ignores_sub_tolerance_jitter():
    baseline = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10)])
    current = LayoutSnapshot(elements=[_element("a", 1, 1, 10, 10)])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    assert result.changes == []


def test_compare_classifies_high_risk_for_majority_removed():
    baseline = LayoutSnapshot(
        elements=[_element("a", 0, 0, 10, 10), _element("b", 20, 20, 10, 10)]
    )
    current = LayoutSnapshot(elements=[])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    assert result.risk_level in (VisualRiskLevel.HIGH, VisualRiskLevel.CRITICAL)


def test_changes_of_type_filters_correctly():
    baseline = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10)])
    current = LayoutSnapshot(elements=[_element("a", 30, 30, 10, 10), _element("b", 0, 0, 5, 5)])

    result = LayoutDiffAnalyzer().compare(baseline, current)

    added = result.changes_of_type(LayoutChangeType.ADDED)
    moved = result.changes_of_type(LayoutChangeType.MOVED)
    assert [c.element_id for c in added] == ["b"]
    assert [c.element_id for c in moved] == ["a"]
