import enum
from datetime import datetime
from uuid import uuid4

import sqlalchemy

from src.database import Base


class UserRole(enum.Enum):
    user = 'user'
    admin = 'admin'
    support = 'support'
    superuser = 'superuser'


class User(Base):
    __table_args__ = dict(extend_existing=True)
    __tablename__ = 'users'

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True,
        index=True,
    )

    referrer_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey('users.id'),
        nullable=True,
    )

    username = sqlalchemy.Column(
        sqlalchemy.String,
        index=True,
        unique=True,
    )

    password = sqlalchemy.Column(
        sqlalchemy.String(64)
    )

    fullname = sqlalchemy.Column(
        sqlalchemy.String,
        default=None
    )

    avatar = sqlalchemy.Column(
        sqlalchemy.String,
        default=None
    )

    telegram_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        default=None
    )

    telegram_fullname = sqlalchemy.Column(
        sqlalchemy.String,
        default=None
    )

    telegram_username = sqlalchemy.Column(
        sqlalchemy.String,
        default=None
    )

    telegram_code = sqlalchemy.Column(
        sqlalchemy.String,
        default=lambda: uuid4().hex
    )

    vk_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        default=None
    )

    active = sqlalchemy.Column(
        sqlalchemy.Boolean,
        default=True
    )

    fingerprint = sqlalchemy.Column(sqlalchemy.String)

    fingerprint_hash = sqlalchemy.Column(sqlalchemy.String)

    role = sqlalchemy.Column(
        sqlalchemy.Enum(UserRole),
        nullable=False
    )

    created_at = sqlalchemy.Column(
        sqlalchemy.DateTime,
        default=datetime.now
    )

    has_deposited = sqlalchemy.Column(  # Добавлено новое поле
        sqlalchemy.Boolean,
        default=False
    )

    referral_bonus_rate = sqlalchemy.Column(  # Добавлено новое поле
        sqlalchemy.Float,
        default=0.1
    )

    referral_earnings = sqlalchemy.Column(  # Новое поле
        sqlalchemy.Numeric,
        default=0.0
    )

    referral_count = sqlalchemy.Column(  # Новое поле для хранения количества рефералов
        sqlalchemy.Integer,
        default=0
    )

    transactions = sqlalchemy.orm.relationship(
        'Transaction',
        back_populates='user'
    )

    tickets = sqlalchemy.orm.relationship(
        'Ticket',
        back_populates='user'
    )

    messages = sqlalchemy.orm.relationship(
        'Message',
        back_populates='user'
    )

    # Relationship to self, reverse for referrer
    referrer = sqlalchemy.orm.relationship(
        'User',
        remote_side=[id],
        back_populates='referrals'
    )

    # Relationship to self, forward for referrals
    referrals = sqlalchemy.orm.relationship(
        'User',
        back_populates='referrer'
    )
