from uuid import uuid4

import pytest

from src.knowledge.infra.splitters import (
    MediaChunk,
    TextChunk,
    extract_media,
    remove_media_syntax,
    split_markdown,
)


class TestExtractMedia:

    @pytest.fixture
    def md_text_without_media(self):
        return """\
        # Header 1

        Some text without media
        """

    @pytest.fixture
    def attachment_id_1(self):
        return uuid4()

    @pytest.fixture
    def attachment_id_2(self):
        return uuid4()

    @pytest.fixture
    def md_text_with_valid_media(self, attachment_id_1, attachment_id_2):
        return f"""\
        # Header 1

        Some text from header 1

        ## Header 2
        ![alt-text-1](media://{attachment_id_1})

        Soma text from header 2

        -----------------------

        ![alt-text-2](media://{attachment_id_2})
        """

    @pytest.fixture
    def md_text_with_invalid_media(self, attachment_id_1):
        return f"""\
        # Header 1

        Some text from header 1

        ## Header 2
        ![alt-text-1](media://{attachment_id_1})

        Soma text from header 2

        -----------------------

        ![alt-text-2](media://not-a-uuid)
        """

    @pytest.fixture
    def md_text_with_empty_alt(self):
        return "![](media://123e4567-e89b-12d3-a456-426614174000)"

    def test_extract_from_empty_text(self):
        empty_text = ""

        assert extract_media(empty_text) == []

    def test_extract_from_text_without_media(self, md_text_without_media):
        assert extract_media(md_text_without_media) == []

    def test_extract_media_success(
            self, attachment_id_1, attachment_id_2, md_text_with_valid_media
    ):
        chunks = extract_media(md_text_with_valid_media)

        assert len(chunks) == len([attachment_id_1, attachment_id_2])

        assert chunks[0].alt_text == "alt-text-1"
        assert chunks[1].alt_text == "alt-text-2"

        assert chunks[0].start_char < chunks[1].start_char

        assert chunks[0].attachment_id == attachment_id_1
        assert chunks[1].attachment_id == attachment_id_2

    def test_invalid_attachment_id_skipped(self, md_text_with_invalid_media):
        chunks = extract_media(md_text_with_invalid_media)

        assert len(chunks) == 1
        assert chunks[0].alt_text == "alt-text-1"

    def test_empty_alt(self, md_text_with_empty_alt):
        chunks = extract_media(md_text_with_empty_alt)

        assert not chunks[0].alt_text


class TestRemoveMediaSyntax:

    def test_empty_text_and_empty_chunks(self):
        assert not remove_media_syntax("", [])

    def test_with_no_media_chunks(self):
        text = "Some random markdown without images"

        assert remove_media_syntax(text, []) == text

    def test_single_media_with_alt(self):

        attachment_id = uuid4()
        md_content = f"Some text ![alt](media://{attachment_id}) here"
        chunks = extract_media(md_content)

        expected = "Some text alt here"
        assert remove_media_syntax(md_content, chunks) == expected

    def test_single_media_without_alt(self):
        attachment_id = uuid4()
        md_content = f"pre ![](media://{attachment_id}) post"
        chunks = extract_media(md_content)

        expected = "pre  post"
        assert remove_media_syntax(md_content, chunks) == expected


class TestSplitMarkdown:

    @pytest.fixture
    def md_content(self):
        return f"""\
        # Введение
        Это вводный раздел, в котором описывается основная цель документа.
        Здесь пока нет изображений.

        ## Начало работы

        Для начала работы вам потребуется установить необходимые зависимости.
        Список команд представлен ниже:

        - Установите Python 3.10+
        - Установите зависимости из requirements.txt
        - Настройте переменные окружения

        ### Конфигурация

        Ниже приведён пример конфигурационного файла `config.yaml`:

        ```yaml
        database:
            host: localhost
            port: 5432
            name: mydb

        ### Медиа примеры

        ![Картинка](media://{uuid4()})

        **Логотип проекта**

        ![Логотип](media://{uuid4()})

        Дополнительные материалы
        Более подробную информацию можно найти в официальной документации.
        Рекомендуется также ознакомиться с видео-инструкцией.
        """

    def test_empty_text(self):
        assert split_markdown("") == []

    def test_split_success(self, md_content):
        chunks = split_markdown(md_content)

        text_orders = [chunk.order for chunk in chunks if isinstance(chunk, TextChunk)]

        assert text_orders == list(range(len(text_orders)))

        media_chunks = [chunk for chunk in chunks if isinstance(chunk, MediaChunk)]
        excepted_media_chunks_length = 2

        assert len(media_chunks) == excepted_media_chunks_length
        assert isinstance(chunks[0], MediaChunk)
