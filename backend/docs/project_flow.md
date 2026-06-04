# Жизненный цикл проекта

```mermaid
flowchart TD
    A[Идея / Запрос на проект] --> B[Создание проекта]
    B --> C[Настройка проекта]
    C --> D[Добавление участников]
    D --> E[Создание тикетов внутри проекта]
    E --> F[Работа над тикетами]
    F --> G[Завершение / Архивация проекта]
```

## Подробное описание жизненного цикла

| Этап            | Кто создаёт / выполняет | Что происходит                                                     | Статус проекта |
|-----------------|-------------------------|--------------------------------------------------------------------|----------------|
| Создание        | Support Manager / Admin | Создаётся проект, указывается название, ключ, контрагент, владелец | ACTIVE         |
| Настройка       | Owner проекта + Manager | Добавляются участники, настраиваются права, workflow (опционально) | ACTIVE         |
| Активная работа | Все участники проекта   | Создаются тикеты, ведётся работа, добавляются комментарии          | ACTIVE         |
| On Hold         | Owner / Manager         | Проект временно приостановлен (например, клиент не отвечает)       | ON_HOLD        |
| Завершение      | Owner / Manager         | Все тикеты закрыты, проект отмечается как завершённый              | COMPLETED      |
| Архивация       | Manager / Admin         | Проект больше не активен, тикеты доступны только для чтения        | ARCHIVED       |

## Взаимодействие клиента с проектом

| Действие                   | Customer         | Customer Admin                     | Support Agent      | Support Manager |
|----------------------------|------------------|------------------------------------|--------------------|-----------------|
| Видеть тикеты проекта      | Только свои      | Все тикеты проекта                 | Все тикеты проекта | Все             |
| Создавать тикеты в проекте | Да               | Да                                 | Да                 | Да              |
| Комментировать тикеты      | Только публичные | Публичные + internal (ограниченно) | Да                 | Да              |
| Назначать исполнителя      | Нет              | Нет                                | Да                 | Да              |
| Менять статус тикета       | Нет              | Нет                                | Да                 | Да              |
| Добавлять других клиентов  | Нет              | Нет                                | Нет                | Да              |

## Создание тикета в проекте

```mermaid
sequenceDiagram
    participant Client as Клиент / Агент
    participant API as Ticket API
    participant Service as TicketService
    participant Domain as Ticket (Aggregate)
    participant Repo as TicketRepository
    participant ProjectRepo as ProjectRepository

    Client->>API: POST /projects/{project_id}/tickets
    API->>Service: create_ticket(data, project_id, current_user)

    Service->>ProjectRepo: get_by_id(project_id)
    ProjectRepo-->>Service: Project

    Service->>Service: Проверить права пользователя в проекте

    Service->>Domain: Ticket.create(...)
    Domain-->>Service: Ticket (с project_id)

    Service->>Repo: create(ticket)
    Repo-->>Service: OK

    Service->>Service: Опубликовать события (TicketCreated)
    Service-->>API: TicketResponse
```
