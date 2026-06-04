from typing import Any

from dataclasses import dataclass, field
from uuid import UUID

from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.domain.vo import UserRole
from ...shared.domain.entities import Entity
from ...shared.domain.exceptions import InvariantViolationError
from ...shared.utils.time import current_datetime
from .vo import ProductCategory, ProductStatus


@dataclass(kw_only=True)
class SoftwareProduct(Entity):
    """
    Агрегат справочника программных продуктов
    """

    name: str
    vendor: str
    category: ProductCategory
    description: str | None = None
    version: str | None = None
    status: ProductStatus = field(default=ProductStatus.ACTIVE)

    # Специфичные аттрибуты
    attributes: dict[str, Any] = field(default_factory=dict)

    # Аудит
    created_by: UUID | None = None
    updated_by: UUID | None = None

    def __post_init__(self) -> None:
        # 1. Наименование и вендор нен могут быть пустыми
        if not self.name.strip():
            raise ValueError("Product name cannot be empty")
        if not self.vendor.strip():
            raise ValueError("Product vendor cannot be empty")

        # 2. Нормализация данных
        self.name = self.name.strip()
        self.vendor = self.vendor.strip()

    def change_status(self, new_status: ProductStatus, changed_by: UUID | None = None) -> None:
        """Обновление статуса"""

        if self.status == new_status:
            return

        # Нельзя активировать архивный продукт без явного действия
        if self.status == ProductStatus.ARCHIVED and new_status == ProductStatus.ACTIVE:
            raise InvariantViolationError(
                "Cannot reactivate archived product directly. Create a new version."
            )

        self.status = new_status
        self.updated_at = current_datetime()
        self.updated_by = changed_by

    def archive(self, archived_by: UUID, archived_by_role: UserRole) -> None:
        """Архивирование продукта"""

        if self.is_deleted:
            return

        # 1. Удалять программные продукты могут только админы и менеджеры поддержки
        if archived_by_role not in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
            raise PermissionDeniedError("Only support manager or admin can archive product")

        # 2. Обновление статуса и полей
        self.status = ProductStatus.ARCHIVED
        self.updated_by = archived_by
        self.deleted_at = current_datetime()

    @property
    def display_name(self) -> str:
        """Человеко-читаемое название для UI"""

        base_name = f"{self.vendor} {self.name}"
        if self.version is not None:
            base_name += f" ({self.version})"

        return base_name

    @property
    def search_keywords(self) -> list[str]:
        """Ключевые слова для полнотекстового поиска"""

        keywords = [self.name, self.vendor]

        if self.version is not None:
            keywords.append(self.version)

        # Добавление строковых метаданных
        keywords.extend([value for value in self.attributes.values() if isinstance(value, str)])

        return keywords
