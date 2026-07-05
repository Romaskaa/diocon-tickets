from ..media.mappers import map_attachment_to_response
from .domain.entities import Comment, Ticket
from .domain.vo import ReactionType
from .schemas import (
    CommentResponse,
    CommentWithReactionsResponse,
    Tag,
    TicketPreview,
    TicketResponse,
    TicketViewResponse,
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
        type=ticket.type,
        status=ticket.status,
        priority=ticket.priority,
    )


def map_ticket_to_view_response(
        ticket: Ticket,
        reporter_full_name: str,
        assignee_full_name: str | None = None,
        counterparty_name: str | None = None,
        project_key: str | None = None,
) -> TicketViewResponse:
    return TicketViewResponse(
        id=ticket.id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        reporter_full_name=reporter_full_name,
        assignee_full_name=assignee_full_name,
        counterparty_name=counterparty_name,
        project_key=project_key,
        number=ticket.number.value,
        title=ticket.title,
        type=ticket.type,
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
        number=ticket.number.value,
        title=ticket.title,
        description=ticket.description,
        type=ticket.type,
        status=ticket.status,
        priority=ticket.priority,
        assignee_id=ticket.assignee_id,
        closed_at=ticket.closed_at,
        is_archived=ticket.is_deleted,
        tags=[Tag(name=tag.name, color=tag.color) for tag in ticket.tags],
        attachments=[map_attachment_to_response(attachment) for attachment in ticket.attachments],
    )
