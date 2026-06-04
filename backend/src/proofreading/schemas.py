from pydantic import BaseModel, Field, NonNegativeInt


class TextIssue(BaseModel):
    """Проблема с текстом (исправление)"""

    category: str
    original: str
    suggestion: str
    start: NonNegativeInt
    end: NonNegativeInt
    message: str


class TextCheckResult(BaseModel):
    """Результат проверки текста"""

    original_text: str = Field(..., description="Оригинальный текст")
    corrected_text: str = Field(..., description="Исправленный текст")
    has_issues: bool = Field(..., description="Есть ли замечания и исправления по тексту")
    suggestions: list[TextIssue] = Field(default_factory=list, description="Список исправлений")
