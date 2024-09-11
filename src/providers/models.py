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


