from uuid import uuid4

import pytest

from src.projects.domain.entities import Project, ProjectStage
from src.projects.domain.vo import ProjectKey, ProjectStatus
from src.shared.utils.time import current_datetime


@pytest.fixture
def project_factory():

    def _make_project(**kwargs):
        name = kwargs.pop("name", None)
        key = kwargs.pop("key", None)
        created_by = kwargs.pop("created_by", uuid4())

        if name is None:
            name = "Test project"
        if key is None:
            key = ProjectKey("TESTPRJ")

        return Project(
            id=kwargs.pop("id", uuid4()),
            created_at=kwargs.pop("created_at", current_datetime()),
            updated_at=kwargs.pop("updated_at", current_datetime()),
            deleted_at=kwargs.pop("deleted_at", None),
            name=name,
            key=key,
            description=kwargs.pop("description", None),
            counterparty_id=kwargs.pop("counterparty_id", uuid4()),
            status=kwargs.pop("status", ProjectStatus.ACTIVE),
            owner_id=created_by,
            created_by=created_by,
            current_stage_id=kwargs.pop("current_stage_id", None),
            stages=kwargs.pop("stages", []),
        )

    return _make_project


@pytest.fixture
def stage_factory():

    def _make_stage(**kwargs) -> ProjectStage:
        name = kwargs.pop("name", "Test stage")
        order = kwargs.pop("execution_order", 1)

        if not name.strip():
            name = "Test stage"

        return ProjectStage(
            project_id=kwargs.pop("project_id", uuid4()),
            name=name,
            order=max(order, 1),
            status=kwargs.pop("status", ProjectStatus.ACTIVE),
            planned_start=kwargs.pop("planned_start", None),
            planned_end=kwargs.pop("planned_end", None),
            started_at=kwargs.pop("started_at", None),
            completed_at=kwargs.pop("completed_at", None),
            responsible_id=kwargs.pop("responsible_id", None),
            description=kwargs.pop("description", None),
            completion_criteria=kwargs.pop("completion_criteria", []),
        )

    return _make_stage
