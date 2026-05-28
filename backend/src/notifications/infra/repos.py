from uuid import UUID

from sqlalchemy import func, select

from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...shared.schemas import Page, Pagination
from ..domain.entities import Notification, UserPreference
from ..domain.vo import NotificationType
from .models import NotificationOrm, UserPreferenceOrm


class NotificationMapper(ModelMapper[Notification, NotificationOrm]):
    @staticmethod
    def to_entity(model: NotificationOrm) -> Notification:
        return Notification(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            user_id=model.user_id,
            title=model.title,
            message=model.message,
            type=model.notification_type,
            read=model.read,
            data=model.data,
        )

    @staticmethod
    def from_entity(entity: Notification) -> NotificationOrm:
        return NotificationOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            user_id=entity.user_id,
            title=entity.title,
            message=entity.message,
            notification_type=entity.type,
            read=entity.read,
            data=entity.data,
        )


class SqlNotificationRepository(SqlAlchemyRepository[Notification, NotificationOrm]):
    model = NotificationOrm
    model_mapper = NotificationMapper

    async def get_unread_count(self, user_id: UUID) -> int:
        # Формирование запроса
        stmt = select(self.model).where(
            (self.model.user_id == user_id) & (self.model.read.is_(False))
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())

        return await self.session.scalar(count_stmt)

    async def get_by_user(
            self, user_id: UUID, pagination: Pagination, unread_only: bool = False
    ) -> Page[Notification]:
        stmt = select(self.model).where(self.model.user_id == user_id)

        if unread_only:
            stmt = stmt.where(self.model.read.is_(False))

        return await self._paginate(stmt, pagination)


class UserPreferenceMapper(ModelMapper[UserPreference, UserPreferenceOrm]):
    @staticmethod
    def to_entity(model: UserPreferenceOrm) -> UserPreference:
        return UserPreference(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            user_id=model.user_id,
            notification_type=model.notification_type,
            enabled_channels=set(model.enabled_channels),
            muted_until=model.muted_until,
        )

    @staticmethod
    def from_entity(entity: UserPreference) -> UserPreferenceOrm:
        return UserPreferenceOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            user_id=entity.user_id,
            notification_type=entity.notification_type,
            enabled_channels=list(entity.enabled_channels),
            muted_until=entity.muted_until,
        )


class SqlUserPreferenceRepository(SqlAlchemyRepository[UserPreference, UserPreferenceOrm]):
    model = UserPreferenceOrm
    model_mapper = UserPreferenceMapper

    async def get_for_notification(
            self, user_id: UUID, notification_type: NotificationType
    ) -> UserPreference | None:
        stmt = select(self.model).where(
            (self.model.user_id == user_id) & (self.model.notification_type == notification_type)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_by_user(self, user_id: UUID) -> list[UserPreference]:
        stmt = select(self.model).where(self.model.user_id == user_id)
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [self.model_mapper.to_entity(model) for model in models]
