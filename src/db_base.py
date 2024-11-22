from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Импорты всех моделей
from src.users.models import User
from src.wallet.models import Transaction  # Импорт модели Transaction
from src.support.models import Ticket, Message