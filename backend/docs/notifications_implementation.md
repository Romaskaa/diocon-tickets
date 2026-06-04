# Реализация модуля нотификации

## Общая архитектура

```mermaid
graph TD
    A[Domain Event<br/>TicketCreated / CommentAdded] --> B[NotificationHandler]
    B --> C[TargetResolver.get_targets]
    C --> D[NotificationFactory.create]
    D --> E[Notification Entity]
    E --> F[NotificationRepository.save]
    F --> G[ChannelResolver]
    G --> H[EmailChannel]
    G --> I[SSEChannel]
    G --> J[Future: Telegram / Push]
```
