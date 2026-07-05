from typing import Any, Awaitable, Callable

from bcf.core.bcdantic import UUID4, mongo_serializer
from bcf.core.common import EntityStatuses
from bcf.core.dtoly.dtos import CreateDTO, GetDTO, UpdateDTO
from bcf.core.fastapi_addons import conflict_handler
from bcf.core.mongo.mongo_base_model import MongoBaseModel


async def create_wrapper(func: ..., dto: ..., **kwargs):
    # Что то до создания
    await func(dto, **kwargs)
    # Что то после создания


class Crud[
    EntityModel: MongoBaseModel,
    CreateEntityDTO: CreateDTO,
    GetEntityDTO: GetDTO,
    UpdateEntityDTO: UpdateDTO,
    OptionalEntityDTO: UpdateDTO,
    CreateOptionsT,
    GetOptionsT,
    FindOptionsT,
    UpdateOptionsT,
    DeleteOptionsT,
]:
    def __init__(
        self,
        model: type[EntityModel],
        optional_dto: type[OptionalEntityDTO],
        create_wrapper: Callable[
            [
                Callable[[dict[str, Any] | None], Awaitable[EntityModel]],
                CreateEntityDTO,
                CreateOptionsT | None,
            ],
            Awaitable[EntityModel],
        ]
        | None = None,
        get_wrapper: Callable[
            [Callable[[], Awaitable[EntityModel | None]], UUID4, GetOptionsT | None],
            Awaitable[EntityModel | None],
        ]
        | None = None,
        find_wrapper: Callable[
            [Callable[[dict[str, Any] | None], Awaitable[list[OptionalEntityDTO]]], GetEntityDTO, FindOptionsT | None],
            Awaitable[list[OptionalEntityDTO]],
        ]
        | None = None,
        update_wrapper: Callable[
            [
                Callable[[dict[str, Any] | None], Awaitable[EntityModel]],
                EntityModel,
                UpdateEntityDTO,
                UpdateOptionsT | None,
            ],
            Awaitable[EntityModel],
        ]
        | None = None,
        delete_wrapper: Callable[
            [Callable[[], Awaitable[None]], EntityModel, DeleteOptionsT | None],
            Awaitable[None],
        ]
        | None = None,
    ):
        """
        Общий класс CRUD для моделей.

        :param model: Класс модели, для которой создаётся CRUD.
        :param create_wrapper: Обёртка для create.
        :param get_wrapper: Обёртка для get.
        :param find_wrapper: Обёртка для find.
        :param update_wrapper: Обёртка для update.
        :param delete_wrapper: Обёртка для delete.
        """
        self._model = model
        self._optional_dto = optional_dto
        self._create_wrapper = create_wrapper
        self._get_wrapper = get_wrapper
        self._find_wrapper = find_wrapper
        self._update_wrapper = update_wrapper
        self._delete_wrapper = delete_wrapper

    async def create(
        self,
        dto: CreateEntityDTO,
        options: CreateOptionsT | None = None,
    ) -> EntityModel:
        """
        Создаёт новый объект модели.

        :param create_dto: DTO для создания объекта.
        :return: Созданный объект модели.
        """

        async def base_create(additional_fields: dict[str, Any] | None = None) -> EntityModel:
            additional_fields = additional_fields or {}

            async with conflict_handler():
                if result := await self._model.gc().insert_one(
                    self._model.model_validate(
                        {
                            **dto.model_dump(by_alias=True),
                            **additional_fields,
                        },
                        from_attributes=True,
                        by_alias=True,
                    ),
                ):
                    return result
                raise

        if self._create_wrapper:
            return await self._create_wrapper(base_create, dto, options)
        return await base_create()

    async def get(
        self,
        obj_id: Any,
        options: GetOptionsT | None = None,
    ) -> EntityModel | None:
        """
        Возвращает объект модели по sid.

        :param obj_sid: Sid объекта.
        :return: Объект модели.
        """

        async def base_get() -> EntityModel | None:
            _filter = {"_id": obj_id}
            if "status" in self._model.model_fields:
                _filter["status"] = {"$in": [EntityStatuses.active.value, EntityStatuses.blocked.value]}

            return await self._model.gc().find_one(_filter)

        if self._get_wrapper:
            return await self._get_wrapper(base_get, obj_id, options)
        return await base_get()

    async def find(
        self,
        dto: GetEntityDTO,
        options: FindOptionsT | None = None,
    ) -> list[OptionalEntityDTO]:
        """
        Возвращает список объектов модели.
        Этот метод использовать только для api, т.к. он возвращает OptionalEnitytyDTO

        :param get_dto: DTO для получения объектов.
        :return: Список объектов модели.
        """

        async def base_find(and_filter: dict[str, Any] | None = None) -> list[OptionalEntityDTO]:
            return await dto.find(self._optional_dto, and_filter=and_filter)  # type: ignore

        if self._find_wrapper:
            return await self._find_wrapper(base_find, dto, options)
        return await base_find()

    async def update(
        self,
        obj: EntityModel,
        dto: UpdateEntityDTO,
        options: UpdateOptionsT | None = None,
    ) -> EntityModel:
        """
        Обновляет переданный объект модели.

        :param obj: Объект модели для обновления.
        :param update_dto: DTO для обновления объекта.
        :return: Список объектов модели.
        """

        async def base_update(additional_fields: dict[str, Any] | None = None) -> EntityModel:
            return await dto.update_one_and_find_one(
                obj.sid,
                self._model,
                additional_fields=additional_fields,
            )

        if self._update_wrapper:
            return await self._update_wrapper(base_update, obj, dto, options)
        return await base_update()

    async def delete(
        self,
        obj: EntityModel,
        options: DeleteOptionsT | None = None,
    ) -> None:
        """
        Удаляет объект модели либо помечает как удаленный (при наличии поля status в модели)

        :param obj: Объект модели для удаления.
        """

        async def base_delete() -> None:
            if "status" in self._model.model_fields:
                await self._model.gc().update_one(
                    {"_id": obj.sid},
                    {"$set": {"status": EntityStatuses.deleted}},
                )
            else:
                await self._model.gc().c.delete_one({"_id": mongo_serializer(obj.sid)})

        if self._delete_wrapper:
            await self._delete_wrapper(base_delete, obj, options)
        await base_delete()


crud = Crud[..., ..., ..., ...](create_wrapper=create_wrapper)
