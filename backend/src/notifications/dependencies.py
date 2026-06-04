from typing import Annotated

from fastapi import Depends

from ..iam.dependencies import UserRepoDep
from ..shared.dependencies import SessionDep, get_mail_sender
from ..tickets.dependencies import ProjectRepoDep
from ..tickets.domain.events import TicketCreated
from .channels import EmailChannel, NotificationChannel
from .domain.repos import NotificationRepository, PreferenceRepository
from .policies import TicketCreatedPolicy
from .resolvers import ChannelResolver, TargetResolver
from .services import NotificationService


def get_target_resolver(
        user_repo: UserRepoDep,
        project_repo: ProjectRepoDep
) -> TargetResolver:
    target_resolver = TargetResolver()
    target_resolver.registry_policy(
        TicketCreated, TicketCreatedPolicy(project_repo, user_repo),
    )
    return target_resolver


def get_email_channel(user_repo: UserRepoDep) -> NotificationChannel:
    return EmailChannel(mail_sender=get_mail_sender(), user_repo=user_repo)


def get_notification_repo(session: SessionDep) -> NotificationRepository:
    ...


def get_preference_repo(session: SessionDep) -> PreferenceRepository:
    ...


NotificationRepoDep = Annotated[NotificationRepository, Depends(get_notification_repo)]
PreferenceRepoDep = Annotated[PreferenceRepository, Depends(get_preference_repo)]


def get_channel_resolver(
        preference_repo: PreferenceRepoDep,
        email_channel: Annotated[NotificationChannel, Depends(get_email_channel)],
) -> ChannelResolver:
    return ChannelResolver(preference_repo, email_channel)


def get_notification_service(
        session: SessionDep,
        repository: NotificationRepoDep,
        channel_resolver: ...,
) -> NotificationService:
    ...


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
