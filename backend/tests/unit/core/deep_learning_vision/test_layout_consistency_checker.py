"""Unit tests for app.core.deep_learning_vision.layout_consistency_checker."""

from app.core.deep_learning_vision.enums import LayoutConsistencyIssueType, VisualRiskLevel
from app.core.deep_learning_vision.layout_consistency_checker import LayoutConsistencyChecker
from app.core.deep_learning_vision.models import BoundingBox, LayoutElement, LayoutSnapshot


def _element(element_id: str, x: int, y: int, width: int, height: int) -> LayoutElement:
    return LayoutElement(element_id=element_id, tag="div", bounds=BoundingBox(x, y, width, height))


def test_check_reports_no_issues_for_clean_layout():
    layout = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10), _element("b", 20, 20, 10, 10)])

    issues = LayoutConsistencyChecker().check(layout, canvas_width=100, canvas_height=100)

    assert issues == []


def test_check_detects_duplicate_element_id():
    layout = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10), _element("a", 20, 20, 10, 10)])

    issues = LayoutConsistencyChecker().check(layout)

    types = {issue.issue_type for issue in issues}
    assert LayoutConsistencyIssueType.DUPLICATE_ELEMENT_ID in types


def test_check_detects_zero_size_element():
    layout = LayoutSnapshot(elements=[_element("a", 0, 0, 0, 10)])

    issues = LayoutConsistencyChecker().check(layout)

    assert len(issues) == 1
    assert issues[0].issue_type == LayoutConsistencyIssueType.ZERO_SIZE_ELEMENT
    assert issues[0].risk_level == VisualRiskLevel.HIGH


def test_check_detects_off_canvas_element_with_canvas_bounds():
    layout = LayoutSnapshot(elements=[_element("a", 90, 0, 20, 10)])

    issues = LayoutConsistencyChecker().check(layout, canvas_width=100, canvas_height=100)

    assert len(issues) == 1
    assert issues[0].issue_type == LayoutConsistencyIssueType.OFF_CANVAS_ELEMENT


def test_check_detects_negative_position_without_canvas_bounds():
    layout = LayoutSnapshot(elements=[_element("a", -5, 0, 10, 10)])

    issues = LayoutConsistencyChecker().check(layout)

    assert len(issues) == 1
    assert issues[0].issue_type == LayoutConsistencyIssueType.OFF_CANVAS_ELEMENT


def test_check_ignores_in_bounds_element_without_canvas_dimensions():
    layout = LayoutSnapshot(elements=[_element("a", 500, 500, 10, 10)])

    issues = LayoutConsistencyChecker().check(layout)

    assert issues == []


def test_check_detects_significant_overlap():
    layout = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10), _element("b", 1, 1, 10, 10)])

    issues = LayoutConsistencyChecker().check(layout)

    overlap_issues = [i for i in issues if i.issue_type == LayoutConsistencyIssueType.OVERLAPPING_ELEMENTS]
    assert len(overlap_issues) == 1
    assert set(overlap_issues[0].element_ids) == {"a", "b"}


def test_check_ignores_incidental_overlap_below_threshold():
    layout = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10), _element("b", 9, 9, 10, 10)])

    issues = LayoutConsistencyChecker().check(layout)

    overlap_issues = [i for i in issues if i.issue_type == LayoutConsistencyIssueType.OVERLAPPING_ELEMENTS]
    assert overlap_issues == []


def test_check_escalates_near_total_overlap_to_high():
    layout = LayoutSnapshot(elements=[_element("a", 0, 0, 10, 10), _element("b", 0, 0, 10, 10)])

    issues = LayoutConsistencyChecker().check(layout)

    overlap_issues = [i for i in issues if i.issue_type == LayoutConsistencyIssueType.OVERLAPPING_ELEMENTS]
    assert len(overlap_issues) == 1
    assert overlap_issues[0].risk_level == VisualRiskLevel.HIGH
