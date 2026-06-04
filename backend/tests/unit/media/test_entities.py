from datetime import datetime
from uuid import uuid4

import pytest

from src.media.constants import MAX_FILENAME_LENGTH
from src.media.domain.entities import Attachment
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.utils.time import current_datetime


@pytest.fixture
def valid_data():
    return {
        "id": uuid4(),
        "original_filename": "report_q3.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1_234_567,
        "storage_key": "attachments/tickets/abc123/report_q3.pdf",
        "owner_type": "ticket",
        "owner_id": uuid4(),
        "is_public": False,
        "uploaded_at": current_datetime(),
        "uploaded_by": uuid4(),
    }


def test_create_valid_attachment(valid_data):
    """Успешное создание валидного вложения"""
    attachment = Attachment(**valid_data)

    excepted_size_bytes = 1_234_567

    assert attachment.id == valid_data["id"]
    assert attachment.original_filename == "report_q3.pdf"
    assert attachment.mime_type == "application/pdf"
    assert attachment.size_bytes == excepted_size_bytes
    assert attachment.storage_key == valid_data["storage_key"]
    assert attachment.owner_type == "ticket"
    assert attachment.is_public is False
    assert isinstance(attachment.uploaded_at, datetime)


def test_extension_property(valid_data):
    attachment = Attachment(**valid_data)

    assert attachment.extension == "pdf"

    data_no_ext = valid_data.copy()
    data_no_ext["original_filename"] = "README"
    attachment = Attachment(**data_no_ext)

    assert attachment.extension == "readme"


def test_is_image_property():
    attachment = Attachment(
        id=uuid4(),
        original_filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
        storage_key="img/1.jpg",
        owner_type="user",
        owner_id=uuid4(),
        uploaded_at=current_datetime(),
        uploaded_by=uuid4(),
    )
    assert attachment.is_image is True

    non_image_attachment = Attachment(
        id=uuid4(),
        original_filename="doc.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
        storage_key="doc/1.pdf",
        owner_type="ticket",
        owner_id=uuid4(),
        uploaded_at=current_datetime(),
        uploaded_by=uuid4(),
    )
    assert non_image_attachment.is_image is False


def test_is_document_property():
    attachment = Attachment(
        id=uuid4(),
        original_filename="contract.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=5000,
        storage_key="docs/contract.docx",
        owner_type="ticket",
        owner_id=uuid4(),
        uploaded_at=current_datetime(),
        uploaded_by=uuid4(),
    )
    assert attachment.is_document is True

    non_doc_attachment = Attachment(
        id=uuid4(),
        original_filename="avatar.png",
        mime_type="image/png",
        size_bytes=2048,
        storage_key="avatars/1.png",
        owner_type="user",
        owner_id=uuid4(),
        uploaded_at=current_datetime(),
        uploaded_by=uuid4(),
    )
    assert non_doc_attachment.is_document is False


def test_raises_on_empty_filename(valid_data):
    data = valid_data.copy()
    data["original_filename"] = "   "
    with pytest.raises(ValueError, match="Original filename cannot be empty"):
        Attachment(**data)


def test_raises_on_too_long_filename(valid_data):
    data = valid_data.copy()
    data["original_filename"] = "a" * (MAX_FILENAME_LENGTH + 10)
    with pytest.raises(ValueError, match="Original filename too long"):
        Attachment(**data)


def test_raises_on_negative_size(valid_data):
    data = valid_data.copy()
    data["size_bytes"] = -100
    with pytest.raises(InvariantViolationError, match="File size cannot be negative"):
        Attachment(**data)


def test_raises_on_unsupported_owner_type(valid_data):
    data = valid_data.copy()
    data["owner_type"] = "unknown_entity"
    with pytest.raises(InvariantViolationError, match="Unsupported owner type"):
        Attachment(**data)


def test_raises_on_invalid_mime_type_format(valid_data):
    # Пока в модели нет такой проверки, но можно протестировать текущее поведение
    data = valid_data.copy()
    data["mime_type"] = "invalid_mime"
    # Сейчас проходит — если добавишь проверку позже, тест нужно будет обновить
    attachment = Attachment(**data)
    assert attachment.mime_type == "invalid_mime"
