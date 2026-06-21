from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.domain.authz import Subject
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError

from ..domain.authz import ProjectAuthZService
from ..domain.entities import Project
from ..domain.repos import ProjectMembershipRepository, ProjectRepository
from ..mappers import map_membership_to_response
from ..schemas import ProjectMembershipCreate, ProjectMembershipResponse


class ProjectMembershipService:
    def __init__(
            self,
            session: AsyncSession,
            project_repo: ProjectRepository,
            membership_repo: ProjectMembershipRepository,
            user_repo: UserRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.user_repo = user_repo
        self.project_repo = project_repo
        self.membership_repo = membership_repo
        self.authz_service = ProjectAuthZService(membership_repo)
        self.event_publisher = event_publisher

    async def _get_project_or_404(self, project_id: UUID) -> Project:
        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        return project

    async def add_member(
            self, project_id: UUID, data: ProjectMembershipCreate, current_subject: Subject
    ) -> ProjectMembershipResponse:
        """Добавление участника в проект"""

        project = await self._get_project_or_404(project_id)

        invitee = await self.user_repo.read(data.user_id)
        if invitee is None or invitee.is_deleted:
            raise NotFoundError(f"User with ID {data.user_id} not found")

        permission = await self.authz_service.can_add_member(
            subject=current_subject,
            project=project,
            invitee=invitee,
            target_role=data.project_role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        existing = await self.membership_repo.find(project_id, data.user_id)
        if existing is not None:
            raise AlreadyExistsError(f"User with ID {data.user_id} is already a member")

        membership = project.create_membership(
            user_id=data.user_id,
            project_role=data.project_role,
            created_by=current_subject.id,
        )
        await self.membership_repo.create(membership)
        await self.session.commit()

        for event in project.collect_events():
            await self.event_publisher.publish(event)

        return map_membership_to_response(membership)

    async def remove_member(
            self, project_id: UUID, user_id: UUID, current_subject: Subject
    ) -> None:
        """Удаляет участника из проекта"""

        project = await self._get_project_or_404(project_id)

        membership_to_remove = await self.membership_repo.find(project_id, user_id)
        if membership_to_remove is None:
            raise NotFoundError(
                f"User with ID {user_id} not a member of the project with ID {project_id}"
            )

        permission = await self.authz_service.can_remove_member(
            subject=current_subject,
            project=project,
            membership_to_remove=membership_to_remove,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        membership_to_remove.remove(removed_by=current_subject.id)
        await self.membership_repo.update(membership_to_remove)
        await self.session.commit()

        for event in membership_to_remove.collect_events():
            await self.event_publisher.publish(event)
