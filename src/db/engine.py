from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.config import settings
from src.logger import log


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Создаёт таблицы приложения (не dds.*, только app-таблицы)."""
    from src.db import models  # noqa: F401 — регистрирует модели

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("База данных инициализирована")


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
