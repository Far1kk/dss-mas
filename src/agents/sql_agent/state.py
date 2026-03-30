from typing import Optional
from src.agents.base import BaseAgentState


class SQLAgentState(BaseAgentState):
    generated_sql: str
    sql_valid: bool
    query_result: list[dict]
    result_summary: str
    needs_clarification: bool
    clarification_question: str
