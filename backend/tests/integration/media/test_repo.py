from uuid import uuid4

import pytest

from src.media.domain.entities import Attachment
from src.shared.utils.time import current_datetime


@pytest.fixture
def sample_attachment() -> Attachment:
    return Attachment(
        original_filename="test_file.txt",
        mime_type="text/plain",
        size_bytes=1024,
        storage_key="test-storage-key",
        owner_type="ticket",
        owner_id=uuid4(),
        is_public=False,
        uploaded_at=current_datetime(),
        uploaded_by=uuid4(),
    )


class TestSqlAttachmentRepository:
    @pytest.mark.asyncio
    async def test_get_by_storage_key(self, session, attachment_repo, sample_attachment):
        await attachment_repo.create(sample_attachment)
        await session.commit()

        attachment = await attachment_repo.get_by_storage_key(sample_attachment.storage_key)
        assert attachment is not None
        assert attachment.id == sample_attachment.id

    @pytest.mark.asyncio
    async def test_get_by_storage_key_returns_none(self, attachment_repo):
        attachment = await attachment_repo.get_by_storage_key("nonexistent-key")
        assert attachment is None

    @pytest.mark.asyncio
    async def test_get_by_owner(self, session, attachment_repo):
        owner_type = "ticket"
        owner_id = uuid4()
        attachments = []
        excepted_attachments_count = 3
        for i in range(excepted_attachments_count):
            attachment = Attachment(
                original_filename=f"test_file{i}.txt",
                mime_type="text/plain",
                size_bytes=100 * (i + 1),
                storage_key=f"storage-key-{i}",
                owner_type=owner_type,
                owner_id=owner_id,
                is_public=False,
                uploaded_at=current_datetime(),
                uploaded_by=uuid4(),
            )
            attachments.append(attachment)
            await attachment_repo.create(attachment)

        other_owner_attachment = Attachment(
            original_filename="other_file.txt",
            mime_type="text/plain",
            size_bytes=500,
            storage_key="other-key",
            owner_type=owner_type,
            owner_id=uuid4(),
            is_public=False,
            uploaded_at=current_datetime(),
            uploaded_by=uuid4(),
        )
        await attachment_repo.create(other_owner_attachment)
        await session.commit()

        found_attachments = await attachment_repo.get_by_owner(owner_type, owner_id)

        assert len(found_attachments) == excepted_attachments_count

        found_ids = {found_attachment.id for found_attachment in found_attachments}
        excepted_ids = {attachment.id for attachment in attachments}

        assert found_ids == excepted_ids
