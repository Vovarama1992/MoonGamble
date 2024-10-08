"""Добавлен статус транзакции и столбец has_deposited в модель User

Revision ID: 41e3a99b04b7
Revises: 9a8a3c7f821c
Create Date: 2024-08-21 07:38:29.337198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '41e3a99b04b7'
down_revision: Union[str, None] = '9a8a3c7f821c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    
    # Создание ENUM типа в базе данных
    transactionstatus = postgresql.ENUM('PENDING', 'CONFIRMED', 'REJECTED', name='transactionstatus')
    transactionstatus.create(op.get_bind(), checkfirst=True)
    
    # Добавление нового столбца со статусом транзакции
    op.add_column('transactions', sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'REJECTED', name='transactionstatus'), nullable=False))
    
    # Добавление уникального ограничения и новых столбцов в таблицу users
    op.create_unique_constraint(None, 'transactions', ['id'])
    op.add_column('users', sa.Column('has_deposited', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('referral_bonus_rate', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('referral_earnings', sa.Numeric(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'referral_earnings')
    op.drop_column('users', 'referral_bonus_rate')
    op.drop_column('users', 'has_deposited')
    op.drop_constraint(None, 'transactions', type_='unique')
    op.drop_column('transactions', 'status')
    
    # Удаление типа ENUM из базы данных
    transactionstatus = postgresql.ENUM('PENDING', 'CONFIRMED', 'REJECTED', name='transactionstatus')
    transactionstatus.drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###