from datetime import timedelta
from decimal import Decimal
from typing import Annotated, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status, Body
from fastapi.security import OAuth2PasswordRequestForm

from .fingerprint import FingerprintExists, InvalidFingerprint
from .oauth.vk import get_access_token
from .schemas import ReadProfile, ReferralsStatistics, RegisterUser
from .security import (ACCESS_TOKEN_EXPIRE_MINUTES, Token, create_access_token,
                       credentials_exception, decode_token, get_password_hash,
                       oauth2_scheme, verify_password)
from .service import ReferralsService, UserService

import logging

# Настройка логгера
logger = logging.getLogger(__name__)

router = APIRouter()

# Модель для обработки JSON с полем `code`
class CodeRequest(BaseModel):
    code: str

async def authenticate_user(username: str, password: str):
    async with UserService() as service:
        user = await service.get_user_by_username(username)
    if not user:
        return False

    if not verify_password(password, user.password):
        return False

    return user

def get_jwt_token(user) -> Token:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    token_data = decode_token(token)
    async with UserService() as service:
        user = await service.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[ReadProfile, Depends(get_current_user)],
):
    if not current_user.active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def _register_user(
    username: str,
    password: str,
    fingerprint: str,
    vk_id: Optional[str] = None,
    referrer_id: Optional[int] = None
):
    try:
        async with UserService() as service:
            new_user = await service.register_user(RegisterUser(
                username=username,
                password=password,
                fingerprint=fingerprint,
                vk_id=vk_id,
                referrer_id=referrer_id
            ))

            # Увеличение referral_count у реферера
            if referrer_id:
                referrer = await service.get_user_by_id(referrer_id)
                if referrer and referrer.referral_count is not None:
                    referrer.referral_count += 1
                    await service.update_user(referrer)

            return get_jwt_token(new_user)
    except InvalidFingerprint:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Invalid fingerprint provided')
    except FingerprintExists:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'This device has already been used for registration')
        

@router.post(
    '/users/register',
    response_model=Token,
    tags=['Users']
)
async def register_user(
    username: str = Form(max_length=16),
    password: str = Form(min_length=8, max_length=32),
    fingerprint: str = Form(description='JSON fingerprint object retreived with fingerprint.js as string'),
    referrer_id: int = Query(None)
):
    return await _register_user(username, password, fingerprint, referrer_id=referrer_id)

@router.post(
    '/users/auth/token',
    tags=['Users']
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_jwt_token(user)

@router.get(
    '/users/me',
    response_model=ReadProfile,
    tags=['Users']
)
async def read_my_profile(
    me: ReadProfile = Depends(get_current_active_user)
):
    return me

@router.patch(
    '/users/me/update-password',
    tags=['Users']
)
async def change_password(
    old_password: str = Form(),
    new_password: str = Form(),
    user: ReadProfile = Depends(get_current_active_user)
):
    new_password = get_password_hash(new_password)
    async with UserService() as service:
        db_user = await service.get_user_by_id(user.id)

        if not verify_password(old_password, db_user.password):
            return HTTPException(status.HTTP_401_UNAUTHORIZED, 'Wrong password')

        await service.change_password(user.id, new_password)

        return {}

@router.patch(
    '/users/me/update-avatar',
    tags=['Users']
)
async def update_avatar(
    avatar_id: int = Query(),
    user: ReadProfile = Depends(get_current_active_user)
):
    # TODO: List of available avatars and methods to manage and use avatars
    async with UserService() as service:
        db_user = await service.update_avatar(user.id, avatar_id)
        return ReadProfile.model_validate(db_user)

@router.get(
    '/users/oauth/vk/register',
    response_model=Token,
    tags=['VK']
)
async def register_with_vk_oauth(
    password: str = Form(),
    fingerprint: str = Form(),
    code: str = Form(description='Code from VK OAuth response'),
    referrer_id: int = Query(None)
):
    access_token = await get_access_token(code)
    vk_id = access_token.user_id
    return await _register_user(f'user_{vk_id}', password, fingerprint, vk_id, referrer_id)

@router.get(
    '/users/oauth/vk/login',
    tags=['VK']
)
async def login_with_vk_oauth(
    code: str = Form(description='Code from VK OAuth response')
) -> Token:
    access_token = await get_access_token(code)
    async with UserService() as service:
        user = await service.get_user_by_vk_id(access_token.user_id)
        return get_jwt_token(user)

@router.post('/users/oauth/vk/link')
async def link_vk(
    code_request: CodeRequest,  # Принимаем JSON-объект с полем `code`
    me: ReadProfile = Depends(get_current_active_user)
) -> Token:
    code = code_request.code
    logger.info('Received VK linking request for user ID: %s', me.id)
    logger.debug('VK OAuth code received: %s', code)

    try:
        # Получаем токен доступа от VK
        access_token = await get_access_token(code)
        logger.info('Access token received for VK user ID: %s', access_token.user_id)
    except Exception as e:
        logger.error('Failed to get access token for user ID: %s, error: %s', me.id, str(e))
        raise HTTPException(status_code=400, detail='Failed to retrieve VK access token')

    try:
        # Используем UserService для привязки VK аккаунта
        async with UserService() as service:
            # Привязываем VK к пользователю
            await service.link_vk(me.id, access_token.user_id)

            logger.info('Successfully linked VK account to user ID: %s', me.id)
            logger.debug('Linked VK user ID: %s', access_token.user_id)

            # Создаем токен доступа после успешной привязки VK аккаунта
            new_access_token = create_access_token(data={"sub": me.username})
            return Token(access_token=new_access_token, token_type="bearer")
    except Exception as e:
        logger.error('Failed to link VK account for user ID: %s, error: %s', me.id, str(e))
        raise HTTPException(status_code=500, detail='Failed to link VK account')

@router.get(
    '/users/telegram/link',
    tags=['Telegram']
)
async def get_link_telegram_url(
    user: ReadProfile = Depends(get_current_active_user)
) -> str:
    return f'https://t.me/moon_backend_bot?start={user.telegram_code}'

@router.get(
    '/users/me/referrals-stats',
    tags=['Referrals']
)
async def get_referrals_analytics(
    user: ReadProfile = Depends(get_current_active_user)
):
    async with ReferralsService() as service:
        daily_counts = await service.count_user_referrals_last_n_days(user.id, 30)
        total_count = await service.count_all_user_referrals(user.id)
        revenue = await service.get_user_revenue(user.id)

        return ReferralsStatistics(
            last_month=daily_counts,
            total_referrals=total_count,
            total_revenue=Decimal(revenue)  # Используем Decimal
        )