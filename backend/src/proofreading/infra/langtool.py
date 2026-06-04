import language_tool_python

from ...core.settings import settings
from ..schemas import TextCheckResult, TextIssue

MIN_TEXT_LENGTH = 3


def check_text_spells(text: str) -> TextCheckResult:
    """Проверка текста на грамматические и орфографические ошибки"""

    tool = language_tool_python.LanguageTool(
        language=settings.language_tool.language,
        remote_server=settings.language_tool.url,
    )

    # 1. Текст слишком короткий
    if not text.strip() or len(text.strip()) < MIN_TEXT_LENGTH:
        return TextCheckResult(
            original_text=text, corrected_text=text, has_issues=False, suggestions=[]
        )

    # 2. Получение ошибок
    matches = tool.check(text)

    # 3. Формирование списка исправлений
    suggestions: list[TextIssue] = []
    corrected_text = text

    for match in matches:
        issue = TextIssue(
            category=match.category,
            original=match.context[match.offset:match.offset + match.error_length],
            suggestion=match.replacements[0] if match.replacements else "",
            start=match.offset,
            end=match.offset + match.error_length,
            message=match.message,
        )
        suggestions.append(issue)

        # 4. Исправление ошибок в тексте
        if match.replacements:
            corrected_text = (
                corrected_text[:match.offset]
                + match.replacements[0]
                + corrected_text[match.offset + match.error_length:]
            )

    return TextCheckResult(
        original_text=text,
        corrected_text=corrected_text,
        has_issues=len(suggestions) > 0,
        suggestions=suggestions,
    )
