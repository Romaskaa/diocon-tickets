import contextlib
import re
from dataclasses import dataclass, field
from uuid import UUID

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

MEDIA_PATTERN = r"!\[(.*?)\]\(media://([0-9a-fA-F-]+)\)"


@dataclass(frozen=True)
class TextChunk:
    order: int
    content: str
    context_heading: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class MediaChunk:
    attachment_id: UUID
    alt_text: str | None = None
    start_char: int
    end_char: int


def extract_media(md_content: str) -> list[MediaChunk]:
    """Извлечение медиа контента из текста статьи"""

    media = []
    for match in re.finditer(MEDIA_PATTERN, md_content):
        alt, attachment_id = match.groups()

        with contextlib.suppress(ValueError):
            attachment_id = UUID(attachment_id)

            media.append(
                MediaChunk(
                    attachment_id=attachment_id,
                    alt_text=alt.strip(),
                    start_char=match.start(),
                    end_char=match.end(),
                )
            )

    return media


def remove_media_syntax(md_content: str, chunks: list[MediaChunk]) -> str:
    """Удаление медиа ссылок ![alt](media://...), оставляя alt-текст"""

    chars = list(md_content)

    for chunk in sorted(chunks, key=lambda x: x.start_char, reverse=True):
        # Замена на alt-текст
        replacement = "" if chunk.alt_text is None else chunk.alt_text
        chars[chunk.start_char:chunk.end_char] = replacement

    return "".join(chars)


def split_markdown(
        md_content: str,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        headers_to_split_on: list[tuple[str, str]] | None = None
) -> list[TextChunk | MediaChunk]:
    """Разбиение Markdown текста на чанки с определением медиа"""

    if not md_content.strip():
        return []

    if headers_to_split_on is None:
        headers_to_split_on = [
            ("#", "H1"),
            ("##", "H2"),
            ("###", "H3"),
            ("####", "H4"),
        ]

    # Первичное разбиение по заголовкам
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on, strip_headers=False
    )

    # Извлечение медиа контента
    media_chunks = extract_media(md_content)

    # Удаление медиа Markdown синтаксиса для чистоты текста
    cleaned_content = remove_media_syntax(md_content, chunks=media_chunks)

    md_header_splits = markdown_splitter.split_text(cleaned_content)

    # Рекурсивное разбиение на более малые чанки
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        keep_separator=True,
    )

    chunks: list[TextChunk | MediaChunk] = [*media_chunks]
    order = 0

    for document in md_header_splits:
        context_headings = []

        # Обогащение контекста иерархией заголовков
        for _, header_key in headers_to_split_on:
            if header_value := document.metadata.get(header_key, "").strip():
                context_headings.append(header_value)

        # Если блок не превышает лимит - оставляем как есть
        if len(document.page_content) <= chunk_size + 100:
            chunks.append(
                TextChunk(
                    order=order,
                    content=document.page_content.strip(),
                    context_heading=context_headings
                )
            )
            order += 1  # Переход к следующему блоку

        # Рекурсивное разбиение по символам
        else:
            texts = recursive_splitter.split_text(document.page_content)

            for text in texts:
                if text.strip():
                    chunks.append(
                        TextChunk(
                            order=order,
                            content=text.strip(),
                            context_heading=context_headings
                        )
                    )
                    order += 1

    return chunks
