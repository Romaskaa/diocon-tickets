from enum import StrEnum


class ProductCategory(StrEnum):
    """Категории программных продуктов"""

    ERP = "ERP"  # 1C, SAP, Oracle
    WEB = "WEB"  # Сайты, порталы, лендинги
    MOBILE = "MOBILE"  # IOS, Android приложения
    API = "API"  # REST, GraphQL, SOAP сервисы и интеграции
    DESKTOP = "DESKTOP"  # Локальные программы
    HARDWARE = "HARDWARE"  # Серверы, принтеры, IOT устройства
    OTHER = "OTHER"  # прочее


class ProductStatus(StrEnum):
    """Жизненный цикл продукта в каталоге"""

    ACTIVE = "active"  # Доступен для выбора в новых тикетах
    BETA = "beta"  # Тестовая версия, доступна ограниченному кругу
    DEPRECATED = "deprecated"  # Больше не поддерживается, но есть в старых тикетах
    ARCHIVED = "archived"  # Полностью удален из поиска, только для истории


class EnvironmentType(StrEnum):
    """Тип окружения в котором работает продукт"""

    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TESTING = "testing"
