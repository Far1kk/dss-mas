from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import ConversationMessage, Feedback
from src.logger import log


# DDL-схема для передачи в промпты агентов (упрощённый RAG)
DB_SCHEMA_CONTEXT = """
Схема базы данных PostgreSQL (схема: dds):

Таблица dds.dim_project — справочник проектов:
  issueid (bigint, PK) — ID проекта
  project_name (varchar) — Название проекта
  status (int) — Статус: 1=активный, 2=завершён, 3=приостановлен
  type (int) — Тип: 1=внутренний, 2=внешний, 3=ТМ
  description (text) — Описание проекта
  date_begin (date) — Дата старта проекта
  date_end (date) — Дата окончания проекта
  kam (varchar) — Менеджер по работе с ключевыми клиентами
  pm (varchar) — Проджект-менеджер

Таблица dds.dim_counteragent — справочник заказчиков/контрагентов:
  dwh_id (bigint, PK) — ID заказчика
  jira_id (bigint) — ID в Jira
  counteragent (text) — Наименование контрагента
  industry (int) — Сфера деятельности: 1=IT, 2=банки, 3=производство, 4=госсектор
  responsible (varchar) — Ответственный менеджер

Таблица dds.dim_contract — таблица контрактов:
  jira_issueid (bigint, PK) — ID контракта
  name (varchar) — Название контракта
  type (int) — Тип: 1=доходный договор, 2=расходный договор, 3=акт
  counteragent_id (bigint, FK → dds.dim_counteragent.dwh_id) — ID контрагента
  sum (float) — Сумма контракта
  date_sign (date) — Дата начала контракта
  date_end (date) — Дата окончания контракта
  status (int) — Статус: 1=активный, 2=завершён, 3=расторгнут
  manager (text) — Ответственный менеджер

Таблица dds.fact_forecast — выработка по проектам:
  issueid (bigint, PK) — ID выработки
  summary (varchar) — Название документа выработки
  date_start (date) — Дата начала выработки
  date_end (date) — Дата окончания выработки
  forecast_sum (float) — Прогнозный доход от выработки
  fact_sum (float) — Фактический доход по выработке
  pr_id (bigint, FK → dds.dim_project.issueid) — ID проекта
  status (int) — Статус: 1=в работе, 2=выставлен счёт, 3=оплачен, 4=просрочен
  plan_date_pay (date) — Планируемая дата оплаты
  income_subcounteragent (int) — Доходы от субподрядчиков

Таблица dds.link_contract_project — связи контрактов и проектов:
  contract_id (bigint, FK → dds.dim_contract.jira_issueid) — ID контракта
  project_id (bigint, FK → dds.dim_project.issueid) — ID проекта

Бизнес-правила:
- Заказчик проекта = контрагент текущего доходного договора проекта (dim_contract.type=1)
- Выработки с plan_date_pay < CURRENT_DATE и status != 3 считаются просроченными
- Активные проекты: dim_project.status = 1
- Активные контракты: dim_contract.status = 1
"""


async def execute_raw_sql(sql: str, session: AsyncSession) -> list[dict]:
    """Выполняет SQL и возвращает результат в виде списка словарей."""
    try:
        result = await session.execute(text(sql))
        rows = result.fetchall()
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        log.error(f"Ошибка выполнения SQL: {e}")
        raise


async def save_message(
    session_id: str,
    role: str,
    content: str,
    db_session: AsyncSession,
    agent_type: str | None = None,
) -> None:
    msg = ConversationMessage(
        session_id=session_id,
        role=role,
        content=content,
        agent_type=agent_type,
    )
    db_session.add(msg)
    await db_session.commit()


async def get_history(
    session_id: str, db_session: AsyncSession, limit: int = 10
) -> list[dict]:
    result = await db_session.execute(
        text(
            "SELECT role, content FROM conversation_messages "
            "WHERE session_id = :sid ORDER BY timestamp DESC LIMIT :lim"
        ),
        {"sid": session_id, "lim": limit},
    )
    rows = result.fetchall()
    # Возвращаем в хронологическом порядке
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


async def save_feedback(
    session_id: str,
    rating: str,
    comment: str | None,
    db_session: AsyncSession,
) -> None:
    fb = Feedback(session_id=session_id, rating=rating, comment=comment)
    db_session.add(fb)
    await db_session.commit()
