from typing import Any, Literal

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .domain.vo import ProductCategory, ProductStatus


class ProductBase(BaseModel):
    """Базовая API схема программного продукта"""

    name: str = Field(..., description="Полное наименование", examples=["1С УНФ"])
    vendor: str = Field(..., description="Вендор ПО", examples=["1С"])
    category: ProductCategory = Field(..., description="Категория программного продукта")
    description: str | None = Field(None, description="Описание")
    version: str | None = Field(None, description="Версия", examples=["3.0.1"])
    status: ProductStatus = Field(..., description="Статус в справочнике")

    attributes: dict[str, Any] = Field(default_factory=dict, description="Специальные аттрибуты")


class ProductResponse(ProductBase):
    """API схема ответа программного продукта"""

    id: UUID = Field(..., description="Уникальный ID продукта")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    display_name: str = Field(..., description="Человеко-читаемое имя для UI")

    created_by: UUID | None = Field(None, description="Тот кто создал запись в справочнике")
    updated_by: UUID | None = Field(None, description="Тот кто обновил запись в справочнике")


class ProductCreate(ProductBase):
    """API схема для создания программного продукта"""


class ProductFilters(BaseModel):
    """Фильтры продуктов"""

    category: ProductCategory | None = Field(None, description="По категории")
    status: ProductStatus | None = Field(None, description="По статусу")
    query: str | None = Field(None, description="Запрос для полнотекстового поиска")


# Динамические поля для конфигураций программных продуктов


class BaseAttributes(BaseModel):
    """Базовая конфигурация для всех категорий"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"additionalProperties": False}
    )


class ErpAttributes(BaseAttributes):
    """Аттрибуту для ERP-систем"""

    environment: Literal["production", "staging", "development", "test"] = Field(
        default="production", description="Среда развертывания"
    )
    license_type: Literal["cloud", "on-premise", "subscription", "perpetual"] = Field(
        ..., description="Тип лицензирования"
    )
    db_connection_ref: str | None = Field(
        None, description="ID или ссылка на подключение к БД (без паролей/секретов)"
    )
    modules_enabled: list[str] | None = Field(
        None, description="Активные модули/конфигурации (CRM, склад, бухгалтерия, HR)"
    )
    max_concurrent_users: int | None = Field(
        None, description="Лимит одновременных пользовательских сессий"
    )
    integration_points: list[str] | None = Field(
        None, description="Внешние интеграции (API-шлюзы, EDI, почта, банки)"
    )
    backup_policy_ref: str | None = Field(
        None, description="Ссылка на регламент или ID задачи резервного копирования"
    )


class WebAttributes(BaseAttributes):
    """Аттрибуты для WEB приложений"""

    environment: Literal["production", "staging", "development", "test"] = Field(
        default="production"
    )
    base_url: str | None = Field(
        None, description="Основной URL продукта", examples=["https://portal.example.com"]
    )
    admin_url: str | None = Field(None, description="URL панели администратора/консоли")
    hosting_provider: str | None = Field(
        None, description="Провайдер хостинга/облака (AWS, GCP, Timeweb, Vercel)"
    )
    tech_stack: list[str] | None = Field(
        None, description="Технический стек", examples=[["Django", "PostgreSQL", "Nginx"]]
    )
    ssl_expiry_date: date | None = Field(None, description="Дата истечения SSL/TLS сертификата")
    cdn_enabled: bool = Field(default=False, description="Используется ли CDN")
    cms_or_platform: str | None = Field(
        None,
        description="CMS или базовая платформа",
        examples=["WordPress", "Strapi", "Next.js", "Bitrix"]
    )


class MobileAttributes(BaseAttributes):
    """Аттрибуты для мобильных приложений"""

    platform: Literal["ios", "android", "cross-platform"] = Field(
        ..., description="Целевая платформа"
    )
    app_store_url: str | None = Field(None, description="Ссылка на App Store")
    google_play_url: str | None = Field(None, description="Ссылка на Google Play")
    min_os_version: str | None = Field(
        None, description="Минимальная поддерживаемая версия ОС", examples=["iOS 15", "Android 12"]
    )
    sdk_framework: str | None = Field(
        None,
        description="Фреймворк/SDK",
        examples=["Flutter", "React Native", "Swift", "Kotlin", "Expo"]
    )
    push_provider: str | None = Field(
        None,
        description="Провайдер пуш-уведомлений (FCM, APNs, Firebase)",
        examples=["FCM", "APNs", "Firebase"]
    )
    backend_api_version: str | None = Field(
        None, description="Версия backend API, с которой совместима сборка"
    )


class ApiAttributes(BaseAttributes):
    """Аттрибуты для API"""

    base_url: str | None = Field(None, description="Базовый URL сервиса")
    swagger_url: str | None = Field(None, description="Ссылка на OpenAPI/Swagger документацию")
    auth_method: Literal["OAuth2", "API-Key", "JWT", "mTLS", "Basic", "None"] = Field(
        default="JWT", description="Основной метод авторизации"
    )
    rate_limit: str | None = Field(
        None, description="Лимит запросов", examples=["1000 req/min", "10k/day"]
    )
    versioning_strategy: Literal["path", "header", "query", "none"] = Field(
        default="path", description="Стратегия версионирования эндпоинтов"
    )
    webhook_endpoints: list[str] | None = Field(None, description="URL для webhook-уведомлений")
    health_check_url: str | None = Field(
        None,
        description="URL эндпоинта проверки здоровья",
        examples=["/health", "/ping"]
    )
    data_format: Literal["JSON", "XML", "gRPC", "GraphQL", "CSV"] = Field(
        default="JSON", description="Формат обмена данными"
    )


class DesktopAttributes(BaseAttributes):
    """Аттрибуты для desktop приложений"""

    os_compatibility: list[str] | None = Field(
        None,
        description="Поддерживаемые ОС",
        examples=["Windows 10/11", "macOS 12+", "Ubuntu 22.04"]
    )
    architecture: Literal["x86_64", "ARM64", "Universal"] | None = Field(
        None, description="Архитектура сборки"
    )
    default_install_path: str | None = Field(None, description="Путь установки по умолчанию")
    runtime_dependencies: list[str] | None = Field(
        None,
        description="Зависимости",
        examples=[[".NET 8", "Java 17", "Electron 28", "MSVC Redist"]]
    )
    auto_update_enabled: bool = Field(
        False, description="Включено ли автоматическое обновление"
    )
    distribution_method: Literal[
                             "MSI", "EXE", "DMG", "PKG", "AppImage", "Winget", "Manual"
                         ] | None = None
    license_type: Literal["perpetual", "subscription", "trial", "freeware"] | None = None


class HardwareAttributes(BaseAttributes):
    """Серверы, сетевое оборудование, IoT, периферия, принтеры"""

    model_sku: str | None = Field(None, description="Модель / SKU / Артикул производителя")
    firmware_version: str | None = Field(None, description="Версия прошивки/микрокода")
    network_config: Literal["static", "dhcp", "pppoe", "mac-bound"] | None = Field(
        None, description="Тип сетевой конфигурации"
    )
    physical_location: str | None = Field(
        None, description="Местоположение (Офис 3, Стойка A2, Склад Б)"
    )
    warranty_expiry: date | None = Field(None, description="Дата окончания заводской гарантии")
    maintenance_contract_ref: str | None = Field(
        None, description="ID или ссылка на договор SLA/ТО"
    )
    monitoring_agent: str | None = Field(
        None, description="Агент мониторинга", examples=["SNMP community", "Zabbix host"]
    )
    serial_prefix_pattern: str | None = Field(
        None, description="Маска/префикс серийных номеров для инвентаризации"
    )


class OtherAttributes(BaseAttributes):
    """Прочее / Кастомные продукты"""

    notes: str | None = Field(None, description="Свободные заметки администратора")
    support_group: str | None = Field(
        None, description="Группа или контакт ответственной поддержки"
    )


# Реестр схем для валидации и генерации форм
CATEGORY_ATTRIBUTES_SCHEMA = {
    ProductCategory.ERP: ErpAttributes,
    ProductCategory.WEB: WebAttributes,
    ProductCategory.MOBILE: MobileAttributes,
    ProductCategory.API: ApiAttributes,
    ProductCategory.DESKTOP: DesktopAttributes,
    ProductCategory.HARDWARE: HardwareAttributes,
    ProductCategory.OTHER: OtherAttributes,
}


def get_product_attributes_schema(category: ProductCategory) -> dict[str, Any]:
    # 1. Получение модели схемы
    model_cls = CATEGORY_ATTRIBUTES_SCHEMA.get(category)
    if model_cls is None:
        raise ValueError(f"Unknown product category {category}")

    # 2. Генерация JSON Schema + UI-подсказки
    schema = model_cls.model_json_schema(ref_template="#/$defs/{model}", mode="serialization")

    # 3. Добавление человеко-читаемого описания для frontend
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    return schema


def validate_product_attributes(category: ProductCategory, attributes: dict[str, Any]) -> None:
    model_cls = CATEGORY_ATTRIBUTES_SCHEMA.get(category)
    if model_cls is None:
        return

    try:
        model_cls.model_validate(attributes)
    except ValidationError as e:
        raise ValueError(f"Invalid {category} attributes: {e}") from e


class AttributesSchemaResponse(BaseModel):
    """API схема ответа для аттрибутов продукта"""

    category: ProductCategory
    schema: dict[str, Any]
