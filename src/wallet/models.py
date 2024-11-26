import enum
from datetime import datetime

from sqlalchemy import (DECIMAL, Column, DateTime, Boolean, Enum, ForeignKey, Integer,
                        String)
from sqlalchemy.orm import relationship

from src.db_base import Base


class TransactionType(enum.Enum):
    IN = 0
    OUT = 1
    BONUS = 2
    REFERRAL = 3
    


class PaymentSystem(enum.Enum):
    fps = 'faster_payment_system'
    sberpay = 'sberpay'
    yoomoney = 'yoomoney'
    card = 'card'
    ptop = 'p2p'
    internal = 'internal'


class TransactionStatus(enum.Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, unique=True)
    payment_system = Column(Enum(PaymentSystem), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(DECIMAL, nullable=False)

    from_account = Column(String, default='')
    to_account = Column(String, default='')

    created_at = Column(DateTime, default=datetime.now)

    status = Column(Enum(TransactionStatus), default=TransactionStatus.CONFIRMED, nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='transactions')

    # Новый флаг для трудового депозита
    is_hard_deposit = Column(Boolean, default=False)

