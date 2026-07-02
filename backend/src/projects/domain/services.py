import random
import re
import string
from uuid import UUID

from src.iam.domain.authz import Subject
from src.shared.utils.text import get_latin_slug

from .entities import Project, ProjectMember
from .vo import ProjectKey, ProjectRole

WORDS_COUNT = 2
MIN_KEY_LENGTH = 2
MAX_KEY_LENGTH = 10


def generate_project_key(name: str, default: str = "PRJ") -> str:
    """
    Генерирует предложение ключа проекта на основе его имени.

    Алгоритм:
     1. Оставляем только буквы (латиница, кириллица) и пробелы.
     2. Приводим к верхнему регистру.
     3. Берём первые буквы от первых 1-3 слов, если слов несколько.
     4. Если получилось слишком коротко (<2) – берём первые 2-4 буквы первого слова.
     5. Обрезаем до 10 символов.
     6. Если результат всё ещё пуст – возвращаем default.
    """

    if not name:
        return default

    # 1. Только буквы и пробелы (удаление цифр, знаков, эмодзи)
    cleaned = re.sub(r"[^A-Za-zА-Яа-яЁё\s]", "", name)
    cleaned = cleaned.upper()

    # 2. Разбиение на слова
    words = cleaned.split()
    if not words:
        return default

    # 3. Транслитерация слов
    words = [get_latin_slug(word) for word in words]

    # 4. Генерация ключа
    key = "".join(word[0] for word in words[:3]) if len(words) > WORDS_COUNT else words[0][:4]

    # 5. Обеспечение минимальной длины (2 символа)
    if len(key) < MIN_KEY_LENGTH:
        key = (key + key).ljust(2, "X")[:2]  # "А" -> "АА" или "АX"

    # 6. Обрезание до максимальной длины (10 символов)
    key = key[:10]

    # 7. Дополнительная проверка, что первый символ является буквой
    if not key[0].isalpha():
        key = "P" + key[1:] if len(key) > 1 else "PR"

    return key


def generate_key_suggestions(
        original_key: str,
        *,
        max_attempts: int = 5,
        min_key_length: int = 3
) -> list[str]:
    """
    Генерирует альтернативные ключи проекта на основе заданного ключа.
    Использовать для разрешения конфликтов уникальности.
    """

    base_key = original_key.strip().upper()

    if not base_key:
        base_key = "PROJ"  # fallback

    suggestions = [f"{base_key}{i}" for i in range(1, max_attempts + 1)]

    if len(base_key) <= min_key_length:
        suggestions.extend(
            f"{base_key}{letter}"
            for letter in random.sample(
                string.ascii_uppercase,
                len(string.ascii_uppercase),
            )
        )

    seen = set()
    result = []

    for key in suggestions:
        if key not in seen:
            seen.add(key)
            result.append(key)

    return result[: max_attempts * 2]


def create_project(
        *,
        name: str,
        key: ProjectKey,
        description: str | None,
        counterparty_id: UUID,
        creator: Subject,
) -> tuple[Project, ProjectMember]:
    """
    Создаёт новый проект вместе с владельцем.
    """

    project = Project.create(
        name=name,
        key=key,
        description=description,
        counterparty_id=counterparty_id,
        created_by=creator.id
    )
    owner = project.create_member(
        user_id=creator.id,
        project_roles=[ProjectRole.OWNER],
        created_by=creator.id
    )

    return project, owner
