import logging
from datetime import timezone, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.users.route import get_current_active_user
from src.users.schemas import ReadProfile
from src.database import async_session

from .models import TransactionType, TransactionStatus, Transaction, PaymentSystem
from src.users.models import User

from .schemas import (
    CreateDeposit, CreateTransaction, CreateWithdrawal,
    ReadBalance, ReadBonusEarned, ReadTransaction,
    ReadTransactionsPaginated
)
from .service import TooEarly, TransactionService, WalletException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Набор промокодов
promo_codes = [
    {"code": "PROMO30", "amount": 30, "used": False},
    {"code": "DISCOUNT10", "amount": 10, "used": False},
    {"code": "GIFT75", "amount": 75, "used": False},
    {"code": "SPECIAL150", "amount": 150, "used": False},
    {"code": "LUCKY250", "amount": 250, "used": False},

    # Новые промокоды
    {"code": "BONUS20", "amount": 20, "used": False},
    {"code": "SAVE50", "amount": 50, "used": False},
    {"code": "REWARD100", "amount": 100, "used": False},
    {"code": "EXTRA200", "amount": 200, "used": False},
    {"code": "SURPRISE300", "amount": 300, "used": False},
    {"code": "WIN400", "amount": 400, "used": False},
    {"code": "VIP500", "amount": 500, "used": False},
    {"code": "GOLD600", "amount": 600, "used": False},
    {"code": "PLATINUM700", "amount": 700, "used": False},
    {"code": "ELITE800", "amount": 800, "used": False},
    {"code": "KING900", "amount": 900, "used": False},
    {"code": "SUPER1000", "amount": 1000, "used": False},
    {"code": "MEGA1100", "amount": 1100, "used": False},
    {"code": "ULTIMATE1200", "amount": 1200, "used": False},
    {"code": "LEGEND1300", "amount": 1300, "used": False},
]

async def check_and_apply_referral_bonus(user: ReadProfile, deposit_amount: float, session: AsyncSession):
    if not user.has_deposited:
        if user.referrer_id:
            referrer = await session.get(User, user.referrer_id)
            if referrer:
                logger.info(f"Referrer found: {referrer.id}, username: {referrer.username}, referral_bonus_rate: {referrer.referral_bonus_rate}")

                referral_bonus_rate = referrer.referral_bonus_rate or Decimal(0.1)
                referral_bonus = Decimal(deposit_amount) * referral_bonus_rate

                if referrer.referral_earnings is None:
                    referrer.referral_earnings = Decimal(0)
                referrer.referral_earnings += referral_bonus

                referral_transaction = Transaction(
                    payment_system=PaymentSystem.internal,
                    amount=referral_bonus,
                    type=TransactionType.REFERRAL,
                    user_id=user.referrer_id,
                    status=TransactionStatus.CONFIRMED
                )
                session.add(referral_transaction)
            else:
                logger.warning(f"Referrer with id {user.referrer_id} not found.")
        else:
            logger.info("No referrer_id provided.")
        
        user.has_deposited = True
        session.add(user)
        await session.commit()
    else:
        logger.info(f"User {user.id} has already made a deposit.")

@router.post(
    '/wallet/deposit',
    tags=['Wallet']
)
async def create_deposit(
    deposit: CreateDeposit,
    user: ReadProfile = Depends(get_current_active_user)
):
    async with async_session() as session:
        await check_and_apply_referral_bonus(user, deposit.amount, session)

        transaction = CreateTransaction(
            payment_system=deposit.payment_system,
            amount=deposit.amount,
            type=TransactionType.IN,
            user_id=user.id,
            status=TransactionStatus.CONFIRMED
        )

        async with TransactionService() as service:
            db_transaction = await service.create_transaction(transaction)
            logger.info(f"Deposit created: {db_transaction}")
            return ReadTransaction.model_validate(db_transaction)

@router.post(
    '/wallet/bonus-deposit',
    tags=['Wallet']
)
async def create_bonus_deposit(
    deposit: CreateDeposit,
    user: ReadProfile = Depends(get_current_active_user)
):
    async with async_session() as session:
        await check_and_apply_referral_bonus(user, deposit.amount, session)

        # Распаковка полей для передачи в create_transaction
        async with TransactionService() as service:
            db_transaction = await service.create_transaction(
                user_id=user.id,
                amount=deposit.amount,
                transaction_type=TransactionType.BONUS.name  # Передаем имя типа
            )
            logger.info(f"Bonus deposit created: {db_transaction}")
            return ReadTransaction.model_validate(db_transaction)

@router.post(
    '/wallet/withdrawal',
    tags=['Wallet']
)
async def create_withdrawal(
    withdrawal: CreateWithdrawal,
    user: ReadProfile = Depends(get_current_active_user)
):
    transaction = CreateTransaction(
        payment_system=withdrawal.payment_system,
        amount=withdrawal.amount,
        type=TransactionType.OUT,
        user_id=user.id,
        status=TransactionStatus.PENDING
    )

    async with TransactionService() as service:
        balance = await service.get_balance(user.id)
        bonus_balance = await service.get_bonus_balance(user.id)
        pure_balance = balance - bonus_balance

        logger.info(f"User {user.id} is attempting to withdraw {withdrawal.amount}. Balance: {balance}, Pure balance: {pure_balance}")

        if withdrawal.amount > pure_balance:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Insufficient pure balance to withdraw')

        db_transaction = await service.create_transaction(transaction)
        logger.info(f"Withdrawal request created: {db_transaction}")
        return ReadTransaction.model_validate(db_transaction)

@router.get(
    '/wallet/history',
    tags=['Wallet']
)
async def get_history(
    page: int = Query(1),
    limit: int = Query(5),
    types: Optional[str] = Query(None),
    user: ReadProfile = Depends(get_current_active_user)
) -> ReadTransactionsPaginated:
    async with TransactionService() as service:
        db_transactions = await service.get_transactions(page, limit, user.id, types)
        transactions = [
            ReadTransaction.model_validate(t)
            for t in db_transactions
        ]
        total = await service.get_total_transactions_by_user(user.id, types)
        logger.info(f"Retrieved {len(transactions)} transactions for user {user.id}. Total: {total}")
        return ReadTransactionsPaginated(
            total=total,
            transactions=transactions
        )

@router.get(
    '/wallet/balance',
    tags=['Wallet']
)
async def get_balance(
    user: ReadProfile = Depends(get_current_active_user)
) -> ReadBalance:
    async with TransactionService() as service:
        balance = await service.get_balance(user.id)
        bonus_balance = await service.get_bonus_balance(user.id)
        pure_balance = await service.get_pure_balance(user.id)
        logger.info(f"User {user.id} balance: {balance}, Bonus balance: {bonus_balance}, Pure balance: {pure_balance}")
        return ReadBalance(balance=balance, bonus_balance=bonus_balance, pure_balance=pure_balance)

@router.get(
    '/wallet/bonus'
)
async def earn_bonuses(
    user: ReadProfile = Depends(get_current_active_user)
) -> ReadBonusEarned:
    async with TransactionService() as service:
        try:
            bonuses_earned = await service.earn_bonuses(user.id)
            new_balance = await service.get_balance(user.id)

            logger.info(f"User {user.id} earned bonuses: {bonuses_earned}, New balance: {new_balance}")
            return ReadBonusEarned(
                amount=bonuses_earned,
                balance=new_balance
            )
        except TooEarly:
            logger.warning(f"User {user.id} tried to earn bonuses too early.")
            raise HTTPException(status.HTTP_425_TOO_EARLY, 'Too early')

@router.get(
    '/wallet/bonus/last-earn'
)
async def get_time_of_last_bonus_earn(
    user: ReadProfile = Depends(get_current_active_user)
):
    async with TransactionService() as service:
        transaction = await service.get_latest_bonus_earn_transaction(user.id)
        if transaction is None:
            raise HTTPException(status_code=404, detail="No bonus transactions found for this user")
        
        created_at_utc = transaction.created_at.astimezone(timezone.utc).isoformat()
        logger.info(f"User {user.id} last bonus earn time: {created_at_utc}")
        
        return {"created_at": created_at_utc}

@router.post(
    '/wallet/apply_promo_code',
    tags=['Wallet']
)
async def apply_promo_code(
    promo_code: str,  # Теперь promo_code будет извлекаться из тела запроса
    user: ReadProfile = Depends(get_current_active_user)
):
    logger.info(f"Attempting to apply promo code: {promo_code} for user: {user.id}")

    # Поиск промокода в локальном списке
    promo = next((p for p in promo_codes if p["code"] == promo_code), None)

    if not promo:
        logger.warning(f"Promo code {promo_code} not found for user {user.id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found"
        )

    if promo["used"]:
        logger.warning(f"Promo code {promo_code} already used for user {user.id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promo code already used"
        )

    # Создаем транзакцию
    transaction_data = {
        "user_id": user.id,
        "amount": Decimal(promo["amount"]),
        "transaction_type": "REFERRAL"  # Передаем строку, как ожидает create_transaction
    }

    # Применяем бонус через TransactionService
    async with TransactionService() as service:
        db_transaction = await service.create_transaction(**transaction_data)

    # Устанавливаем флаг used для промокода
    promo["used"] = True

    logger.info(
        f"Promo code {promo_code} successfully applied for user {user.id}. Amount: {promo['amount']}"
    )
    return {
        "message": "Promo code applied successfully",
        "amount": promo["amount"]
    }


# Новый маршрут для получения всех заявок на вывод средств
@router.get(
    '/wallet/withdrawals/pending',
    tags=['Admin']
)
async def get_pending_withdrawals(
    user: ReadProfile = Depends(get_current_active_user)
):
    async with TransactionService() as service:
        pending_withdrawals = await service.get_pending_withdrawals()
        return [ReadTransaction.model_validate(w) for w in pending_withdrawals]

# Маршрут для подтверждения заявки на вывод средств
@router.post(
    '/wallet/withdrawals/confirm',
    tags=['Admin']
)
async def confirm_withdrawal(
    transaction_id: int,
    user: ReadProfile = Depends(get_current_active_user)
):
    async with TransactionService() as service:
        try:
            await service.confirm_withdrawal(transaction_id)
            return {"message": "Withdrawal confirmed"}
        except WalletException as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

# Маршрут для отклонения заявки на вывод средств
@router.post(
    '/wallet/withdrawals/reject',
    tags=['Admin']
)
async def reject_withdrawal(
    transaction_id: int,
    user: ReadProfile = Depends(get_current_active_user)
):
    async with TransactionService() as service:
        try:
            await service.reject_withdrawal(transaction_id)
            return {"message": "Withdrawal rejected"}
        except WalletException as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

@router.get(
    '/wallet/withdrawals/last',
    tags=['Wallet']
)
async def get_last_withdrawal_attempt(
    user: ReadProfile = Depends(get_current_active_user)
):
    async with TransactionService() as service:
        last_withdrawal = await service.get_last_withdrawal_attempt(user.id)
        
        if not last_withdrawal:
            # Если нет записи о последнем выводе, возвращаем 1 сентября 1900 года
            return {"created_at": datetime(1900, 9, 1)}

        return {"created_at": last_withdrawal.created_at}