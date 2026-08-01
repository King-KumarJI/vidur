"""Unit tests for app.api.v1.dependencies."""

import pytest

from app.api.v1.dependencies import get_project_id
from app.core.project_isolation import project_scope
from app.core.project_isolation.exceptions import ProjectContextNotSetError


def test_get_project_id_raises_when_no_context_bound():
    with pytest.raises(ProjectContextNotSetError):
        get_project_id()


def test_get_project_id_returns_bound_project_id():
    with project_scope("demo-project"):
        assert get_project_id() == "demo-project"
