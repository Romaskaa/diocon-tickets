from ...media.infra.repo import AttachmentMapper
from ...shared.infra.repos import ModelMapper
from ..domain.entities import Comment, Membership, Project, Reaction, Ticket, TicketHistoryEntry
from ..domain.vo import ProjectKey, Tag, TicketNumber
from .models import (
    CommentOrm,
    MembershipOrm,
    ProjectOrm,
    ReactionOrm,
    TicketHistoryEntryOrm,
    TicketOrm,
)

# Маппинг ORM модели тикета в доменную сущность и обратно


class CommentMapper(ModelMapper[Comment, CommentOrm]):
    @staticmethod
    def to_entity(model: CommentOrm) -> Comment:
        return Comment(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            ticket_id=model.ticket_id,
            author_id=model.author_id,
            author_role=model.author_role,
            text=model.text,
            type=model.comment_type,
            parent_comment_id=model.parent_comment_id,
            reply_count=model.reply_count,
            attachments=[
                AttachmentMapper.to_entity(attachment) for attachment in model.attachments
            ],
        )

    @staticmethod
    def from_entity(entity: Comment) -> CommentOrm:
        return CommentOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            ticket_id=entity.ticket_id,
            author_id=entity.author_id,
            author_role=entity.author_role,
            text=entity.text,
            comment_type=entity.type,
            parent_comment_id=entity.parent_comment_id,
            reply_count=entity.reply_count,
            attachments=[
                AttachmentMapper.from_entity(attachment) for attachment in entity.attachments
            ],
        )


class TicketHistoryEntryMapper(ModelMapper[TicketHistoryEntry, TicketHistoryEntryOrm]):
    @staticmethod
    def to_entity(model: TicketHistoryEntryOrm) -> TicketHistoryEntry:
        return TicketHistoryEntry(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            ticket_id=model.ticket_id,
            actor_id=model.actor_id,
            action=model.action,
            old_value=model.old_value,
            new_value=model.new_value,
            description=model.description,
        )

    @staticmethod
    def from_entity(entity: TicketHistoryEntry) -> TicketHistoryEntryOrm:
        return TicketHistoryEntryOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            ticket_id=entity.ticket_id,
            actor_id=entity.actor_id,
            action=entity.action,
            old_value=entity.old_value,
            new_value=entity.new_value,
            description=entity.description,
        )


class TicketMapper(ModelMapper[Ticket, TicketOrm]):
    @staticmethod
    def to_entity(model: TicketOrm) -> Ticket:
        return Ticket(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            project_id=model.project_id,
            counterparty_id=model.counterparty_id,
            product_id=model.product_id,
            created_by_role=model.created_by_role,
            created_by=model.created_by,
            reporter_id=model.reporter_id,
            number=TicketNumber(model.number),
            title=model.title,
            description=model.description,
            status=model.status,
            priority=model.priority,
            assigned_to=model.assigned_to,
            closed_at=model.closed_at,
            tags=[Tag(name=tag["name"], color=tag["color"]) for tag in model.tags],
            attachments=[
                AttachmentMapper.to_entity(attachment) for attachment in model.attachments
            ],
            history=[TicketHistoryEntryMapper.to_entity(entry) for entry in model.history]
        )

    @staticmethod
    def to_preview(model: TicketOrm) -> Ticket:
        return Ticket(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            project_id=model.project_id,
            counterparty_id=model.counterparty_id,
            product_id=model.product_id,
            created_by_role=model.created_by_role,
            created_by=model.created_by,
            reporter_id=model.reporter_id,
            number=TicketNumber(model.number),
            title=model.title,
            description=model.description,
            status=model.status,
            priority=model.priority,
            assigned_to=model.assigned_to,
            closed_at=model.closed_at,
            tags=[Tag(name=tag["name"], color=tag["color"]) for tag in model.tags],
            attachments=[],
            history=[],
        )

    @staticmethod
    def from_entity(entity: Ticket) -> TicketOrm:
        return TicketOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            project_id=entity.project_id,
            counterparty_id=entity.counterparty_id,
            product_id=entity.product_id,
            created_by_role=entity.created_by_role,
            created_by=entity.created_by,
            reporter_id=entity.reporter_id,
            number=entity.number.value,
            title=entity.title,
            description=entity.description,
            status=entity.status,
            priority=entity.priority,
            assigned_to=entity.assigned_to,
            closed_at=entity.closed_at,
            tags=[{"name": tag.name, "color": tag.color} for tag in entity.tags],
            attachments=[
                AttachmentMapper.from_entity(attachment) for attachment in entity.attachments
            ],
            history=[TicketHistoryEntryMapper.from_entity(entry) for entry in entity.history],
        )


# Маппинг ORM модели проекта в доменную сущность и обратно


class MembershipMapper(ModelMapper[Membership, MembershipOrm]):
    @staticmethod
    def to_entity(model: MembershipOrm) -> Membership:
        return Membership(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            project_id=model.project_id,
            user_id=model.user_id,
            project_role=model.project_role,
            added_at=model.added_at,
            added_by=model.added_by,
        )

    @staticmethod
    def from_entity(entity: Membership) -> MembershipOrm:
        return MembershipOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            user_id=entity.user_id,
            project_id=entity.project_id,
            project_role=entity.project_role,
            added_at=entity.added_at,
            added_by=entity.added_by,
        )


class ProjectMapper(ModelMapper[Project, ProjectOrm]):
    @staticmethod
    def to_entity(model: ProjectOrm) -> Project:
        return Project(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            name=model.name,
            description=model.description,
            key=ProjectKey(model.key),
            counterparty_id=model.counterparty_id,
            owner_id=model.owner_id,
            status=model.status,
            memberships=[
                MembershipMapper.to_entity(membership) for membership in model.memberships
            ]
        )

    @staticmethod
    def from_entity(entity: Project) -> ProjectOrm:
        return ProjectOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            name=entity.name,
            key=entity.key.value,
            description=entity.description,
            counterparty_id=entity.counterparty_id,
            owner_id=entity.owner_id,
            status=entity.status,
            memberships=[
                MembershipMapper.from_entity(membership) for membership in entity.memberships
            ]
        )


class ReactionMapper(ModelMapper[Reaction, ReactionOrm]):
    @staticmethod
    def to_entity(model: ReactionOrm) -> Reaction:
        return Reaction(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            comment_id=model.comment_id,
            author_id=model.author_id,
            reaction_type=model.reaction_type,
        )

    @staticmethod
    def from_entity(entity: Reaction) -> ReactionOrm:
        return ReactionOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            comment_id=entity.comment_id,
            author_id=entity.author_id,
            reaction_type=entity.reaction_type,
        )
