from typing import Annotated

from fastapi import Depends

from ..core.broker import broker
from ..iam.dependencies import UserRepoDep
from ..projects.dependencies import MembershipRepoDep
from ..shared.dependencies import SessionDep, get_mail_sender
from ..tickets.domain.events import TicketAssigned, TicketCreated
from .channels import EmailChannel, InAppChannel, NotificationChannel
from .domain.repos import NotificationRepository, PreferenceRepository
from .infra.repos import SqlNotificationRepository, SqlUserPreferenceRepository
from .policies import TicketAssignedPolicy, TicketCreatedPolicy
from .resolvers import ChannelResolver, TargetResolver
from .services import NotificationService


def get_target_resolver(
        user_repo: UserRepoDep,
        project_membership_repo: MembershipRepoDep,
) -> TargetResolver:
    target_resolver = TargetResolver()

    target_resolver.registry_policy(
        TicketCreated, TicketCreatedPolicy(project_membership_repo, user_repo),
    )
    target_resolver.registry_policy(
        TicketAssigned, TicketAssignedPolicy(),
    )

    return target_resolver


def get_email_channel(user_repo: UserRepoDep) -> NotificationChannel:
    return EmailChannel(mail_sender=get_mail_sender(), user_repo=user_repo)


in_app_channel = InAppChannel(broker)


def get_notification_repo(session: SessionDep) -> SqlNotificationRepository:
    return SqlNotificationRepository(session)


def get_preference_repo(session: SessionDep) -> SqlUserPreferenceRepository:
    return SqlUserPreferenceRepository(session)


NotificationRepoDep = Annotated[NotificationRepository, Depends(get_notification_repo)]
PreferenceRepoDep = Annotated[PreferenceRepository, Depends(get_preference_repo)]


def get_channel_resolver(
        preference_repo: PreferenceRepoDep,
        email_channel: Annotated[NotificationChannel, Depends(get_email_channel)],
) -> ChannelResolver:
    return ChannelResolver(preference_repo, email_channel, in_app_channel)


def get_notification_service(
        session: SessionDep,
        repository: NotificationRepoDep,
        channel_resolver: ChannelResolver = Depends(get_channel_resolver),
) -> NotificationService:
    return NotificationService(session, repository, channel_resolver)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
