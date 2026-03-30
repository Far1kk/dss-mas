from langgraph.graph import StateGraph, END
from src.agents.ml_agent.state import MLAgentState
from src.agents.ml_agent.nodes import (
    formulate_problem_node,
    extract_data_node,
    preprocess_node,
    train_node,
    evaluate_node,
    explain_node,
    clarify_ml_node,
)


def _route_after_formulate(state: MLAgentState) -> str:
    if state.get("needs_clarification"):
        return "clarify"
    if state.get("error"):
        return "explain"
    return "extract_data"


def build_ml_graph():
    graph = StateGraph(MLAgentState)

    graph.add_node("formulate", formulate_problem_node)
    graph.add_node("clarify", clarify_ml_node)
    graph.add_node("extract_data", extract_data_node)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("train", train_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("explain", explain_node)

    graph.set_entry_point("formulate")
    graph.add_conditional_edges(
        "formulate",
        _route_after_formulate,
        {"clarify": "clarify", "extract_data": "extract_data", "explain": "explain"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("extract_data", "preprocess")
    graph.add_edge("preprocess", "train")
    graph.add_edge("train", "evaluate")
    graph.add_edge("evaluate", "explain")
    graph.add_edge("explain", END)

    return graph.compile()


ml_graph = build_ml_graph()
