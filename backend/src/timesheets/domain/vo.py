from enum import StrEnum


class WorklogStatus(StrEnum):
    """Статус записи о потраченном времени"""

    DRAFT = "draft"  # черновик
    SUBMITTED = "submitted"  # на согласовании
    APPROVED = "approved"  # согласовано
    REJECTED = "rejected"  # отклонено

    def is_editable(self) -> bool:
        """Можно ли редактировать запись"""

        return self in {self.DRAFT, self.REJECTED}

    def is_final(self) -> bool:
        """Является ли статус финальным"""

        return self == self.APPROVED


class TimesheetStatus(StrEnum):
    """Статус листа учёта рабочего времени"""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    PARTIALLY_APPROVED = "partially_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
