from typing import Annotated
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

from src.providers.schemas import ReadProfile
from src.users.service import UserService  # Исправленный импорт
from src.users.security import decode_token

# Определение исключений
credentials_exception = HTTPException(
    status_code=401,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

# Настройка схемы OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/auth/token")

# Получение текущего пользователя по токену
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    token_data = decode_token(token)  # Декодируем токен, чтобы получить данные пользователя
    async with UserService() as service:  # Открываем сессию с UserService
        user = await service.get_user_by_username(token_data.username)  # Ищем пользователя по username
    if user is None:
        raise credentials_exception  # Если пользователь не найден, вызываем исключение
    return user

# Получение активного пользователя (с проверкой активности)
async def get_current_active_user(
    current_user: Annotated[ReadProfile, Depends(get_current_user)],  # Зависимость от get_current_user
):
    if not current_user.active:  # Проверка активности пользователя
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
