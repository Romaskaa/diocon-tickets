from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.tasks.domain.acl import (
    can_archive_task,
    can_assign_task,
    can_create_task,
    can_edit_task,
    can_move_status,
    can_request_review,
    can_review_task,
)
from src.tasks.domain.vo import TaskStatus

from .helpers import make_task


class TestCanCreateTask:

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN]
    )
    def test_internal_user_can_create_task(self, user_role):
        """
        Внутренние пользователи могут создавать задачи
        """

        permission = can_create_task(user_role)

        assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.CUSTOMER,
            UserRole.CUSTOMER_ADMIN,
            UserRole.FINANCE,
            UserRole.ACCOUNT_MANAGER
        ]
    )
    def test_forbidden_user_cannot_create_task(self, user_role):
        """
        Клиенты, финансовые менеджеры и менеджеры по работе с клиентами
        не могут создавать задачи.
        """

        permission = can_create_task(user_role)

        assert permission.allowed is False
        assert "task can only be created by" in permission.reason.lower()


class TestCanEditTask:

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN],
    )
    def test_creator_with_allowed_role_can_edit_task(self, user_role):
        """
        Фактический создатель может редактировать задание
        """

        user_id = uuid4()
        task = make_task(created_by=user_id)

        permission = can_edit_task(
            task=task, user_id=user_id, user_role=user_role
        )

        assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN],
    )
    def test_assignee_can_edit_task(self, user_role):
        """
        Исполнитель задачи может редактировать
        """

        user_id = uuid4()
        task = make_task(assignee_id=user_id)

        permission = can_edit_task(task=task, user_id=user_id, user_role=user_role)

        assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.FINANCE, UserRole.ACCOUNT_MANAGER],
    )
    def test_assignee_with_forbidden_role_cannot_edit_task(self, user_role):
        """
        Исполнитель с неподходящей ролью не может редактировать задание
        """

        user_id = uuid4()
        task = make_task(assignee_id=user_id)

        permission = can_edit_task(task=task, user_id=user_id, user_role=user_role)

        assert permission.allowed is False
        assert "do not have permission to edit this task" in permission.reason.lower()

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN],
    )
    def test_stranger_with_allowed_role_cannot_edit_task(self, user_role):
        """
        Посторонний пользователь с разрешённой ролью не может редактировать задание
        """

        task = make_task()

        permission = can_edit_task(task=task, user_id=uuid4(), user_role=user_role)

        assert permission.allowed is False
        assert "you need to be assigned to it or the creator" in permission.reason.lower()

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.FINANCE, UserRole.ACCOUNT_MANAGER],
    )
    def test_forbidden_role_cannot_edit_even_when_creator(self, user_role):
        """
        С неразрешённой ролью нельзя редактировать задачу, даже если
        он фактический создатель
        """

        user_id = uuid4()
        task = make_task(created_by=user_id)

        permission = can_edit_task(task=task, user_id=user_id, user_role=user_role)

        assert permission.allowed is False
        assert "do not have permission to edit this task" in permission.reason.lower()


class TestCanMoveStatus:

    # Тест кейсы для администратора

    @pytest.mark.parametrize("new_status", list(TaskStatus))
    def test_admin_can_move_any_statuses(self, new_status):
        """
        Администратор может ставить любой статус
        """

        task = make_task()

        permission = can_move_status(
            task=task,
            new_status=new_status,
            user_id=uuid4(),
            user_role=UserRole.ADMIN,
        )

        assert permission.allowed is True

    # Тест кейсы для проверяющего

    @pytest.mark.parametrize("new_status", [TaskStatus.DONE, TaskStatus.IN_PROGRESS])
    def test_reviewer_can_approve_or_reject(self, new_status):
        """
        Ответственный за задачу может согласовывать или отклонять
        """

        user_id = uuid4()
        task = make_task(status=TaskStatus.TO_REVIEW, reviewer_id=user_id)

        permission = can_move_status(
            task=task, new_status=new_status, user_id=user_id, user_role=UserRole.SUPPORT_MANAGER
        )

        assert permission.allowed is True

    @pytest.mark.parametrize("new_status", [
        status for status in TaskStatus if status not in {TaskStatus.DONE, TaskStatus.IN_PROGRESS}
    ])
    def test_reviewer_cannot_move_to_other_statuses(self, new_status):
        """
        Проверяющий не может устанавливать любой статус задачи, кроме
        'завершена' и 'в работе'.
        """

        user_id = uuid4()
        task = make_task(status=TaskStatus.TO_REVIEW, reviewer_id=user_id)

        permission = can_move_status(
            task=task, new_status=new_status, user_id=user_id, user_role=UserRole.SUPPORT_AGENT
        )

        assert permission.allowed is False
        assert "only can move to IN_PROGRESS or DONE status" in permission.reason

    def test_reviewer_cannot_move_task_when_not_review_status(self):
        """
        Проверяющий не может изменить статус задачи, если текущий статус не TO_REVIEW
        """

        user_id = uuid4()
        task = make_task(reviewer_id=user_id)

        permission = can_move_status(
            task=task, new_status=TaskStatus.DONE, user_id=user_id, user_role=UserRole.DEVELOPER
        )

        assert permission.allowed is False

    # Тестовые сценарии для исполнителя

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]
    )
    @pytest.mark.parametrize(
        "new_status",
        [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.TO_REVIEW, TaskStatus.DONE]
    )
    def test_assignee_can_move_to_work_statuses(self, user_role, new_status):
        """
        Исполнитель может перемещать задачу только в рабочие статусы
        """

        user_id = uuid4()
        task = make_task(assignee_id=user_id, status=TaskStatus.TODO)

        permission = can_move_status(
            task=task, new_status=new_status, user_id=user_id, user_role=user_role
        )

        assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]
    )
    @pytest.mark.parametrize("new_status", [TaskStatus.BACKLOG, TaskStatus.TODO])
    def test_assignee_cannot_move_to_todo_or_backlog(self, user_role, new_status):
        """
        Исполнитель не может переместить задачу в бек-лог или открыть для работы
        """

        user_id = uuid4()
        task = make_task(assignee_id=user_id)

        permission = can_move_status(
            task=task, new_status=new_status, user_id=user_id, user_role=user_role
        )

        assert permission.allowed is False
        assert f"role {user_role} cannot move this task to {new_status}" in permission.reason

    @pytest.mark.parametrize(
        "user_role",
        [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]
    )
    def test_non_assignee_cannot_move_status(self, user_role):
        """
        Не исполнитель не может пенять статус задачи
        """

        task = make_task(assignee_id=uuid4(), status=TaskStatus.IN_PROGRESS)

        permission = can_move_status(
            task=task, new_status=TaskStatus.DONE, user_id=uuid4(), user_role=user_role
        )

        assert permission.allowed is False
        assert "not assigner" in permission.reason


class TestCanAssignTask:

    def test_admin_can_assign_any(self):
        """
        Администратор может назначать и переназначать любые задачи
        """

        task = make_task()

        permission = can_assign_task(
            task=task, assignee_role=UserRole.DEVELOPER, user_id=uuid4(), user_role=UserRole.ADMIN
        )

        assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role", [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]
    )
    def test_assign_free_task_success(self, user_role):
        """
        Успешное назначение ещё не назначенной задачи
        """

        task = make_task()

        permission = can_assign_task(
            task=task, assignee_role=UserRole.DEVELOPER, user_id=uuid4(), user_role=user_role
        )

        assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role", [UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]
    )
    @pytest.mark.parametrize(
        "assignee_role", [
            UserRole.DEVELOPER,
            UserRole.SUPPORT_AGENT,
            UserRole.SUPPORT_MANAGER,
            UserRole.ADMIN,
        ]
    )
    def test_reassign_own_task(self, user_role, assignee_role):
        """
        Исполнитель может переназначить свою задачу
        """

        user_id = uuid4()
        task = make_task(assignee_id=user_id)

        permission = can_assign_task(
            task=task, assignee_role=assignee_role, user_id=user_id, user_role=user_role
        )

        assert permission.allowed is True

    def test_cannot_reassign_others_task(self):
        """
        Нельзя переназначить задачу если пользователь не является исполнителем
        """

        task = make_task(assignee_id=uuid4())

        permission = can_assign_task(
            task=task,
            assignee_role=UserRole.DEVELOPER,
            user_id=uuid4(),
            user_role=UserRole.DEVELOPER,
        )

        assert permission.allowed is False
        assert "can only reassign tasks assigned to yourself" in permission.reason

    @pytest.mark.parametrize(
        "assignee_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.FINANCE]
    )
    def test_cannot_assign_to_customer_or_finance(self, assignee_role):
        """
        Нельзя назначить задачу клиенту или финансовому менеджеру
        """

        task = make_task()

        permission = can_assign_task(
            task=task,
            assignee_role=assignee_role,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_MANAGER,
        )

        assert permission.allowed is False
        assert "can only be assigned to internal staff" in permission.reason

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.CUSTOMER,
            UserRole.CUSTOMER_ADMIN,
            UserRole.FINANCE,
            UserRole.ACCOUNT_MANAGER,
        ]
    )
    def test_forbidden_role_cannot_assign(self, user_role):
        """
        Только внутренняя поддержка может назначать задачи
        """

        task = make_task()

        permission = can_assign_task(
            task=task,
            assignee_role=UserRole.SUPPORT_AGENT,
            user_id=uuid4(),
            user_role=user_role,
        )

        assert permission.allowed is False
        assert "only developers or supports can assign" in permission.reason.lower()


class TestCanRequestReview:

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_MANAGER, UserRole.ADMIN])
    def test_admin_or_support_manager_can_request(self, user_role):
        """
        Администратор или менеджер поддержки может запросить ревью для задачи
        """

        task = make_task(status=TaskStatus.IN_PROGRESS)

        permission = can_request_review(
            task=task, reviewer_role=UserRole.SUPPORT_AGENT, user_id=uuid4(), user_role=user_role
        )

        assert permission.allowed is True

    def test_assignee_can_request_review(self):
        """
        Исполнитель может запросить ревью для своей задачи
        """

        user_id = uuid4()
        task = make_task(assignee_id=user_id, status=TaskStatus.IN_PROGRESS)

        permission = can_request_review(
            task=task,
            reviewer_role=UserRole.DEVELOPER,
            user_id=user_id,
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert permission.allowed is True

    def test_non_assignee_cannot_request_review(self):
        """
        Не исполнитель задачи не может запросить ревью
        """

        task = make_task(assignee_id=uuid4(), status=TaskStatus.IN_PROGRESS)

        permission = can_request_review(
            task=task,
            user_id=uuid4(),
            reviewer_role=UserRole.DEVELOPER,
            user_role=UserRole.DEVELOPER
        )

        assert permission.allowed is False
        assert "don't have permission to request review" in permission.reason

    @pytest.mark.parametrize(
        "reviewer_role",
        [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.FINANCE, UserRole.ACCOUNT_MANAGER],
    )
    def test_request_review_only_from_supports_or_developers(self, reviewer_role):
        """
        Запросить ревью задачи можно только у сотрудников поддержки и разработчиков
        """

        user_id = uuid4()
        task = make_task(assignee_id=user_id, status=TaskStatus.IN_PROGRESS)

        permission = can_request_review(
            task=task,
            reviewer_role=reviewer_role,
            user_id=user_id,
            user_role=UserRole.DEVELOPER,
        )

        assert permission.allowed is False
        assert "can request a review only from developers and support staff" in permission.reason


class TestCanReviewTask:

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_MANAGER, UserRole.ADMIN])
    def test_admin_or_support_manager_can_review(self, user_role):
        """
        Администратор или менеджер поддержки могут проверить любую задачу
        """

        task = make_task(status=TaskStatus.TO_REVIEW)

        permission = can_review_task(task=task, user_id=uuid4(), user_role=user_role)

        assert permission.allowed is True

    def test_reviewer_can_review_task(self):
        """
        Ответственный может проверить задачу
        """

        user_id = uuid4()
        task = make_task(status=TaskStatus.TO_REVIEW, reviewer_id=user_id)

        permission = can_review_task(task=task, user_id=user_id, user_role=UserRole.DEVELOPER)

        assert permission.allowed is True

    def test_non_reviewer_cannot_review_task(self):
        """
        Если пользователь не назначен ответственным за задачу,
        то он не может проверить её
        """

        task = make_task(status=TaskStatus.TO_REVIEW, reviewer_id=uuid4())

        permission = can_review_task(task=task, user_id=uuid4(), user_role=UserRole.SUPPORT_AGENT)

        assert permission.allowed is False

    def test_other_cannot_review_task(self):
        """
        Другие пользователи не могут проводить ревью задачи
        """

        task = make_task(status=TaskStatus.TO_REVIEW, reviewer_id=uuid4())

        permission = can_review_task(task=task, user_id=uuid4(), user_role=UserRole.DEVELOPER)

        assert permission.allowed is False


class TestCanArchiveTask:

    def test_admin_can_archive_success(self):
        """
        Админ может переносить задачу в архив
        """

        task = make_task()

        permission = can_archive_task(task=task, user_id=uuid4(), user_role=UserRole.ADMIN)

        assert permission.allowed is True

    def test_creator_can_archive_success(self):
        """
        Фактический создатель задачи может архивировать
        """

        user_id = uuid4()
        task = make_task(created_by=user_id)

        permission = can_archive_task(task=task, user_id=user_id, user_role=UserRole.SUPPORT_AGENT)

        assert permission.allowed is True

    def test_other_user_cannot_archive_task(self):
        """
        Другие пользователи не могут архивировать задачу
        """

        task = make_task(created_by=uuid4())

        permission = can_archive_task(task=task, user_id=uuid4(), user_role=UserRole.SUPPORT_AGENT)

        assert permission.allowed is False
