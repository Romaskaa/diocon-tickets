from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...iam.schemas import CurrentUser
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ..domain.entities import Reaction
from ..domain.repos import CommentRepository, ReactionRepository
from ..domain.vo import ReactionType
from ..schemas import ReactionResponse


class ReactionService:
    def __init__(
            self,
            session: AsyncSession,
            comment_repo: CommentRepository,
            reaction_repo: ReactionRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.comment_repo = comment_repo
        self.reaction_repo = reaction_repo
        self.event_publisher = event_publisher

    async def toggle(
            self,
            comment_id: UUID,
            current_user: CurrentUser,
            reaction_type: ReactionType,
    ) -> None:
        """Поставить или снять реакцию текущего пользователя"""

        # 1. Проверка комментария на существование
        comment = await self.comment_repo.read(comment_id)
        if comment is None or comment.is_deleted:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Проверка - оставлял ли пользователь такую реакцию
        existing = await self.reaction_repo.find(
            comment_id=comment_id, author_id=current_user.user_id, reaction_type=reaction_type
        )

        events_to_publish = []

        # 3. Обработка 3 основных сценариев
        if existing is None:
            # 3.1. Пользователь не оставлял реакции - создаём новую реакцию
            reaction = Reaction.create(
                comment_id=comment_id,
                author_id=current_user.user_id,
                author_role=current_user.role,
                reaction_type=reaction_type,
            )
            await self.reaction_repo.create(reaction)
            events_to_publish.extend(reaction.collect_events())
        elif existing.reaction_type == reaction_type:
            # 3.2. Пользователь нажал на ту же реакцию - удаляем
            await self.reaction_repo.delete(existing.id)
        else:
            # 3.3. Пользователь нажал на другую реакцию меняем тип
            existing.toggle(reaction_type, current_user.role)
            await self.reaction_repo.upsert(existing)
            events_to_publish.extend(existing.collect_events())

        await self.session.commit()

        # 4. Публикация доменных событий
        for event in events_to_publish:
            await self.event_publisher.publish(event)

    async def get_reactions_for_comment(
            self, comment_id: UUID, current_user: CurrentUser
    ) -> ReactionResponse:
        """Получение реакции для комментария"""

        # 1. Проверка существования комментария
        comment = await self.comment_repo.read(comment_id)
        if comment is None or comment.is_deleted:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        stats = await self.reaction_repo.get_reaction_stats([comment_id], current_user.user_id)

        return ReactionResponse(
            reaction_counts=stats.counts.get(comment_id, {}),
            user_reactions=list(stats.user_reactions.get(comment_id, set())),
        )
