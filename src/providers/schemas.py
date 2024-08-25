from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from src.schemas import ORM

from .models import UserRole


class SelfValidateResponse(BaseModel):
    success: bool
    log: list[str]


class ReadProfile(ORM):
    id: int
    username: str
    fullname: Optional[str]
    avatar: Optional[str]
    telegram_id: Optional[int]
    telegram_fullname: Optional[str]
    telegram_username: Optional[str]
    vk_id: Optional[int]
    role: UserRole
    telegram_code: str
    created_at: datetime
