from src.service import BaseService
from src.users.models import User  # Изменённый импорт

STATICS_PATH = './static/users/'


class UserException(Exception):
    ...


class UserNotFound(UserException):
    ...


class AvatarException(UserException):
    ...


class AvatarTooLarge(AvatarException):
    ...


class UserService(BaseService):

    async def get_user_by_id(self, id: int) -> User:
        return await self.session.get(User, id)
