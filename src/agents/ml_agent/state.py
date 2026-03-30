from typing import Optional
from src.agents.base import BaseAgentState


class MLAgentState(BaseAgentState):
    problem_type: str               # classification / regression / clustering / ...
    algorithm_type: str             # AlgorithmType enum value
    target_column: str
    feature_columns: list[str]
    sql_for_data: str
    raw_data: list[dict]
    preprocessing_steps: list[str]
    model_params: dict
    train_metrics: dict
    best_model_name: str
    explanation: str                # Краткое объяснение (2-3 предл.)
    detailed_explanation: str       # Детальная интерпретация
    needs_clarification: bool
    clarification_question: str
