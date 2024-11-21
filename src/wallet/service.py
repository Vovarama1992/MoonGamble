import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.future import select
from src.service import BaseService
from .models import PaymentSystem, Transaction, TransactionType, TransactionStatus
from .schemas import CreateTransaction

# Настройка логирования
logger = logging.getLogger(__name__)

class WalletException(Exception):
    pass

class InsufficientFunds(Exception):
    pass

class BonusException(Exception):
    pass

class TooEarly(BonusException):
    pass

class TransactionService(BaseService):

    async def create_transaction(self, user_id: int, amount: Decimal, transaction_type: str):
        logger.info(f"Creating transaction for user {user_id}: {transaction_type} of {amount}")
        
        # Создаём объект транзакции
        db_transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=TransactionType[transaction_type.upper()],  # Преобразуем строку в enum
            payment_system=PaymentSystem.internal,  # Например, все транзакции внутри системы
            status=TransactionStatus.CONFIRMED  # Статус по умолчанию CONFIRMED
        )
        
        # Добавляем в сессию, коммитим и обновляем объект
        self.session.add(db_transaction)
        await self.session.commit()
        await self.session.refresh(db_transaction)
        
        logger.info(f"Transaction created with ID: {db_transaction.id}")
        return db_transaction

    async def get_total_transactions_by_user(self, user_id: int, types: Optional[str] = None):
        logger.info(f"Fetching total transactions for user {user_id} with types {types}")
        query = select(Transaction).where(Transaction.user_id == user_id)

        if types:
            type_values = [TransactionType(int(t)) for t in types.split(',')]
            query = query.where(Transaction.type.in_(type_values))

        result = await self.session.execute(query)
        total_transactions = len(result.scalars().all())
        logger.info(f"Total transactions found: {total_transactions}")
        return total_transactions

    async def get_transactions(self, page: int = 1, limit: int = 5, user_id: int = None, types: Optional[str] = None):
        logger.info(f"Fetching transactions for user {user_id} - Page: {page}, Limit: {limit}, Types: {types}")
        query = select(Transaction).where(Transaction.user_id == user_id)

        if types:
            type_values = [TransactionType(int(t)) for t in types.split(',')]
            query = query.where(Transaction.type.in_(type_values))

        query = query.offset((page - 1) * limit).limit(limit)

        transactions = (await self.session.execute(query)).scalars().all()
        logger.info(f"Transactions fetched: {len(transactions)}")
        return transactions

    async def get_balance(self, user_id: int):
        logger.info(f"Calculating balance for user {user_id}")
        query = select(Transaction).where(Transaction.user_id == user_id)
        transactions = await self.session.execute(query)
        balance = Decimal(0.0)
        
        for transaction in transactions.scalars().all():
            logger.info(f"Transaction: {transaction.id}, Type: {transaction.type}, Amount: {transaction.amount}, Status: {transaction.status}")
            
            if transaction.type in [TransactionType.IN, TransactionType.BONUS, TransactionType.REFERRAL] and transaction.status == TransactionStatus.CONFIRMED:
                balance += transaction.amount
                logger.info(f"Balance increased by {transaction.amount}, new balance: {balance}")
            elif transaction.type == TransactionType.OUT and transaction.status == TransactionStatus.CONFIRMED:
                balance -= transaction.amount
                logger.info(f"Balance decreased by {transaction.amount}, new balance: {balance}")
        
        logger.info(f"Final balance for user {user_id}: {balance}")
        return balance

    async def get_bonus_balance(self, user_id: int) -> Decimal:
        logger.info(f"Calculating bonus balance for user {user_id}")
        query = select(Transaction).where(Transaction.user_id == user_id)
        transactions = await self.session.execute(query)
        balance = Decimal(0.0)
        for transaction in transactions.scalars().all():
            if transaction.type == TransactionType.BONUS and transaction.status == TransactionStatus.CONFIRMED:
                balance += transaction.amount
                logger.info(f"Bonus balance increased by {transaction.amount}, new bonus balance: {balance}")
        logger.info(f"Final bonus balance for user {user_id}: {balance}")
        return balance

    async def get_pure_balance(self, user_id: int):
        logger.info(f"Calculating pure balance for user {user_id}")
        query = select(Transaction).where(Transaction.user_id == user_id)
        transactions = await self.session.execute(query)
        balance = Decimal(0.0)
        for transaction in transactions.scalars().all():
            if transaction.type == TransactionType.IN and transaction.status == TransactionStatus.CONFIRMED:
                balance += transaction.amount
            elif transaction.type == TransactionType.OUT and transaction.status == TransactionStatus.CONFIRMED:
                balance -= transaction.amount
        logger.info(f"Final pure balance for user {user_id}: {balance}")
        return balance

    async def get_latest_bonus_earn_transaction(self, user_id: int) -> Optional[Transaction]:
        logger.info(f"Fetching latest bonus earn transaction for user {user_id}")
        result = await self.session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.BONUS
            ).order_by(
                Transaction.created_at.desc()
            ).limit(1)
        )
        transaction = result.scalar_one_or_none()
        if transaction:
            logger.info(f"Latest bonus earn transaction found: {transaction.id}")
        else:
            logger.info("No bonus earn transaction found.")
        return transaction

    async def add_bonuses(self, user_id: int, amount: Decimal):
        logger.info(f"Adding bonuses to user {user_id}: {amount}")
        await self.create_transaction(CreateTransaction(
            payment_system=PaymentSystem.internal,
            type=TransactionType.BONUS,
            from_account='system',
            to_account=str(user_id),
            amount=amount,
            user_id=user_id
        ))

    async def earn_bonuses(self, user_id: int) -> Optional[Decimal]:
        logger.info(f"User {user_id} attempting to earn bonuses")
        now = datetime.now()

        transaction = await self.get_latest_bonus_earn_transaction(user_id)

        if transaction is None:
            earned_bonuses = Decimal(randint(10, 100))  # Генерация случайной суммы бонусов
            await self.add_bonuses(user_id, earned_bonuses)  # Передача сгенерированной суммы
            logger.info(f"Bonuses earned: {earned_bonuses}")
            return earned_bonuses

        seconds_from_last_bonus_earn = (now - transaction.created_at).total_seconds()
        if seconds_from_last_bonus_earn >= 86400:  # 24 hours
            earned_bonuses = Decimal(randint(10, 100))
            await self.add_bonuses(user_id, earned_bonuses)
            logger.info(f"Bonuses earned after 24 hours: {earned_bonuses}")
            return earned_bonuses
        else:
            logger.info(f"Too early to earn bonuses for user {user_id}, time left: {86400 - seconds_from_last_bonus_earn} seconds")
            raise TooEarly()

    async def get_pending_withdrawals(self) -> List[Transaction]:
        logger.info("Fetching pending withdrawals")
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.type == TransactionType.OUT,
                Transaction.status == TransactionStatus.PENDING
            )
        )
        pending_withdrawals = result.scalars().all()
        logger.info(f"Pending withdrawals found: {len(pending_withdrawals)}")
        return pending_withdrawals

    async def confirm_withdrawal(self, transaction_id: int):
        logger.info(f"Confirming withdrawal with transaction ID: {transaction_id}")
        transaction = await self.session.get(Transaction, transaction_id)
        if transaction and transaction.status == TransactionStatus.PENDING:
            transaction.status = TransactionStatus.CONFIRMED
            await self.session.commit()
            logger.info(f"Withdrawal confirmed: {transaction_id}")
        else:
            logger.warning(f"Transaction not found or not pending: {transaction_id}")
            raise WalletException("Transaction not found or not in pending status")

    async def reject_withdrawal(self, transaction_id: int):
        logger.info(f"Rejecting withdrawal with transaction ID: {transaction_id}")
        transaction = await self.session.get(Transaction, transaction_id)
        if transaction and transaction.status == TransactionStatus.PENDING:
            transaction.status = TransactionStatus.REJECTED
            await self.session.commit()
            logger.info(f"Withdrawal rejected: {transaction_id}")
        else:
            logger.warning(f"Transaction not found or not pending: {transaction_id}")
            raise WalletException("Transaction not found or not in pending status")

    async def get_last_withdrawal_attempt(self, user_id: int) -> Optional[Transaction]:
        logger.info(f"Fetching last withdrawal attempt for user ID: {user_id}")
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.OUT
            ).order_by(Transaction.created_at.desc()).limit(1)
        )
        last_withdrawal = result.scalars().first()
        if last_withdrawal:
            logger.info(f"Last withdrawal attempt found: {last_withdrawal.created_at}")
        else:
            logger.info("No withdrawal attempts found")
        return last_withdrawal