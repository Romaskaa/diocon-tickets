from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.products.domain.entities import SoftwareProduct
from src.products.domain.vo import ProductCategory, ProductStatus
from src.shared.domain.exceptions import InvariantViolationError


@pytest.fixture
def sample_product():
    return SoftwareProduct(
        name="1С ERP",
        vendor="1C",
        version="0.1.0",
        category=ProductCategory.ERP,
        status=ProductStatus.ACTIVE,
        attributes={
            "auth_method": "OAuth 2.0",
            "release_date": 2026,
        },
    )


def test_create_and_normalize_product_success():
    """
    Успешное создание программного продукта
    """

    product = SoftwareProduct(
        name="1С УНФ  ",
        vendor=" 1С ",
        version="0.1.0",
        category=ProductCategory.ERP,
        description="""\
        «1С:Управление нашей фирмой» (1С:УНФ) — это комплексное решение для автоматизации учета
        и управления малым бизнесом
        """,
        status=ProductStatus.ACTIVE,
        attributes={
            "server_url": "http://localhost:80",
            "users_count": 15,
        },
        created_by=uuid4(),
    )

    assert product.name == "1С УНФ"
    assert product.vendor == "1С"


def test_empty_title_or_vendor_raises_value_error():
    """
    Наименование или вендор не могут быть пустыми
    """

    with pytest.raises(ValueError, match="Product name cannot be empty"):
        SoftwareProduct(
            name="     ",
            vendor="1C",
            category=ProductCategory.ERP,
            status=ProductStatus.ACTIVE,
        )

    with pytest.raises(ValueError, match="Product vendor cannot be empty"):
        SoftwareProduct(
            name="1С ERP",
            vendor="  ",
            category=ProductCategory.ERP,
            status=ProductStatus.ACTIVE,
        )


def test_cannot_activate_archived_product():
    """
    Нельзя активировать продукт из архива (нужно создать новый)
    """

    product = SoftwareProduct(
        name="1С ERP",
        vendor="1C",
        category=ProductCategory.ERP,
        status=ProductStatus.ARCHIVED,
    )

    with pytest.raises(
            InvariantViolationError, match="Cannot reactivate archived product directly"
    ):
        product.change_status(ProductStatus.ACTIVE)


@pytest.mark.parametrize(
    "new_status", [ProductStatus.ACTIVE, ProductStatus.DEPRECATED, ProductStatus.ARCHIVED]
)
def test_change_product_status_success(new_status):
    """
    Успешное изменение статуса продукта
    """

    product = SoftwareProduct(
        name="1С ERP",
        vendor="1C",
        category=ProductCategory.ERP,
        status=ProductStatus.BETA,
    )

    updated_by = uuid4()
    product.change_status(new_status, changed_by=updated_by)

    assert product.status == new_status
    assert product.updated_by == updated_by


def test_product_fields_includes_in_search_keywords(sample_product):
    """
    Необходимые поля продукта включаются в ключевые слова для поиска
    """

    for value in ["1С ERP", "1C", "0.1.0", "OAuth 2.0"]:
        assert value in sample_product.search_keywords

    release_date = 2026
    assert release_date not in sample_product.search_keywords


def test_archive_product_success(sample_product):
    """
    Успешная архивация продукта
    """

    archived_by = uuid4()
    sample_product.archive(archived_by=archived_by, archived_by_role=UserRole.SUPPORT_MANAGER)

    assert sample_product.status == ProductStatus.ARCHIVED
    assert sample_product.updated_by == archived_by
    assert sample_product.is_deleted is True


@pytest.mark.parametrize(
    "user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.SUPPORT_AGENT]
)
def test_not_required_role_try_archive_product_failure(sample_product, user_role):
    """
    Падение ошибки при невалидной роли
    """

    with pytest.raises(
            PermissionDeniedError, match="Only support manager or admin can archive product"
    ):
        sample_product.archive(archived_by=uuid4(), archived_by_role=user_role)


def test_archive_already_archived_do_nothing(sample_product):
    """
    При архивации уже архивированного продукта ничего не происходит
    """

    first_archived_by = uuid4()
    sample_product.archive(archived_by=first_archived_by, archived_by_role=UserRole.ADMIN)
    first_updated_at = sample_product.updated_at

    assert sample_product.is_deleted is True

    second_archived_by = uuid4()
    sample_product.archive(
        archived_by=second_archived_by, archived_by_role=UserRole.SUPPORT_MANAGER
    )

    assert sample_product.updated_by == first_archived_by
    assert sample_product.updated_at == first_updated_at
