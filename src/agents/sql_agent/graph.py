from langgraph.graph import StateGraph, END
from src.agents.sql_agent.state import SQLAgentState
from src.agents.sql_agent.nodes import (
    generate_sql_node,
    execute_sql_node,
    format_result_node,
    clarify_node,
    _is_ambiguous,
)


def _route_start(state: SQLAgentState) -> str:
    if state.get("needs_clarification") or _is_ambiguous(state.get("user_query", "")):
        return "clarify"
    return "generate_sql"


def build_sql_graph():
    graph = StateGraph(SQLAgentState)

    graph.add_node("clarify", clarify_node)
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("format_result", format_result_node)

    graph.set_conditional_entry_point(
        _route_start,
        {"clarify": "clarify", "generate_sql": "generate_sql"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("generate_sql", "execute_sql")
    graph.add_edge("execute_sql", "format_result")
    graph.add_edge("format_result", END)

    return graph.compile()


sql_graph = build_sql_graph()
