from ..media.mappers import map_attachment_to_response
from .domain.entities import Comment, Project, Ticket, TicketHistoryEntry
from .domain.vo import ReactionType
from .schemas import (
    CommentResponse,
    CommentWithReactionsResponse,
    HistoryEntryResponse,
    MembershipResponse,
    ProjectResponse,
    Tag,
    TicketPreview,
    TicketResponse,
)


def map_ticket_to_preview(ticket: Ticket) -> TicketPreview:
    return TicketPreview(
        id=ticket.id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        created_by=ticket.created_by,
        reporter_id=ticket.reporter_id,
        number=f"{ticket.number}",
        title=ticket.title,
        status=ticket.status,
        priority=ticket.priority,
    )


def map_comment_to_response(comment: Comment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_role=comment.author_role,
        text=comment.text,
        type=comment.type,
        parent_comment_id=comment.parent_comment_id,
        reply_count=comment.reply_count,
        attachments=[map_attachment_to_response(attachment) for attachment in comment.attachments],
    )


def map_comment_with_reactions_to_response(
        comment: Comment,
        reaction_counts: dict[ReactionType, int],
        user_reactions: list[ReactionType]
) -> CommentWithReactionsResponse:
    return CommentWithReactionsResponse(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_role=comment.author_role,
        text=comment.text,
        type=comment.type,
        parent_comment_id=comment.parent_comment_id,
        reply_count=comment.reply_count,
        attachments=[map_attachment_to_response(attachment) for attachment in comment.attachments],
        reaction_counts=reaction_counts,
        user_reactions=user_reactions,
    )


def map_history_entry_to_response(history_entry: TicketHistoryEntry) -> HistoryEntryResponse:
    return HistoryEntryResponse(
        created_at=history_entry.created_at,
        actor_id=history_entry.actor_id,
        action=history_entry.action,
        old_value=history_entry.old_value,
        new_value=history_entry.new_value,
        description=history_entry.description,
    )


def map_ticket_to_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        project_id=ticket.project_id,
        counterparty_id=ticket.counterparty_id,
        product_id=ticket.product_id,
        created_by_role=ticket.created_by_role,
        created_by=ticket.created_by,
        reporter_id=ticket.reporter_id,
        number=f"{ticket.number}",
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        assigned_to=ticket.assigned_to,
        closed_at=ticket.closed_at,
        is_archived=ticket.is_deleted,
        tags=[Tag(name=tag.name, color=tag.color) for tag in ticket.tags],
        attachments=[map_attachment_to_response(attachment) for attachment in ticket.attachments],
        history=[map_history_entry_to_response(history_entry) for history_entry in ticket.history],
    )


def map_project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        name=project.name,
        key=f"{project.key}",
        description=project.description,
        owner_id=project.owner_id,
        counterparty_id=project.counterparty_id,
        created_by=project.created_by,
        status=project.status,
        memberships=[
            MembershipResponse(
                user_id=membership.user_id,
                project_role=membership.project_role,
                added_by=membership.added_by,
                added_at=membership.added_at,
                is_active=membership.is_active
            )
            for membership in project.memberships
        ]
    )
