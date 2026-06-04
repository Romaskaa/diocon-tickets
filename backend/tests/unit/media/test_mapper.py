from uuid import uuid4

import pytest

from src.media.domain.entities import Attachment
from src.media.infra.models import AttachmentOrm
from src.media.infra.repo import AttachmentMapper
from src.shared.utils.time import current_datetime


@pytest.fixture
def sample_attachment_orm() -> AttachmentOrm:
    return AttachmentOrm(
        id=uuid4(),
        updated_at=current_datetime(),
        created_at=current_datetime(),
        original_filename="document.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        storage_key="uploads/doc.pdf",
        owner_type="ticket",
        owner_id=uuid4(),
        is_public=False,
        uploaded_at=current_datetime(),
        uploaded_by=uuid4(),
    )


@pytest.fixture
def sample_attachment() -> Attachment:
    return Attachment(
        original_filename="document.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        storage_key="uploads/doc.pdf",
        owner_type="ticket",
        owner_id=uuid4(),
        is_public=False,
        uploaded_at=current_datetime(),
        uploaded_by=uuid4(),
    )


class TestAttachmentMapper:
    def test_to_entity(self, sample_attachment_orm: AttachmentOrm):
        entity = AttachmentMapper.to_entity(sample_attachment_orm)

        assert entity.id == sample_attachment_orm.id
        assert entity.updated_at == sample_attachment_orm.updated_at
        assert entity.created_at == sample_attachment_orm.created_at
        assert entity.original_filename == sample_attachment_orm.original_filename
        assert entity.mime_type == sample_attachment_orm.mime_type
        assert entity.size_bytes == sample_attachment_orm.size_bytes
        assert entity.storage_key == sample_attachment_orm.storage_key
        assert entity.owner_type == sample_attachment_orm.owner_type
        assert entity.owner_id == sample_attachment_orm.owner_id
        assert entity.is_public == sample_attachment_orm.is_public
        assert entity.uploaded_at == sample_attachment_orm.uploaded_at
        assert entity.uploaded_by == sample_attachment_orm.uploaded_by

    def test_from_entity(self, sample_attachment: Attachment):
        orm = AttachmentMapper.from_entity(sample_attachment)

        assert orm.id == sample_attachment.id
        assert orm.updated_at == sample_attachment.updated_at
        assert orm.created_at == sample_attachment.created_at
        assert orm.original_filename == sample_attachment.original_filename
        assert orm.mime_type == sample_attachment.mime_type
        assert orm.size_bytes == sample_attachment.size_bytes
        assert orm.storage_key == sample_attachment.storage_key
        assert orm.owner_type == sample_attachment.owner_type
        assert orm.owner_id == sample_attachment.owner_id
        assert orm.is_public == sample_attachment.is_public
        assert orm.uploaded_at == sample_attachment.uploaded_at
        assert orm.uploaded_by == sample_attachment.uploaded_by

    def test_roundtrip(self, sample_attachment_orm: AttachmentOrm):
        entity = AttachmentMapper.to_entity(sample_attachment_orm)
        orm_back = AttachmentMapper.from_entity(entity)

        assert orm_back.id == sample_attachment_orm.id
        assert orm_back.updated_at == sample_attachment_orm.updated_at
        assert orm_back.created_at == sample_attachment_orm.created_at
        assert orm_back.original_filename == sample_attachment_orm.original_filename
        assert orm_back.mime_type == sample_attachment_orm.mime_type
        assert orm_back.size_bytes == sample_attachment_orm.size_bytes
        assert orm_back.storage_key == sample_attachment_orm.storage_key
        assert orm_back.owner_type == sample_attachment_orm.owner_type
        assert orm_back.owner_id == sample_attachment_orm.owner_id
        assert orm_back.is_public == sample_attachment_orm.is_public
        assert orm_back.uploaded_at == sample_attachment_orm.uploaded_at
        assert orm_back.uploaded_by == sample_attachment_orm.uploaded_by
