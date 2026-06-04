from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.security import OAuth2PasswordRequestForm

from ..dependencies import AuthServiceDep, CurrentUserDep, oauth2_scheme
from ..schemas import CurrentUser, LogoutRequest, Tokens, TokensRefresh, UserCreateForm

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    path="/register/{token}",
    status_code=status.HTTP_201_CREATED,
    response_model=Tokens,
    summary="Регистрация пользователя по приглашению"
)
async def register(
        token: Annotated[str, Path(..., description="Токен из пригласительного письма")],
        data: UserCreateForm,
        service: AuthServiceDep,
) -> Tokens:
    return await service.register(token, data)


@router.post(
    path="/login",
    status_code=status.HTTP_200_OK,
    response_model=Tokens,
    summary="Вход в учётную запись"
)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        service: AuthServiceDep,
) -> Tokens:
    return await service.authenticate(form_data.username, form_data.password)


@router.post(
    path="/refresh",
    status_code=status.HTTP_200_OK,
    response_model=Tokens,
    summary="Обновление пары токенов"
)
async def refresh(data: TokensRefresh, service: AuthServiceDep) -> Tokens:
    return await service.refresh_tokens(data.refresh_token)


@router.post(
    path="/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из аккаунта"
)
async def logout(
        access_token: Annotated[str, Depends(oauth2_scheme)],
        data: LogoutRequest,
        service: AuthServiceDep
) -> None:
    return await service.logout(access_token, data.refresh_token)


@router.get(
    path="/userinfo",
    response_model=CurrentUser,
    status_code=status.HTTP_200_OK,
    summary="Получение информации о пользователе",
    description="Информация берётся только из токена (не требует запроса к БД)"
)
async def get_userinfo(current_user: CurrentUserDep) -> CurrentUser:
    return current_user
