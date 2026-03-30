import asyncio
from typing import Callable, Awaitable
from langchain_core.messages import SystemMessage, HumanMessage
from src.agents.base import BaseAgentState
from src.llm.factory import LLMFactory
from src.db.repository import DB_SCHEMA_CONTEXT
from src.logger import log

SYSTEM_ROUTE = """Ты — оркестратор многоагентной системы анализа данных. Определи тип запроса пользователя.

Доступные типы:
- SQL: поиск, фильтрация, агрегация данных из БД (найди, покажи, сколько, список, выведи)
- ML: машинное обучение (спрогнозируй, предскажи, классифицируй, обучи, кластеризуй, регресс)
- UNKNOWN: запрос непонятен или не относится к задачам системы

Верни ТОЛЬКО одно слово: SQL, ML или UNKNOWN."""


class AgentType:
    SQL = "SQL"
    ML = "ML"
    UNKNOWN = "UNKNOWN"


StatusCallback = Callable[[str], Awaitable[None]]


async def route_query(query: str, llm_provider: str) -> str:
    llm = LLMFactory.get_llm(llm_provider)
    messages = [
        SystemMessage(content=SYSTEM_ROUTE),
        HumanMessage(content=f"Запрос: {query}"),
    ]
    try:
        response = await llm.ainvoke(messages)
        result = response.content.strip().upper()
        if "SQL" in result:
            return AgentType.SQL
        if "ML" in result:
            return AgentType.ML
        return AgentType.UNKNOWN
    except Exception as e:
        log.error(f"[Orchestrator] Ошибка роутинга: {e}")
        # Fallback: простая эвристика
        q = query.lower()
        ml_keywords = ["спрогноз", "предск", "класс", "обучи", "кластер", "регресс", "модел"]
        if any(k in q for k in ml_keywords):
            return AgentType.ML
        return AgentType.SQL


async def run(
    query: str,
    session_id: str,
    llm_provider: str,
    chat_history: list[dict],
    status_callback: StatusCallback,
) -> str:
    """
    Главная точка входа. Роутит запрос к нужному агенту и возвращает финальный ответ.
    status_callback вызывается с текстом статуса для SSE-стриминга.
    """
    await status_callback("Анализирую запрос...")
    agent_type = await route_query(query, llm_provider)
    log.info(f"[Orchestrator] Тип запроса: {agent_type} | {query[:80]}")

    base_state: dict = {
        "session_id": session_id,
        "user_query": query,
        "chat_history": chat_history,
        "db_schema_context": DB_SCHEMA_CONTEXT,
        "llm_provider": llm_provider,
        "status_updates": [],
        "error": None,
        "final_answer": "",
    }

    if agent_type == AgentType.SQL:
        await status_callback("Запускаю агент поиска в базе данных...")
        from src.agents.sql_agent.graph import sql_graph
        from src.agents.sql_agent.state import SQLAgentState

        state = SQLAgentState(
            **base_state,
            generated_sql="",
            sql_valid=False,
            query_result=[],
            result_summary="",
            needs_clarification=False,
            clarification_question="",
        )
        result = await sql_graph.ainvoke(state)

    elif agent_type == AgentType.ML:
        await status_callback("Запускаю агент машинного обучения...")
        from src.agents.ml_agent.graph import ml_graph
        from src.agents.ml_agent.state import MLAgentState
        from src.config import settings

        state = MLAgentState(
            **base_state,
            problem_type="",
            algorithm_type="auto",
            target_column="",
            feature_columns=[],
            sql_for_data="",
            raw_data=[],
            preprocessing_steps=[],
            model_params={},
            train_metrics={},
            best_model_name="",
            explanation="",
            detailed_explanation="",
            needs_clarification=False,
            clarification_question="",
        )
        result = await ml_graph.ainvoke(state)

    else:
        return "Не удалось определить тип задачи. Попробуйте уточнить запрос: используйте слова 'найди', 'покажи', 'спрогнозируй' или 'классифицируй'."

    # Отправляем промежуточные статусы
    for update in result.get("status_updates", []):
        await status_callback(update)

    if result.get("error"):
        await status_callback(f"Ошибка: {result['error']}")

    return result.get("final_answer", "Ответ не получен.")
