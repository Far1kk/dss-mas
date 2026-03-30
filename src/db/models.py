from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, BigInteger, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from src.db.engine import Base


# ---------------------------------------------------------------------------
# Таблицы приложения (создаются автоматически)
# ---------------------------------------------------------------------------

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # sql / ml / orchestrator
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rating: Mapped[str] = mapped_column(String(16), nullable=False)  # like / dislike
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Read-only ORM-отражения dds.* таблиц (не создаются автоматически)
# ---------------------------------------------------------------------------

class DimProject(Base):
    __tablename__ = "dim_project"
    __table_args__ = {"schema": "dds", "extend_existing": True}

    issueid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[Optional[int]] = mapped_column(Integer)
    type: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    date_begin: Mapped[Optional[date]] = mapped_column(Date)
    date_end: Mapped[Optional[date]] = mapped_column(Date)
    kam: Mapped[Optional[str]] = mapped_column(String(255))
    pm: Mapped[Optional[str]] = mapped_column(String(255))


class DimCounteragent(Base):
    __tablename__ = "dim_counteragent"
    __table_args__ = {"schema": "dds", "extend_existing": True}

    dwh_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    jira_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    counteragent: Mapped[Optional[str]] = mapped_column(Text)
    industry: Mapped[Optional[int]] = mapped_column(Integer)
    responsible: Mapped[Optional[str]] = mapped_column(String)


class DimContract(Base):
    __tablename__ = "dim_contract"
    __table_args__ = {"schema": "dds", "extend_existing": True}

    jira_issueid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column("name", String(255))
    type: Mapped[Optional[int]] = mapped_column(Integer)
    counteragent_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    sum: Mapped[Optional[float]] = mapped_column(Float)
    date_sign: Mapped[Optional[date]] = mapped_column(Date)
    date_end: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[Optional[int]] = mapped_column(Integer)
    manager: Mapped[Optional[str]] = mapped_column(Text)


class FactForecast(Base):
    __tablename__ = "fact_forecast"
    __table_args__ = {"schema": "dds", "extend_existing": True}

    issueid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    summary: Mapped[Optional[str]] = mapped_column(String(255))
    date_start: Mapped[Optional[date]] = mapped_column(Date)
    date_end: Mapped[Optional[date]] = mapped_column(Date)
    forecast_sum: Mapped[Optional[float]] = mapped_column(Float)
    fact_sum: Mapped[Optional[float]] = mapped_column(Float)
    pr_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    status: Mapped[Optional[int]] = mapped_column(Integer)
    plan_date_pay: Mapped[Optional[date]] = mapped_column(Date)
    income_subcounteragent: Mapped[Optional[int]] = mapped_column(Integer)
