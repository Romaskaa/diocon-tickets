from uuid import UUID

from src.iam.domain.authz import Subject
from src.iam.domain.entities import User
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.domain.repos import UnitOfWork, finalize, get_or_raise_404

from ..domain.authz import ProjectAuthZService
from ..domain.entities import Project
from ..domain.repos import ProjectMemberRepository, ProjectRepository
from ..mappers import map_member_to_response
from ..schemas import ProjectMemberCreate, ProjectMemberResponse


class ProjectMemberService:
    def __init__(
            self,
            uow: UnitOfWork,
            project_repo: ProjectRepository,
            member_repo: ProjectMemberRepository,
            user_repo: UserRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.user_repo = user_repo
        self.project_repo = project_repo
        self.member_repo = member_repo
        self.authz_service = ProjectAuthZService(member_repo)
        self.event_publisher = event_publisher

    async def add_member(
            self, project_id: UUID, data: ProjectMemberCreate, current_subject: Subject
    ) -> ProjectMemberResponse:
        """
        Добавление нового участника в проект.
        """

        project = await get_or_raise_404(self.project_repo.read, project_id, Project)
        invitee = await get_or_raise_404(self.user_repo.read, data.user_id, User)

        permission = await self.authz_service.can_add_member(
            subject=current_subject,
            project=project,
            invitee=invitee,
            target_roles=data.project_roles,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        existing = await self.member_repo.find(project_id, data.user_id)
        if existing is not None:
            raise AlreadyExistsError(f"User with ID {data.user_id} is already a member")

        member = project.create_member(
            user_id=data.user_id,
            project_roles=list(data.project_roles),
            created_by=current_subject.id,
        )
        await self.member_repo.create(member)
        await finalize(self.uow, project, event_publisher=self.event_publisher)

        return map_member_to_response(member)

    async def remove_member(
            self, project_id: UUID, user_id: UUID, current_subject: Subject
    ) -> None:
        """
        Удалить участника из проекта.
        """

        project = await get_or_raise_404(self.project_repo.read, project_id, Project)

        member_to_remove = await self.member_repo.find(project_id, user_id)
        if member_to_remove is None:
            raise NotFoundError(
                f"User with ID {user_id} not a member of the project with ID {project_id}"
            )

        permission = await self.authz_service.can_remove_member(
            subject=current_subject,
            project=project,
            membership_to_remove=member_to_remove,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        member_to_remove.remove(removed_by=current_subject.id)
        await self.member_repo.update(member_to_remove)
        await finalize(self.uow, member_to_remove, event_publisher=self.event_publisher)
