"""Unit tests for app.services.project_service."""

import pytest

from app.core.project_isolation.exceptions import InvalidProjectIdError
from app.services.project_service import ProjectService


def test_validate_normalizes_and_confirms_valid_project_id():
    service = ProjectService()

    result = service.validate("Demo-Project")

    assert result == {"project_id": "demo-project", "valid": True}


def test_validate_raises_for_invalid_project_id():
    service = ProjectService()
    with pytest.raises(InvalidProjectIdError):
        service.validate("!!not valid!!")


def test_resource_names_derives_isolated_names():
    service = ProjectService()

    result = service.resource_names("Demo-Project")

    assert result["project_id"] == "demo-project"
    assert "demo-project" in result["mongodb_database"]
    assert "demo-project" in result["chromadb_collection"]
