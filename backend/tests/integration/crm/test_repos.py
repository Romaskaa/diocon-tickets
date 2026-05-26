from uuid import uuid4

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import CounterpartyType, Inn, Kpp, Phone
from src.crm.infra.repos import SqlCounterpartyRepository
from src.iam.domain.services import create_customer
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.shared.schemas import Pagination
from src.products.domain.entities import SoftwareProduct
from src.products.domain.vo import ProductCategory, ProductStatus
from src.products.infra.repo import SqlProductRepository


EXPECTED_BRANCHES_COUNT = 2
EXPECTED_TREE_ITEMS_COUNT = 3
EXPECTED_CUSTOMERS_COUNT = 2


@pytest.fixture
def counterparty_repo(session):
    return SqlCounterpartyRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
def product_repo(session):
    return SqlProductRepository(session)


def make_legal_counterparty(
    *,
    email: str | None = None,
    inn: str | None = None,
) -> Counterparty:
    return Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name=f"Test Counterparty {uuid4()}",
        legal_name=f"Test Legal {uuid4()}",
        inn=Inn(inn or f"{uuid4().int % 10**10:010d}"),
        kpp=Kpp(f"{uuid4().int % 10**9:09d}"),
        phone=Phone("+70000000000"),
        email=email or f"counterparty-{uuid4()}@example.com",
        contact_persons=[],
        is_active=True,
    )


def make_product(name: str | None = None) -> SoftwareProduct:
    return SoftwareProduct(
        name=name or f"Product {uuid4()}",
        vendor="Test Vendor",
        category=ProductCategory.WEB,
        description="Test product",
        version="1.0",
        status=ProductStatus.ACTIVE,
        attributes={"kind": "test"},
    )


class TestSqlCounterpartyRepository:
    @pytest.mark.asyncio
    async def test_get_by_email_returns_head_counterparty(self, session, counterparty_repo):
        """
        Проверяем SQL-репозиторий контрагентов: он нужен, чтобы найти головного
        контрагента по email и не спутать его с филиалом.
        Данные: головной контрагент и филиал в реальной БД.
        """
        counterparty = make_legal_counterparty()
        branch = counterparty.create_branch(
            name="Branch",
            legal_name="Branch Legal",
            kpp=f"{uuid4().int % 10**9:09d}",
            phone="+70000000001",
            email=f"branch-{uuid4()}@example.com",
        )

        await counterparty_repo.create(counterparty)
        await counterparty_repo.create(branch)
        await session.commit()

        found_counterparty = await counterparty_repo.get_by_email(counterparty.email)
        found_branch = await counterparty_repo.get_by_email(branch.email)

        assert found_counterparty is not None
        assert found_counterparty.id == counterparty.id
        assert found_counterparty.parent_id is None
        assert found_branch is None

    @pytest.mark.asyncio
    async def test_get_by_email_returns_none(self, counterparty_repo):
        """
        Проверяем SQL-репозиторий контрагентов: он должен вернуть None,
        если головного контрагента с таким email нет.
        Данные: email, которого нет в реальной БД.
        """
        found_counterparty = await counterparty_repo.get_by_email(
            f"missing-{uuid4()}@example.com"
        )

        assert found_counterparty is None

    @pytest.mark.asyncio
    async def test_get_by_inn_returns_head_counterparty(self, session, counterparty_repo):
        """
        Проверяем SQL-репозиторий контрагентов: он нужен, чтобы найти головного
        контрагента по ИНН, даже если у него есть филиалы с тем же ИНН.
        Данные: головной контрагент и филиал в реальной БД.
        """
        inn = f"{uuid4().int % 10**10:010d}"
        counterparty = make_legal_counterparty(inn=inn)
        branch = counterparty.create_branch(
            name="Branch",
            legal_name="Branch Legal",
            kpp=f"{uuid4().int % 10**9:09d}",
            phone="+70000000001",
            email=f"branch-{uuid4()}@example.com",
        )

        await counterparty_repo.create(counterparty)
        await counterparty_repo.create(branch)
        await session.commit()

        found_counterparty = await counterparty_repo.get_by_inn(Inn(inn))

        assert found_counterparty is not None
        assert found_counterparty.id == counterparty.id
        assert found_counterparty.parent_id is None

    @pytest.mark.asyncio
    async def test_get_by_inn_returns_none(self, counterparty_repo):
        """
        Проверяем SQL-репозиторий контрагентов: он должен вернуть None,
        если головного контрагента с таким ИНН нет.
        Данные: ИНН, которого нет в реальной БД.
        """
        found_counterparty = await counterparty_repo.get_by_inn(Inn("9999999999"))

        assert found_counterparty is None

    @pytest.mark.asyncio
    async def test_get_with_descendants_returns_head_and_branches(
        self, session, counterparty_repo
    ):
        """
        Проверяем SQL-репозиторий контрагентов: он нужен, чтобы получить головного
        контрагента вместе с филиалами через recursive CTE.
        Данные: головной контрагент и два филиала в реальной БД.
        """
        counterparty = make_legal_counterparty()
        branches = [
            counterparty.create_branch(
                name=f"Branch {index}",
                legal_name=f"Branch Legal {index}",
                kpp=f"{uuid4().int % 10**9:09d}",
                phone="+70000000001",
                email=f"branch-{index}-{uuid4()}@example.com",
            )
            for index in range(EXPECTED_BRANCHES_COUNT)
        ]

        await counterparty_repo.create(counterparty)
        for branch in branches:
            await counterparty_repo.create(branch)
        await session.commit()

        descendants = await counterparty_repo.get_with_descendants(counterparty.id)

        found_ids = {item.id for item in descendants}
        assert len(descendants) == EXPECTED_TREE_ITEMS_COUNT
        assert counterparty.id in found_ids
        assert {branch.id for branch in branches}.issubset(found_ids)

    @pytest.mark.asyncio
    async def test_get_customers_returns_users_for_counterparty(
        self, session, counterparty_repo, user_repo
    ):
        """
        Проверяем SQL-репозиторий контрагентов: он нужен, чтобы получить страницу
        customer-пользователей, привязанных к конкретному контрагенту.
        Данные: два customer пользователя нужного контрагента и один пользователь другого.
        """
        counterparty = make_legal_counterparty()
        other_counterparty = make_legal_counterparty()
        await counterparty_repo.create(counterparty)
        await counterparty_repo.create(other_counterparty)
        await session.commit()

        first_customer = create_customer(
            email=f"customer-1-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty.id,
            user_role=UserRole.CUSTOMER,
        )
        second_customer = create_customer(
            email=f"customer-2-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty.id,
            user_role=UserRole.CUSTOMER_ADMIN,
        )
        other_customer = create_customer(
            email=f"customer-other-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=other_counterparty.id,
            user_role=UserRole.CUSTOMER,
        )
        await user_repo.create(first_customer)
        await user_repo.create(second_customer)
        await user_repo.create(other_customer)
        await session.commit()

        page = await counterparty_repo.get_customers(
            counterparty.id,
            Pagination(page=1, size=10),
        )

        found_ids = {user.id for user in page.items}
        assert page.total_items == EXPECTED_CUSTOMERS_COUNT
        assert found_ids == {first_customer.id, second_customer.id}
        assert other_customer.id not in found_ids

    @pytest.mark.asyncio
    async def test_get_customers_returns_empty_page(
        self,
        session,
        counterparty_repo,
    ):
        """
        Проверяем SQL-репозиторий контрагентов: он должен вернуть пустую страницу,
        если у контрагента пока нет customer-пользователей.
        Данные: головной контрагент в реальной БД без связанных пользователей.
        """
        counterparty = make_legal_counterparty()
        await counterparty_repo.create(counterparty)
        await session.commit()

        page = await counterparty_repo.get_customers(
            counterparty.id,
            Pagination(page=1, size=10),
        )

        assert page.items == []
        assert page.total_items == 0
        assert page.page == 1
        assert page.size == 10

    @pytest.mark.asyncio
    async def test_get_products_returns_linked_products(
        self,
        session,
        counterparty_repo,
        product_repo,
    ):
        """
        Проверяем SQL-репозиторий контрагентов: он должен вернуть продукты,
        связанные с конкретным контрагентом через таблицу counterparty_products.
        Данные: два продукта нужного контрагента и один продукт без связи.
        """
        counterparty = make_legal_counterparty()
        await counterparty_repo.create(counterparty)

        first_product = make_product()
        second_product = make_product()
        unlinked_product = make_product()

        await product_repo.create(first_product)
        await product_repo.create(second_product)
        await product_repo.create(unlinked_product)
        await session.commit()

        await counterparty_repo.link_product(counterparty.id, first_product.id)
        await counterparty_repo.link_product(counterparty.id, second_product.id)
        await session.commit()

        page = await counterparty_repo.get_products(
            counterparty.id,
            Pagination(page=1, size=10),
        )

        found_ids = {product.id for product in page.items}
        assert page.total_items == 2
        assert found_ids == {first_product.id, second_product.id}
        assert unlinked_product.id not in found_ids

    @pytest.mark.asyncio
    async def test_get_products_returns_empty_page(
        self,
        session,
        counterparty_repo,
    ):
        """
        Проверяем SQL-репозиторий контрагентов: он должен вернуть пустую страницу,
        если у контрагента нет связанных программных продуктов.
        Данные: головной контрагент в реальной БД без записей в counterparty_products.
        """
        counterparty = make_legal_counterparty()
        await counterparty_repo.create(counterparty)
        await session.commit()

        page = await counterparty_repo.get_products(
            counterparty.id,
            Pagination(page=1, size=10),
        )

        assert page.items == []
        assert page.total_items == 0
        assert page.page == 1
        assert page.size == 10
