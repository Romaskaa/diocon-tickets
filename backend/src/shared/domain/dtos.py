from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TimeRangeFilters:
    """
    Фильтр по временным промежуткам.
    """

    created_after: datetime | None = None
    created_before: datetime | None = None
