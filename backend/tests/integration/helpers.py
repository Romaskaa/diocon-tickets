from dataclasses import dataclass

from sqlalchemy.orm import Mapped

from src.core.database import Base
from src.shared.domain.entities import Entity
from src.shared.infra.repos import ModelMapper


@dataclass(kw_only=True)
class ExampleEntity(Entity):
    value: str


class ExampleOrm(Base):
    __tablename__ = "tests"

    value: Mapped[str]


class ExampleMapper(ModelMapper[ExampleEntity, ExampleOrm]):
    @staticmethod
    def to_entity(model: ExampleOrm) -> ExampleEntity:
        return ExampleEntity(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            value=model.value
        )

    @staticmethod
    def from_entity(entity: ExampleEntity) -> ExampleOrm:
        return ExampleOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            value=entity.value
        )
