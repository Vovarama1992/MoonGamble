from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.db_base import Base

# Конфигурация подключения
DATABASE_URL = "postgresql+asyncpg://moon:moon@pgdb/moon"

# Создаём асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаём фабрику для сессий
async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Функция для получения сессии
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
