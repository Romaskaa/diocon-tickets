import logging

from botocore.exceptions import ClientError

from src.core.database import session_factory
from src.core.settings import S3_BACKUPS_BUCKET_NAME, S3_BUCKET_NAME, settings
from src.iam.domain.services import create_admin
from src.iam.infra.repos import SqlUserRepository
from src.iam.security import hash_password
from src.media.infra.s3 import S3Storage

logger = logging.getLogger(__name__)


async def create_first_admin() -> None:
    """Создание системного администратора"""

    async with session_factory() as session:
        user_repo = SqlUserRepository(session)
        exists = await user_repo.get_by_email(settings.admin.email)
        if exists:
            logger.warning("Admin already exists")
            return
        admin = create_admin(
            email=settings.admin.email, password_hash=hash_password(settings.admin.password)
        )
        await user_repo.create(admin)
        await session.commit()
        logger.info("First admin created successfully")


async def init_s3_buckets() -> None:
    """Создание S3 бакетов"""

    # 1. Инициализация приватного S3 клиента
    storage = S3Storage(
        endpoint_url=settings.yandex_cloud.endpoint_url,
        access_key=settings.yandex_cloud.access_key_id,
        secret_key=settings.yandex_cloud.secret_access_key,
        bucket_name=S3_BUCKET_NAME,
    )

    # 2. Инициализация публичного S3 клиента
    async with storage.get_client() as client:
        for bucket in [S3_BUCKET_NAME, S3_BACKUPS_BUCKET_NAME]:
            try:
                await client.head_bucket(Bucket=bucket)
                logger.info("S3 bucket - `%s` already exists, skipping creation", bucket)
            except ClientError:
                logger.info("S3 bucket does not exist, planned_start creating - `%s`", bucket)
                await client.create_bucket(Bucket=bucket)

    logger.info("S3 storage initialized successfully")
