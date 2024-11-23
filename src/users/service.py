import datetime
from decimal import Decimal

import sqlalchemy

from src.service import BaseService
from src.wallet import models as wallet_models
from src.wallet.service import TransactionService

from .fingerprint import hash_fingerprint
from .models import User, UserRole
from .schemas import RegisterUser
from .security import get_password_hash

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
    async def register_user(self, user: RegisterUser):
        # Check if username exists
        query = sqlalchemy.select(User).where(
            User.username == user.username
        )
        result = await self.session.execute(query)
        db_user = result.scalar_one_or_none()
        if db_user:
            raise UserException("User with username exist already")

        # Create user
        user.password = get_password_hash(user.password)
        user.fingerprint_hash = hash_fingerprint(user.fingerprint)

        new_user = User(**{'role': UserRole.user, **user.model_dump()})
        self.session.add(new_user)

        await self.session.commit()
        await self.session.refresh(new_user)

        return new_user

    async def get_user_by_id(self, id: int) -> User:
        return await self.session.get(User, id)

    async def get_user_by_vk_id(self, vk_id: int) -> User:
        query = await self.session.execute(
            sqlalchemy.select(User).where(User.vk_id == vk_id)
        )
        return query.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User:
        query = await self.session.execute(
            sqlalchemy.select(User).where(
                User.username == username
            )
        )
        return query.scalar_one_or_none()

    async def link_telegram(
        self,
        telegram_id: int,
        fullname: str | None,
        username: str | None,
        telegram_code: str,
    ):
        query = await self.session.execute(
            sqlalchemy.select(User).where(
                User.telegram_code == telegram_code
            )
        )
        user = query.scalar_one_or_none()

        if not user:
            return None

        if user.telegram_id is not None:
            return None

        user.telegram_id = telegram_id
        user.telegram_fullname = fullname
        user.telegram_username = username

        await self.session.flush([user])
        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def link_vk(self, user_id: int, vk_id: int):
        user = await self.get_user_by_id(user_id)

        user.vk_id = vk_id

        # Сохраняем изменения пользователя
        await self.session.flush([user])
        await self.session.commit()
        await self.session.refresh(user)

        # Создаем бонусную транзакцию
        transaction_service = TransactionService(self.session)  # Создаем экземпляр сервиса транзакций
        bonus_amount = Decimal(10)  # Сумма бонуса
        await transaction_service.add_bonuses(user_id, bonus_amount)

        return user

    async def change_password(self, user_id: int, new_password: str):
        user = await self.get_user_by_id(user_id)
        user.password = new_password

        await self.session.flush([user])
        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def update_avatar(self, user_id: int, avatar_id: int):
        db_user = await self.get_user_by_id(user_id)

        db_user.avatar = str(avatar_id)

        await self.session.commit()
        await self.session.refresh(db_user)

        return db_user

    async def update_user(self, user: User):
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)


class ReferralsService(BaseService):
    async def count_user_referrals_last_n_days(self, user_id: int, n_days=30):
        counts = {}
        current_date = datetime.date.today()

        for _ in range(30):
            results = await self.session.execute(
                sqlalchemy.select(User).where(
                    User.referrer_id == user_id,
                    sqlalchemy.func.date(User.created_at) == current_date,
                )
            )
            counts[current_date] = len(results.scalars().all())
            current_date -= datetime.timedelta(days=1)

        return counts

    async def count_all_user_referrals(self, user_id: int):
        results = await self.session.execute(
            sqlalchemy.select(User.id).where(
                User.referrer_id == user_id
            )
        )
        return len(results.scalars().all())

    async def get_user_revenue(self, user_id: int):
        results = await self.session.execute(
            sqlalchemy.select(wallet_models.Transaction).where(
                wallet_models.Transaction.user_id == user_id,
                wallet_models.Transaction.type == wallet_models.TransactionType.REFERRAL
            )
        )
        balance = Decimal(0.0)
        for transaction in results.scalars():
            balance += transaction.amount
        return balance