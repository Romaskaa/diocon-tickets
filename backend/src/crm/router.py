from typing import Annotated, Any

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from pydantic import EmailStr

from ..iam.dependencies import get_current_user, require_role
from ..iam.domain.constants import CUSTOMER_ADMIN_AND_ABOVE, SUPPORT_MANAGER_OR_ABOVE, SUPPORT_TEAM
from ..iam.mappers import map_user_to_response
from ..iam.schemas import UserResponse
from ..products.mappers import map_product_to_response
from ..products.schemas import ProductResponse
from ..shared.dependencies import PaginationDep
from ..shared.domain.exceptions import NotFoundError
from ..shared.schemas import Page
from .dependencies import CounterpartyFiltersDep, CounterpartyRepoDep, CounterpartyServiceDep
from .mappers import map_counterparty_to_response
from .schemas import (
    BranchAdd,
    ContactPersonIn,
    CounterpartyCreate,
    CounterpartyEdit,
    CounterpartyResponse,
)

router = APIRouter(prefix="/counterparties", tags=["Контрагенты"])


@router.post(
    path="",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Создание контрагента",
)
async def create_counterparty(
        data: CounterpartyCreate, service: CounterpartyServiceDep
) -> CounterpartyResponse:
    return await service.create(data)


@router.get(
    path="/{counterparty_id}",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)],
    summary="Получение контрагента",
)
async def get_counterparty(
        counterparty_id: UUID, repository: CounterpartyRepoDep
) -> CounterpartyResponse:
    counterparty = await repository.read(counterparty_id)
    if counterparty is None:
        raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")
    return map_counterparty_to_response(counterparty)


@router.post(
    path="/{counterparty_id}",
    response_model=CounterpartyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Добавление обособленного подразделения",
)
async def add_branch(
        counterparty_id: Annotated[
            UUID,
            Path(..., description="ID контрагента, к которому нужно привязать нового")
        ],
        data: BranchAdd,
        service: CounterpartyServiceDep
) -> CounterpartyResponse:
    return await service.add_branch(counterparty_id, data)


@router.patch(
    path="/{counterparty_id}",
    status_code=status.HTTP_200_OK,
    response_model=CounterpartyResponse,
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Отредактировать контрагента",
)
async def edit_counterparty(
        counterparty_id: UUID, data: CounterpartyEdit, service: CounterpartyServiceDep
) -> CounterpartyResponse:
    return await service.edit(counterparty_id, data)


@router.get(
    path="",
    response_model=Page[CounterpartyResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Получение списка контрагентов",
)
async def get_counterparties(
        params: PaginationDep, filters: CounterpartyFiltersDep, repository: CounterpartyRepoDep
) -> Page[CounterpartyResponse]:
    page = await repository.paginate(
        params,
        query=filters.query,
        email=filters.email,
        inn=filters.inn,
    )
    return page.to_response(map_counterparty_to_response)


@router.delete(
    path="/{counterparty_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(*SUPPORT_MANAGER_OR_ABOVE))],
    summary="Удаление контрагента",
    description="Soft-delete метод, делает контрагента не активным не удаляя фактически"
)
async def delete_counterparty(counterparty_id: UUID, repository: CounterpartyRepoDep) -> None:
    await repository.update(counterparty_id, is_active=False)


@router.post(
    path="/{counterparty_id}/contact-persons",
    status_code=status.HTTP_201_CREATED,
    response_model=CounterpartyResponse,
    dependencies=[Depends(require_role(*SUPPORT_MANAGER_OR_ABOVE))],
    summary="Добавление контактного лица контрагента"
)
async def add_contact_person(
        counterparty_id: UUID, data: ContactPersonIn, service: CounterpartyServiceDep
) -> CounterpartyResponse:
    return await service.add_contact_person(counterparty_id, data)


@router.delete(
    path="/{counterparty_id}/contact-persons",
    status_code=status.HTTP_200_OK,
    response_model=CounterpartyResponse,
    dependencies=[Depends(require_role(*SUPPORT_MANAGER_OR_ABOVE))],
    summary="Удаление контактного лица"
)
async def delete_contact_person(
        counterparty_id: UUID,
        phone: Annotated[str, Query(..., description="Номер телефона")],
        email: Annotated[EmailStr, Query(..., description="Email адрес")],
        service: CounterpartyServiceDep,
) -> CounterpartyResponse:
    return await service.delete_contact_person(counterparty_id, phone, email)


@router.get(
    path="/{counterparty_id}/customers",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserResponse],
    dependencies=[Depends(require_role(*CUSTOMER_ADMIN_AND_ABOVE))],
    summary="Получение клиентов контрагента",
    description="Доступно с ролью `customer_admin` и выше",
)
async def get_counterparty_customers(
        counterparty_id: UUID, params: PaginationDep, repository: CounterpartyRepoDep
) -> Page[dict[str, Any]]:
    page = await repository.get_customers(counterparty_id, params)
    return page.to_response(map_user_to_response)


@router.post(
    path="/{counterparty_id}/products",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(*SUPPORT_MANAGER_OR_ABOVE))],
    summary="Привязка программного продукта к контрагенту"
)
async def link_counterparty_product(
        counterparty_id: UUID,
        product_id: Annotated[
            UUID, Body(..., embed=True, description="ID продукта из справочника")
        ],
        service: CounterpartyServiceDep,
) -> dict[str, str]:
    await service.link_product(counterparty_id, product_id)
    return {"message": "Software product linked successfully"}


@router.get(
    path="/{counterparty_id}/products",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProductResponse],
    dependencies=[Depends(get_current_user)],
    summary="Получение программных продуктов контрагента"
)
async def get_counterparty_products(
        counterparty_id: UUID,
        pagination: PaginationDep,
        repository: CounterpartyRepoDep
) -> Page[ProductResponse]:
    page = await repository.get_products(counterparty_id, pagination)
    return page.to_response(map_product_to_response)
