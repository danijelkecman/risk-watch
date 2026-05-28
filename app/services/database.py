from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, JSON, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(DeclarativeBase):
    pass


class SnapshotRow(Base):
    __tablename__ = "risk_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(50), default="mock", index=True)
    overall_score: Mapped[float] = mapped_column(Float, index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope():
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def insert_snapshot(source: str, payload: dict) -> None:
    async with session_scope() as session:
        session.add(
            SnapshotRow(
                created_at=datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00")) if isinstance(payload["timestamp"], str) else payload["timestamp"],
                source=source,
                overall_score=payload["overall_score"],
                severity=payload["severity"],
                payload=payload,
            )
        )


async def load_recent_snapshots(limit: int) -> list[dict]:
    async with session_scope() as session:
        stmt = select(SnapshotRow).order_by(SnapshotRow.created_at.desc()).limit(limit)
        rows = (await session.execute(stmt)).scalars().all()
        return [row.payload for row in reversed(rows)]
