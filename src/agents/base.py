from typing import TypedDict, Optional


class BaseAgentState(TypedDict):
    session_id: str
    user_query: str
    chat_history: list[dict]        # [{"role": "user"/"assistant", "content": "..."}]
    db_schema_context: str          # DDL-схема для промптов
    llm_provider: str
    status_updates: list[str]       # Статусы для SSE
    error: Optional[str]
    final_answer: str
