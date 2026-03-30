from enum import Enum
from typing import Any, Callable


class AlgorithmType(str, Enum):
    DECISION_TREE = "decision_tree"
    NAIVE_BAYES = "naive_bayes"
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    SVM = "svm"
    ENSEMBLE = "ensemble"
    CLUSTERING = "clustering"
    PCA = "pca"
    SVD = "svd"
    ICA = "ica"
    TIME_SERIES = "time_series"
    CAUSAL_INFERENCE = "causal_inference"
    AUTO = "auto"

    @classmethod
    def from_str(cls, value: str) -> "AlgorithmType":
        value = value.lower().strip()
        for member in cls:
            if member.value == value or member.value.replace("_", " ") in value:
                return member
        # Поиск по ближайшему совпадению
        keywords = {
            "дерево": cls.DECISION_TREE,
            "байес": cls.NAIVE_BAYES,
            "линейн": cls.LINEAR_REGRESSION,
            "регресс": cls.LINEAR_REGRESSION,
            "логистич": cls.LOGISTIC_REGRESSION,
            "класс": cls.LOGISTIC_REGRESSION,
            "svm": cls.SVM,
            "вектор": cls.SVM,
            "ансамбл": cls.ENSEMBLE,
            "лес": cls.ENSEMBLE,
            "кластер": cls.CLUSTERING,
            "pca": cls.PCA,
            "главн": cls.PCA,
            "svd": cls.SVD,
            "ica": cls.ICA,
            "времен": cls.TIME_SERIES,
            "прогноз": cls.AUTO,
        }
        for kw, alg in keywords.items():
            if kw in value:
                return alg
        return cls.AUTO


class ProblemType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    DIMENSIONALITY_REDUCTION = "dimensionality_reduction"
    TIME_SERIES = "time_series"

    @classmethod
    def from_str(cls, value: str) -> "ProblemType":
        value = value.lower()
        if any(k in value for k in ["класс", "classification", "категори"]):
            return cls.CLASSIFICATION
        if any(k in value for k in ["регресс", "regression", "прогноз", "предск"]):
            return cls.REGRESSION
        if any(k in value for k in ["кластер", "cluster", "группир"]):
            return cls.CLUSTERING
        if any(k in value for k in ["pca", "svd", "ica", "снижен", "dimension"]):
            return cls.DIMENSIONALITY_REDUCTION
        if any(k in value for k in ["времен", "time", "ряд", "series"]):
            return cls.TIME_SERIES
        return cls.REGRESSION


def get_sklearn_model(algorithm: AlgorithmType, problem_type: ProblemType, params: dict):
    """Возвращает модель scikit-learn на основе типа алгоритма и задачи."""
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
    from sklearn.naive_bayes import GaussianNB
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.svm import SVC, SVR
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.decomposition import PCA, TruncatedSVD, FastICA

    is_clf = problem_type == ProblemType.CLASSIFICATION

    dispatch = {
        AlgorithmType.DECISION_TREE: (
            DecisionTreeClassifier(**params) if is_clf else DecisionTreeRegressor(**params)
        ),
        AlgorithmType.NAIVE_BAYES: GaussianNB(),
        AlgorithmType.LINEAR_REGRESSION: LinearRegression(),
        AlgorithmType.LOGISTIC_REGRESSION: LogisticRegression(max_iter=500),
        AlgorithmType.SVM: SVC() if is_clf else SVR(),
        AlgorithmType.ENSEMBLE: (
            RandomForestClassifier(n_estimators=100, **params) if is_clf
            else RandomForestRegressor(n_estimators=100, **params)
        ),
        AlgorithmType.CLUSTERING: KMeans(n_clusters=params.get("n_clusters", 3), random_state=42),
        AlgorithmType.PCA: PCA(n_components=params.get("n_components", 2)),
        AlgorithmType.SVD: TruncatedSVD(n_components=params.get("n_components", 2)),
        AlgorithmType.ICA: FastICA(n_components=params.get("n_components", 2)),
        AlgorithmType.AUTO: (
            RandomForestClassifier(n_estimators=100) if is_clf
            else RandomForestRegressor(n_estimators=100)
        ),
        AlgorithmType.TIME_SERIES: RandomForestRegressor(n_estimators=100),  # базовый fallback
        AlgorithmType.CAUSAL_INFERENCE: LinearRegression(),
    }
    return dispatch.get(algorithm, RandomForestRegressor(n_estimators=50))
