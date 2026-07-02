from typing import override

import math
from uuid import UUID

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import Inn
from src.iam.domain.entities import Invitation, User
from src.iam.domain.vo import UserRole
from src.notifications.domain.entities import Notification, UserPreference
from src.notifications.domain.vo import NotificationType
from src.products.domain.entities import SoftwareProduct
from src.projects.domain.entities import Project, ProjectMember
from src.projects.domain.vo import ProjectKey, ProjectRole
from src.shared.infra.repos import InMemoryRepository
from src.shared.schemas import Page, Pagination
from src.shared.utils.time import current_datetime
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber
from src.tickets.domain.entities import Comment, Reaction, Ticket
from src.tickets.domain.repos import ReactionStats, TicketFilters
from src.tickets.domain.services import TicketScopes
from src.tickets.domain.vo import CommentType, ReactionType


class InMemoryCounterpartyRepository(InMemoryRepository[Counterparty]):
    async def get_by_email(self, email: str) -> Counterparty | None:
        for entity in self.data.values():
            if entity.email == email:
                return entity
        return None

    async def get_by_inn(self, inn: Inn) -> Counterparty | None:
        for entity in self.data.values():
            if entity.inn == inn:
                return entity
        return None

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        return [entity for entity in self.data.values() if entity.parent_id == counterparty_id]


class InMemoryUserRepository(InMemoryRepository[User]):

    @override
    async def paginate(
            self, params: Pagination, include_roles: list[UserRole] | None = None
    ) -> Page[User]:
        all_users = list(self.data.values())

        if include_roles is not None:
            allowed_roles = set(include_roles)
            filtered_users = [user for user in all_users if user.role in allowed_roles]
        else:
            filtered_users = all_users

        total_items = len(filtered_users)
        sorted_users = sorted(filtered_users, key=lambda user: user.created_at)
        page_items = sorted_users[params.offset:params.offset + params.size]

        return Page.create(
            items=page_items,
            total_items=total_items,
            page=params.page,
            size=params.size,
        )

    async def get_by_email(self, email: str) -> User | None:
        for user in self.data.values():
            if user.email == email:
                return user
        return None

    async def get_customer_admins(self, counterparty_id: UUID) -> list[User]:
        return [
            user for user in self.data.values()
            if user.counterparty_id == counterparty_id and user.role == UserRole.CUSTOMER_ADMIN
        ]


class InMemoryTokenBlacklist:
    def __init__(self) -> None:
        self.data = {}

    async def revoke(self, jti: UUID, user_id: UUID, exp: int, reason: str) -> bool:
        now = int(current_datetime().timestamp())
        ttl = now - exp
        if ttl <= 0:
            return False

        self.data[jti] = {"revoked_at": current_datetime(), "user_id": user_id, "reason": reason}
        return True

    async def is_revoked(self, jti: UUID) -> bool:
        is_exists = self.data.get(jti)
        return bool(is_exists)


class InMemoryInvitationRepository(InMemoryRepository[Invitation]):
    async def get_by_token(self, token: str) -> Invitation | None:
        for invitation in self.data.values():
            if invitation.token == token:
                return invitation
        return None

    async def get_active_by_email_and_role(
            self, email: str, user_role: UserRole
    ) -> Invitation | None:
        for invitation in self.data.values():
            if (
                invitation.email == email
                and invitation.assigned_role == user_role
                and not invitation.is_used
            ):
                return invitation
        return None


class InMemoryMembershipRepository(InMemoryRepository[ProjectMember]):

    @override
    async def paginate(
            self,
            pagination: Pagination,
            project_id: UUID | None = None,
            include_project_roles: list[ProjectRole] | None = None,
    ) -> Page[ProjectMember]:
        all_memberships = list(self.data.values())

        filtered_memberships = [
            membership
            for membership in all_memberships
            if membership.project_id == project_id
            and membership.project_role in include_project_roles
        ]

        total_items = len(filtered_memberships)
        sorted_memberships = sorted(filtered_memberships, key=lambda member: member.created_at)
        page_items = sorted_memberships[pagination.offset:pagination.offset + pagination.size]

        return Page.create(
            items=page_items,
            total_items=total_items,
            page=pagination.page,
            size=pagination.size,
        )

    async def find(self, project_id: UUID, user_id: UUID) -> ProjectMember | None:
        for membership in self.data.values():
            if membership.project_id == project_id and membership.user_id == user_id:
                return membership

        return None

    async def get_by_user(self, user_id: UUID) -> list[ProjectMember]:
        return [
            membership
            for membership in self.data.values()
            if membership.user_id == user_id
        ]


class InMemoryProjectRepository(InMemoryRepository[Project]):

    async def get_by_key(self, key: ProjectKey) -> Project | None:
        for project in self.data.values():
            if project.key == key:
                return project
        return None

    async def get_existing_keys(self, keys: list[str]) -> set[str]:
        existing = set()
        existing_keys = {str(project.key) for project in self.data.values()}
        for key in keys:
            if key in existing_keys:
                existing.add(key)
        return existing

    async def get_membership(self, project_id: UUID, user_id: UUID) -> ProjectMember | None:
        for project in self.data.values():
            if project.id == project_id:
                return next(
                    (
                        membership
                        for membership in project.members
                        if membership.user_id == user_id
                    ), None
                )
        return None


class InMemoryTicketRepository(InMemoryRepository[Ticket]):

    @override
    async def paginate(
            self,
            pagination: Pagination,
            scopes: TicketScopes | None = None,
            filters: TicketFilters | None = None,
    ) -> Page[Ticket]:
        tickets = [ticket for ticket in self.data.values() if not ticket.is_deleted]

        # Ограничение по области видимости
        if scopes is not None:
            if scopes.reporter_id is not None:
                tickets = [
                    ticket for ticket in tickets if ticket.reporter_id == scopes.reporter_id
                ]
            elif scopes.counterparty_id is not None:
                tickets = [
                    ticket
                    for ticket in tickets
                    if ticket.counterparty_id == scopes.counterparty_id
                    or (ticket.project_id is not None and ticket.project_id in scopes.project_ids)
                ]
            elif scopes.project_ids is not None:
                tickets = [
                    ticket
                    for ticket in tickets
                    if ticket.project_id is None or ticket.project_id in scopes.project_ids
                ]

        tickets.sort(key=lambda x: x.created_at)

        return Page.create(tickets, len(tickets), pagination.page, pagination.size)

    async def get_total(
            self, project_id: UUID | None = None, counterparty_id: UUID | None = None
    ) -> int:
        counter = 0
        if project_id is not None:
            for ticket in self.data.values():
                if ticket.project_id == project_id:
                    counter += 1

        if counterparty_id is not None:
            for ticket in self.data.values():
                if ticket.counterparty_id == counterparty_id:
                    counter += 1

        return counter


class InMemoryCommentRepository(InMemoryRepository[Comment]):

    async def get_by_ticket(
            self,
            ticket_id: UUID,
            pagination: Pagination,
            *,
            user_id: UUID | None = None,
            include_notes: bool = False,
            include_internal: bool = False,
    ) -> Page[Comment]:
        if include_notes and user_id is None:
            raise ValueError("User ID required for received NOTE comments")

        filtered = [
            c
            for c in self.data.values()
            if c.ticket_id == ticket_id
            and c.parent_comment_id is None
            and c.deleted_at is None
            and self._is_visible(c, user_id, include_notes, include_internal)
        ]

        filtered.sort(key=lambda c: c.created_at)
        return self._paginate_list(filtered, pagination)

    async def get_replies(
            self,
            parent_comment_id: UUID,
            pagination: Pagination,
            *,
            user_id: UUID | None = None,
            include_notes: bool = False,
            include_internal: bool = False,
    ) -> Page[Comment]:
        if include_notes and user_id is None:
            raise ValueError("User ID required for received NOTE comments")

        filtered = [
            c
            for c in self.data.values()
            if c.parent_comment_id
            == parent_comment_id
            and c.deleted_at is None
            and self._is_visible(c, user_id, include_notes, include_internal)
        ]

        filtered.sort(key=lambda c: c.created_at)
        return self._paginate_list(filtered, pagination)

    @staticmethod
    def _is_visible(
        comment: Comment,
        user_id: UUID | None,
        include_notes: bool,
        include_internal: bool,
    ) -> bool:
        if comment.type == CommentType.PUBLIC:
            return True
        if include_internal and comment.type == CommentType.INTERNAL:
            return True
        return bool(
            include_notes and comment.type == CommentType.NOTE and comment.author_id == user_id
        )

    @staticmethod
    def _paginate_list(items: list[Comment], params: Pagination) -> Page[Comment]:
        total = len(items)
        start = (params.page - 1) * params.size
        end = start + params.size

        return Page(
            page=params.page,
            size=params.size,
            total_items=total,
            total_pages=math.ceil(total / params.size) if total > 0 else 0,
            has_next=end < total,
            has_prev=params.page > 1,
            items=items[start:end],
        )


class InMemoryPreferenceRepository(InMemoryRepository[UserPreference]):

    async def get_for_notification(
            self, user_id: UUID, notification_type: NotificationType
    ) -> UserPreference | None:
        for preference in self.data.values():
            if preference.user_id == user_id and preference.notification_type == notification_type:
                return preference
        return None

    async def get_by_user(self, user_id: UUID) -> list[UserPreference]:
        return [
            preference for preference in self.data.values() if preference.user_id == user_id
        ]


class InMemoryNotificationRepository(InMemoryRepository[Notification]):

    async def get_unread_count(self, user_id: UUID) -> int:
        return sum(
            notification
            for notification in self.data.values()
            if notification.user_id == user_id and not notification.read
        )

    async def get_by_user(
            self, user_id: UUID, pagination: Pagination, unread_only: bool = False
    ) -> Page[Notification]:
        user_notifications = [
            notification
            for notification in self.data.values()
            if notification.user_id == user_id
        ]
        if unread_only:
            user_notifications = [
                user_notification
                for user_notification in user_notifications
                if not user_notification.read
            ]
        total_items = len(user_notifications)
        sorted_users = sorted(user_notifications, key=lambda user: user.created_at)
        page_items = sorted_users[pagination.offset:pagination.offset + pagination.size]

        return Page.create(
            items=page_items,
            total_items=total_items,
            page=pagination.page,
            size=pagination.size,
        )


class InMemoryReactionRepository(InMemoryRepository[Reaction]):

    async def find(
            self, comment_id: UUID, author_id: UUID, reaction_type: ReactionType
    ) -> Reaction | None:
        for reaction in self.data.values():
            if (
                reaction.comment_id == comment_id and
                reaction.author_id == author_id and
                reaction.reaction_type == reaction_type
            ):
                return reaction

        return None

    async def get_reaction_stats(self, comment_ids: list[UUID], user_id: UUID) -> ReactionStats:
        if not comment_ids:
            return ReactionStats(counts={}, user_reactions={})

        target_ids = set(comment_ids)
        counts: dict[UUID, dict[ReactionType, int]] = {}
        user_reactions: dict[UUID, set[ReactionType]] = {}

        for reaction in self.data.values():
            if reaction.deleted_at is not None or reaction.comment_id not in target_ids:
                continue

            if reaction.comment_id not in counts:
                counts[reaction.comment_id] = {}
            if reaction.comment_id not in user_reactions:
                user_reactions[reaction.comment_id] = set()

            counts[reaction.comment_id][reaction.reaction_type] = (
                counts[reaction.comment_id].get(reaction.reaction_type, 0) + 1
            )

            if reaction.author_id == user_id:
                user_reactions[reaction.comment_id].add(reaction.reaction_type)

        return ReactionStats(counts=counts, user_reactions=user_reactions)


class InMemoryProductRepository(InMemoryRepository[SoftwareProduct]):
    ...


class InMemoryTaskRepository(InMemoryRepository[Task]):
    def __init__(self) -> None:
        super().__init__()
        self.sequences: dict[tuple[UUID | None, ...], int] = {}

    async def get_by_number(self, number: TaskNumber) -> Task | None:
        for task in self.data.values():
            if task.number == number:
                return task

        return None

    async def get_next_sequence(
        self, ticket_id: UUID | None = None, project_id: UUID | None = None
    ) -> int:
        key = (ticket_id, project_id)

        if key not in self.sequences:
            self.sequences[key] = 0

        self.sequences[key] += 1

        return self.sequences[key]
