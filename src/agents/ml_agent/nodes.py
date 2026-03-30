import json
import asyncio
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from src.agents.ml_agent.state import MLAgentState
from src.agents.ml_agent.algorithms import AlgorithmType, ProblemType, get_sklearn_model
from src.llm.factory import LLMFactory
from src.db.repository import execute_raw_sql
from src.db.engine import AsyncSessionLocal
from src.logger import log

# ---------------------------------------------------------------------------
# Промпты
# ---------------------------------------------------------------------------

SYSTEM_FORMULATE = """Ты — эксперт по машинному обучению. Проанализируй запрос пользователя и схему БД.

Схема БД:
{db_schema}

Верни JSON (только JSON, без пояснений):
{{
  "problem_type": "regression|classification|clustering|dimensionality_reduction|time_series",
  "algorithm_type": "auto|decision_tree|naive_bayes|linear_regression|logistic_regression|svm|ensemble|clustering|pca|svd|ica|time_series",
  "target_column": "название целевого столбца или пустая строка",
  "feature_columns": ["столбец1", "столбец2"],
  "table": "основная таблица (например dds.fact_forecast)",
  "needs_clarification": false,
  "clarification_question": ""
}}"""

SYSTEM_EXTRACT_SQL = """Ты — эксперт по SQL. Сгенерируй SQL-запрос для извлечения данных для задачи машинного обучения.

Схема БД:
{db_schema}

Задача: {problem_description}
Целевой столбец: {target_column}
Признаки: {feature_columns}

Верни ТОЛЬКО SQL без пояснений. Добавь LIMIT 1000."""

SYSTEM_EXPLAIN_BRIEF = """Ты — аналитик данных. Напиши краткое объяснение результатов ML-модели на русском языке (2-3 предложения).

Задача: {problem_type}
Алгоритм: {algorithm}
Метрики: {metrics}
Запрос пользователя: {user_query}

Объясни просто и понятно, без технических терминов."""

SYSTEM_EXPLAIN_DETAILED = """Ты — эксперт по машинному обучению. Дай детальную интерпретацию результатов на русском языке.

Задача: {problem_type}
Алгоритм: {algorithm}
Метрики: {metrics}
Признаки: {features}
Целевая переменная: {target}
Размер обучающей выборки: {data_size}
Запрос пользователя: {user_query}

Включи:
1. Интерпретацию метрик
2. Практические выводы
3. Ограничения модели
4. Рекомендации"""


# ---------------------------------------------------------------------------
# Узлы графа
# ---------------------------------------------------------------------------

async def formulate_problem_node(state: MLAgentState) -> dict:
    log.info(f"[ML] Формулировка задачи: {state['user_query'][:80]}")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Формулирую задачу машинного обучения...")

    llm = LLMFactory.get_llm(state["llm_provider"])
    system_prompt = SYSTEM_FORMULATE.format(db_schema=state["db_schema_context"])
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Запрос пользователя: {state['user_query']}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        # Убираем markdown если есть
        if "```" in content:
            content = content.split("```")[1].lstrip("json").strip()

        data = json.loads(content)
        return {
            "problem_type": ProblemType.from_str(data.get("problem_type", "regression")).value,
            "algorithm_type": AlgorithmType.from_str(data.get("algorithm_type", "auto")).value,
            "target_column": data.get("target_column", ""),
            "feature_columns": data.get("feature_columns", []),
            "needs_clarification": data.get("needs_clarification", False),
            "clarification_question": data.get("clarification_question", ""),
            "error": None,
            "status_updates": status_updates,
        }
    except Exception as e:
        log.error(f"[ML] Ошибка формулировки задачи: {e}")
        # Fallback: пытаемся определить из текста запроса
        query = state["user_query"].lower()
        problem_type = ProblemType.from_str(query).value
        algorithm = AlgorithmType.from_str(query).value
        return {
            "problem_type": problem_type,
            "algorithm_type": algorithm,
            "target_column": "fact_sum",
            "feature_columns": ["forecast_sum", "income_subcounteragent"],
            "needs_clarification": False,
            "clarification_question": "",
            "error": None,
            "status_updates": status_updates,
        }


async def extract_data_node(state: MLAgentState) -> dict:
    log.info("[ML] Извлечение данных из БД")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Извлекаю данные из базы данных...")

    llm = LLMFactory.get_llm(state["llm_provider"])

    feature_list = ", ".join(state.get("feature_columns", []))
    target = state.get("target_column", "fact_sum")
    problem_desc = f"{state.get('problem_type', 'regression')} — цель: {target}, признаки: {feature_list}"

    system_prompt = SYSTEM_EXTRACT_SQL.format(
        db_schema=state["db_schema_context"],
        problem_description=problem_desc,
        target_column=target,
        feature_columns=feature_list,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Задача: {state['user_query']}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        sql = response.content.strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        sql = sql.strip()

        async with AsyncSessionLocal() as session:
            raw_data = await execute_raw_sql(sql, session)

        log.info(f"[ML] Извлечено строк: {len(raw_data)}")
        return {
            "sql_for_data": sql,
            "raw_data": raw_data,
            "error": None,
            "status_updates": status_updates,
        }
    except Exception as e:
        log.error(f"[ML] Ошибка извлечения данных: {e}")
        return {
            "sql_for_data": "",
            "raw_data": [],
            "error": f"Ошибка извлечения данных: {str(e)}",
            "status_updates": status_updates,
        }


async def preprocess_node(state: MLAgentState) -> dict:
    log.info("[ML] Предобработка данных")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Предобрабатываю данные...")

    raw_data = state.get("raw_data", [])
    if not raw_data:
        return {
            "preprocessing_steps": ["Нет данных для обработки"],
            "error": "Нет данных для обучения модели",
            "status_updates": status_updates,
        }

    # Выполняем синхронно в executor чтобы не блокировать event loop
    loop = asyncio.get_event_loop()
    steps, processed = await loop.run_in_executor(None, _sync_preprocess, raw_data, state)

    return {
        "preprocessing_steps": steps,
        "raw_data": processed,  # обновлённые данные
        "error": None,
        "status_updates": status_updates,
    }


def _sync_preprocess(raw_data: list[dict], state: dict) -> tuple[list[str], list[dict]]:
    """Синхронная предобработка с pandas."""
    import pandas as pd
    import numpy as np

    steps = []
    df = pd.DataFrame(raw_data)

    # Шаг 1: Удаление полностью пустых строк
    initial_len = len(df)
    df.dropna(how="all", inplace=True)
    if len(df) < initial_len:
        steps.append(f"Удалено {initial_len - len(df)} пустых строк")

    # Шаг 2: Заполнение числовых NaN медианой
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            df[col].fillna(df[col].median(), inplace=True)
            steps.append(f"Заполнено {null_count} пропусков в '{col}' медианой")

    # Шаг 3: Кодирование категориальных переменных
    cat_cols = df.select_dtypes(include=["object"]).columns
    for col in cat_cols:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            df[col].fillna("Unknown", inplace=True)
        df[col] = pd.Categorical(df[col]).codes
        steps.append(f"Закодирован столбец '{col}'")

    # Шаг 4: Обработка дат
    for col in df.columns:
        if "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col]).astype(np.int64) // 10**9
                steps.append(f"Преобразована дата '{col}' в timestamp")
            except Exception:
                df.drop(columns=[col], inplace=True)
                steps.append(f"Удалён столбец с датой '{col}'")

    if not steps:
        steps.append("Предобработка не потребовалась — данные уже чистые")

    return steps, df.to_dict("records")


async def train_node(state: MLAgentState) -> dict:
    log.info(f"[ML] Обучение модели: {state.get('algorithm_type')}")
    status_updates = list(state.get("status_updates", []))
    status_updates.append(f"Обучаю модель ({state.get('algorithm_type', 'auto')})...")

    raw_data = state.get("raw_data", [])
    if not raw_data:
        return {
            "train_metrics": {},
            "best_model_name": "Нет данных",
            "error": "Нет данных для обучения",
            "status_updates": status_updates,
        }

    loop = asyncio.get_event_loop()
    try:
        metrics, model_name = await loop.run_in_executor(
            None, _sync_train, raw_data, state
        )
        return {
            "train_metrics": metrics,
            "best_model_name": model_name,
            "error": None,
            "status_updates": status_updates,
        }
    except Exception as e:
        log.error(f"[ML] Ошибка обучения: {e}")
        return {
            "train_metrics": {},
            "best_model_name": "Ошибка",
            "error": f"Ошибка обучения модели: {str(e)}",
            "status_updates": status_updates,
        }


def _sync_train(raw_data: list[dict], state: dict) -> tuple[dict, str]:
    import pandas as pd
    import numpy as np

    df = pd.DataFrame(raw_data)
    problem_type = ProblemType.from_str(state.get("problem_type", "regression"))
    algorithm = AlgorithmType.from_str(state.get("algorithm_type", "auto"))
    target_col = state.get("target_column", "")
    feature_cols = state.get("feature_columns", [])

    # Определяем целевой столбец автоматически если не задан
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not target_col or target_col not in df.columns:
        # Берём первый числовой столбец с достаточной вариацией
        for col in numeric_cols:
            if df[col].nunique() > 5:
                target_col = col
                break
        if not target_col:
            target_col = numeric_cols[0] if numeric_cols else df.columns[0]

    # Определяем признаки
    if not feature_cols or not all(c in df.columns for c in feature_cols):
        feature_cols = [c for c in numeric_cols if c != target_col]

    if not feature_cols:
        raise ValueError("Не удалось определить признаковые столбцы")

    X = df[feature_cols].fillna(0).values
    y = df[target_col].fillna(0).values

    # Разбивка на train/test
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Попытка LightAutoML
    from src.config import settings
    use_laml = settings.use_lightautoml
    if use_laml and algorithm in (AlgorithmType.AUTO, AlgorithmType.ENSEMBLE):
        try:
            return _train_lightautoml(X_train, X_test, y_train, y_test, problem_type, feature_cols, target_col)
        except Exception as e:
            log.warning(f"LightAutoML недоступен, переключение на sklearn: {e}")

    # Fallback: scikit-learn
    model = get_sklearn_model(algorithm, problem_type, state.get("model_params", {}))

    if problem_type in (ProblemType.CLUSTERING, ProblemType.DIMENSIONALITY_REDUCTION):
        model.fit(X)
        return _unsupervised_metrics(model, X, problem_type, algorithm), type(model).__name__

    model.fit(X_train, y_train)
    return _compute_metrics(model, X_test, y_test, problem_type), type(model).__name__


def _train_lightautoml(X_train, X_test, y_train, y_test, problem_type, feature_cols, target_col):
    import pandas as pd
    import numpy as np
    from lightautoml.automl.presets.tabular_presets import TabularAutoML
    from lightautoml.tasks import Task

    task_name = "reg" if problem_type == ProblemType.REGRESSION else "binary"

    train_df = pd.DataFrame(X_train, columns=feature_cols)
    train_df[target_col] = y_train
    test_df = pd.DataFrame(X_test, columns=feature_cols)
    test_df[target_col] = y_test

    automl = TabularAutoML(task=Task(task_name), timeout=120)
    oof_preds = automl.fit_predict(train_df, roles={"target": target_col})
    test_preds = automl.predict(test_df)

    y_pred = test_preds.data[:, 0]

    if problem_type == ProblemType.REGRESSION:
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        mae = float(mean_absolute_error(y_test, y_pred))
        return {"RMSE": round(rmse, 4), "R²": round(r2, 4), "MAE": round(mae, 4)}, "LightAutoML (AutoML)"
    else:
        from sklearn.metrics import accuracy_score, f1_score
        y_pred_bin = (y_pred > 0.5).astype(int)
        acc = float(accuracy_score(y_test, y_pred_bin))
        f1 = float(f1_score(y_test, y_pred_bin, average="weighted", zero_division=0))
        return {"Accuracy": round(acc, 4), "F1": round(f1, 4)}, "LightAutoML (AutoML)"


def _compute_metrics(model, X_test, y_test, problem_type: ProblemType) -> dict:
    import numpy as np

    y_pred = model.predict(X_test)

    if problem_type == ProblemType.REGRESSION:
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        mae = float(mean_absolute_error(y_test, y_pred))
        return {"RMSE": round(rmse, 4), "R²": round(r2, 4), "MAE": round(mae, 4)}

    if problem_type == ProblemType.CLASSIFICATION:
        from sklearn.metrics import accuracy_score, f1_score
        acc = float(accuracy_score(y_test, y_pred))
        f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
        return {"Accuracy": round(acc, 4), "F1": round(f1, 4)}

    return {}


def _unsupervised_metrics(model, X, problem_type: ProblemType, algorithm: AlgorithmType) -> dict:
    if problem_type == ProblemType.CLUSTERING:
        from sklearn.metrics import silhouette_score
        labels = model.labels_
        try:
            sil = float(silhouette_score(X, labels))
            return {"Силуэтный коэффициент": round(sil, 4), "Кластеров": int(len(set(labels)))}
        except Exception:
            return {"Кластеров": int(len(set(labels)))}

    if problem_type == ProblemType.DIMENSIONALITY_REDUCTION:
        if hasattr(model, "explained_variance_ratio_"):
            total = float(sum(model.explained_variance_ratio_))
            return {"Объяснённая дисперсия": round(total, 4)}
        return {}

    return {}


async def evaluate_node(state: MLAgentState) -> dict:
    log.info("[ML] Оценка качества модели")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Оцениваю качество модели...")

    metrics = state.get("train_metrics", {})
    if not metrics:
        return {"status_updates": status_updates}

    log.info(f"[ML] Метрики: {metrics}")
    return {"status_updates": status_updates}


async def explain_node(state: MLAgentState) -> dict:
    log.info("[ML] Генерация объяснения результатов")
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Подготавливаю объяснение результатов...")

    llm = LLMFactory.get_llm(state["llm_provider"])
    metrics_str = json.dumps(state.get("train_metrics", {}), ensure_ascii=False)

    # Краткое объяснение
    brief_prompt = SYSTEM_EXPLAIN_BRIEF.format(
        problem_type=state.get("problem_type", ""),
        algorithm=state.get("best_model_name", ""),
        metrics=metrics_str,
        user_query=state["user_query"],
    )

    # Детальная интерпретация
    detailed_prompt = SYSTEM_EXPLAIN_DETAILED.format(
        problem_type=state.get("problem_type", ""),
        algorithm=state.get("best_model_name", ""),
        metrics=metrics_str,
        features=", ".join(state.get("feature_columns", [])),
        target=state.get("target_column", ""),
        data_size=len(state.get("raw_data", [])),
        user_query=state["user_query"],
    )

    try:
        brief_response, detailed_response = await asyncio.gather(
            llm.ainvoke([SystemMessage(content=brief_prompt), HumanMessage(content="Краткое объяснение:")]),
            llm.ainvoke([SystemMessage(content=detailed_prompt), HumanMessage(content="Детальная интерпретация:")]),
        )
        explanation = brief_response.content.strip()
        detailed_explanation = detailed_response.content.strip()
    except Exception as e:
        log.error(f"[ML] Ошибка генерации объяснения: {e}")
        explanation = f"Модель обучена. Метрики: {metrics_str}"
        detailed_explanation = f"Алгоритм: {state.get('best_model_name', 'N/A')}\nМетрики: {metrics_str}"

    final_answer = f"{explanation}\n\n---\n\n{detailed_explanation}"

    return {
        "explanation": explanation,
        "detailed_explanation": detailed_explanation,
        "final_answer": final_answer,
        "status_updates": status_updates,
    }


async def clarify_ml_node(state: MLAgentState) -> dict:
    status_updates = list(state.get("status_updates", []))
    status_updates.append("Уточняю задачу...")
    question = state.get("clarification_question", "Уточните, пожалуйста, задачу машинного обучения.")
    return {
        "final_answer": question,
        "status_updates": status_updates,
    }
