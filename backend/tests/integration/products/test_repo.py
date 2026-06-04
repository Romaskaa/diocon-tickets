import pytest
from scripts.regsetup import description

from src.products.domain.vo import ProductCategory, ProductStatus
from src.products.infra.models import SoftwareProductOrm
from src.products.infra.repo import SoftwareProductMapper, SqlProductRepository
from src.shared.schemas import PageParams


@pytest.fixture
def product_repo(session):
    return SqlProductRepository(session)


@pytest.fixture
async def seed_products(session):
    products = [
        SoftwareProductOrm(
            name="1C:УНФ",
            vendor="1C",
            description="""\
            1С:УНФ (Управление нашей фирмой) — это комплексная программа для автоматизации бизнеса,
            разработанная компанией 1С специально для малого и микро-бизнеса.
            """,
            category=ProductCategory.ERP,
            status=ProductStatus.ACTIVE,
            attributes={"environment": "production", "licence_type": "cloud"},
        ),
        SoftwareProductOrm(
            name="1С:Бухгалтерия",
            vendor="1C",
            description="Бухгалтерский учёт",
            category=ProductCategory.ERP,
            status=ProductStatus.ACTIVE,
            attributes={},
        ),
        SoftwareProductOrm(
            name="Битрикс24",
            vendor="1С-Битрикс",
            description="CRM портал",
            category=ProductCategory.WEB,
            status=ProductStatus.ACTIVE,
            attributes={},
        ),
        SoftwareProductOrm(
            name="МойСклад",
            vendor="МойСклад",
            category=ProductCategory.WEB,
            status=ProductStatus.DEPRECATED,
            attributes={},
        ),
        SoftwareProductOrm(
            name="1С:Бухгалтерия",
            vendor="1C",
            category=ProductCategory.ERP,
            status=ProductStatus.ACTIVE,
            description="""\
            «1С:Бухгалтерия» — это самая популярная в России и СНГ профессиональная программа
            для автоматизации бухгалтерского и налогового учета.
            """,
            attributes={},
        ),
    ]
    session.add_all(products)
    await session.commit()
    return products


@pytest.mark.integration
class TestPaginate:
    """
    Тесты для пагинации справочника программных продуктов
    """

    @pytest.mark.asyncio
    async def test_include_filters_by_category_and_status_success(
            self, product_repo, seed_products
    ):
        """
        Успешное применение фильтров по статусу и категории
        """

        page = await product_repo.paginate(
            pagination=PageParams(page=1, size=10),
            category=ProductCategory.ERP,
            status=ProductStatus.ACTIVE,
        )

        excepted_orms = [
            product
            for product in seed_products
            if product.category == ProductCategory.ERP and product.status == ProductStatus.ACTIVE
        ]
        excepted_orms = sorted(excepted_orms, key=lambda x: x.created_at)
        excepted_items = [SoftwareProductMapper.to_entity(orm) for orm in excepted_orms]

        assert page.items == excepted_items

    @pytest.mark.asyncio
    async def test_fuzzy_search_orders_by_similarity(self, product_repo, seed_products):  # noqa: ARG002
        """
        Нечёткий поиск (по три-граммам) название, описание, вендор + сортировка по релевантности
        """

        search_query = "бухгалтер"
        page = await product_repo.paginate(
            pagination=PageParams(page=1, size=10), search=search_query
        )

        assert all(
            search_query in item.description.lower() for item in page.items
        )
