from dataclasses import dataclass, field
from datetime import datetime, time
from uuid import UUID

from ...shared.domain.entities import Entity
from ...shared.utils.time import current_datetime
from .vo import Skill, SupportLineLevel, TicketAssigneeCandidate, TicketAssignmentSuggestionStatus


@dataclass(kw_only=True)
class Employee(Entity):
    """Профиль сотрудника поддержки"""

    user_id: UUID
    support_line_id: UUID | None = None
    skills: list[Skill] = field(default_factory=list)
    current_load: int = field(default=0)
    is_available: bool = True

    # Часы работы
    working_hours_start: time | None = None
    working_hours_end: time | None = None

    def add_skill(self, new_skill: Skill) -> None:
        """Добавление нового навыка"""

        if any(new_skill.name == skill.name for skill in self.skills):
            raise ValueError(f"Skill {new_skill.name} already exists")

        self.skills.append(new_skill)

    def increase_load(self) -> None:
        """Увеличение счётчика текущей нагрузки"""

        self.current_load += 1

    def decrease_load(self) -> None:
        """Уменьшение счётчика нагрузки"""

        if self.current_load > 0:
            self.current_load -= 1


@dataclass(kw_only=True)
class SupportLine(Entity):
    """Линия поддержки"""

    level: SupportLineLevel
    name: str
    description: str | None = None
    is_default: bool = False
    auto_assignment_enabled: bool = True
    ai_assignment_threshold: float = field(default=0.75)  # confidence threshold для AI


@dataclass(kw_only=True)
class TicketAssignmentSuggestion(Entity):
    """
    Предложение системы по назначению тикета (AI + rule-based matching).
    Human-in-the-loop рекомендация.
    """

    ticket_id: UUID
    generated_at: datetime = field(default_factory=current_datetime)
    status: TicketAssignmentSuggestionStatus

    # Топ N - кандидатов
    candidates: list[TicketAssigneeCandidate] = field(default_factory=list)

    # Метаданные
    generated_by_model: str  # Какой моделью сделан метч
    total_candidates_evaluated: int
    generated_by: UUID | None = None
