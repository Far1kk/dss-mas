import json
import sqlparse
from langchain_core.messages import SystemMessage, HumanMessage
from src.agents.sql_agent.state import SQLAgentState
from src.llm.factory import LLMFactory
from src.db.repository import execute_raw_sql
from src.db.engine import AsyncSessionLocal
from src.logger import log

SYSTEM_GENERATE_SQL = """Ты — эксперт по базам данных PostgreSQL. Твоя задача — генерировать корректные SQL-запросы.

Схема базы данных:
{db_schema}

Правила:
1. Используй только таблицы из схемы dds
2. Возвращай ТОЛЬКО SQL-запрос, без пояснений, без markdown-блоков
3. Для дат используй формат 'YYYY-MM-DD'
4. Всегда добавляй LIMIT 100 если не указано иное
5. Используй русские псевдонимы (AS "Название проекта")"""

SYSTEM_FORMAT_RESULT = """Ты — аналитик данных. Тебе нужно на русском языке понятно объяснить результаты SQL-запроса.

Запрос пользователя: {user_query}
SQL-запрос: {sql}

Правила:
1. Отвечай только на русском языке
2. Кратко и по существу — 1-3 абзаца
3. Если данных нет — скажи "По вашему запросу данные не найдены"
4. Выдели ключевые числа и факты
5. Не повторяй SQL-запрос"""

SYSTEM_CLARIFY = """Ты — аналитик данных. Запрос пользователя неоднозначен. Задай уточняющий вопрос на русском языке.

Запрос пользователя: {user_query}
Доступные таблицы: dim_project, dim_counteragent, dim_contract, fact_forecast

Сформулируй один конкретный уточняющий вопрос."""


def _format_history(history: list[dict]) -> str:
    if not history:
        return ""
    lines = []
    for msg in history[-6:]:  # последние 6 сообщений
        role = "Пользователь" if msg["role"] == "user" else "Система"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def _is_ambiguous(query: str) -> bool:
    """Простая эвристика для определения неоднозначных запросов."""
    ambiguous_keywords = ["что-нибудь", "что-то", "покажи всё", "расскажи", "как дела"]
    q = query.lower()
    return any(kw in q for kw in ambiguous_keywords) and len(query) < 20


async def generate_sql_node(state: SQLAgentState) -> dict:
    log.info(f"[SQL] Генерация SQL для: {state['user_query'][:80]}")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Генерирую SQL-запрос...")

    llm = LLMFactory.get_llm(state["llm_provider"])
    history_str = _format_history(state.get("chat_history", []))

    system_prompt = SYSTEM_GENERATE_SQL.format(db_schema=state["db_schema_context"])
    user_content = f"Запрос: {state['user_query']}"
    if history_str:
        user_content = f"История диалога:\n{history_str}\n\n{user_content}"

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]

    try:
        response = await llm.ainvoke(messages)
        sql = response.content.strip()
        # Убираем markdown если LLM добавил
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        sql = sql.strip()

        # Базовая валидация
        parsed = sqlparse.parse(sql)
        sql_valid = bool(parsed and parsed[0].tokens)
        log.info(f"[SQL] Сгенерирован SQL: {sql[:100]}")
    except Exception as e:
        log.error(f"[SQL] Ошибка генерации SQL: {e}")
        return {
            "generated_sql": "",
            "sql_valid": False,
            "error": f"Ошибка генерации SQL: {str(e)}",
            "status_updates": status_updates,
        }

    return {
        "generated_sql": sql,
        "sql_valid": sql_valid,
        "error": None,
        "status_updates": status_updates,
    }


async def execute_sql_node(state: SQLAgentState) -> dict:
    log.info("[SQL] Выполнение SQL-запроса")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Выполняю запрос к базе данных...")

    if not state.get("sql_valid") or not state.get("generated_sql"):
        return {
            "query_result": [],
            "error": "SQL-запрос не был сгенерирован или невалиден",
            "status_updates": status_updates,
        }

    try:
        async with AsyncSessionLocal() as session:
            results = await execute_raw_sql(state["generated_sql"], session)
        log.info(f"[SQL] Получено строк: {len(results)}")
        return {"query_result": results, "error": None, "status_updates": status_updates}
    except Exception as e:
        log.error(f"[SQL] Ошибка выполнения SQL: {e}")
        return {
            "query_result": [],
            "error": f"Ошибка выполнения запроса: {str(e)}",
            "status_updates": status_updates,
        }


async def format_result_node(state: SQLAgentState) -> dict:
    log.info("[SQL] Форматирование результата")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Формирую ответ...")

    results = state.get("query_result", [])

    if state.get("error"):
        final_answer = f"Произошла ошибка при выполнении запроса: {state['error']}"
        return {"final_answer": final_answer, "status_updates": status_updates}

    if not results:
        return {
            "final_answer": "По вашему запросу данные не найдены.",
            "status_updates": status_updates,
        }

    llm = LLMFactory.get_llm(state["llm_provider"])
    # Ограничиваем данные для промпта
    results_str = json.dumps(results[:20], ensure_ascii=False, default=str)

    system_prompt = SYSTEM_FORMAT_RESULT.format(
        user_query=state["user_query"],
        sql=state.get("generated_sql", ""),
    )
    user_content = f"Результаты запроса ({len(results)} строк):\n{results_str}"

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]

    try:
        response = await llm.ainvoke(messages)
        final_answer = response.content.strip()
    except Exception as e:
        log.error(f"[SQL] Ошибка форматирования результата: {e}")
        # Fallback: возвращаем сырые данные
        final_answer = f"Найдено {len(results)} записей:\n" + json.dumps(
            results[:10], ensure_ascii=False, default=str, indent=2
        )

    return {"final_answer": final_answer, "status_updates": status_updates}


async def clarify_node(state: SQLAgentState) -> dict:
    log.info("[SQL] Запрос уточнения")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Уточняю запрос...")

    llm = LLMFactory.get_llm(state["llm_provider"])
    system_prompt = SYSTEM_CLARIFY.format(user_query=state["user_query"])
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=state["user_query"])]

    try:
        response = await llm.ainvoke(messages)
        question = response.content.strip()
    except Exception as e:
        question = "Уточните, пожалуйста, ваш запрос."

    return {
        "clarification_question": question,
        "final_answer": question,
        "status_updates": status_updates,
    }
