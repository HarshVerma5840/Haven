import os
import json
import joblib
import pandas as pd
from typing import Dict, Any, Tuple, Union, Optional, List
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

class ModelNotAvailableError(Exception):
    pass

class ModelService:
    _instance = None
    REQUIRED_ARTIFACTS = [
        "random_forest_pipeline.joblib",
        "random_forest_metadata.json",
        "feature_columns.json"
    ]
    REQUIRED_CLASSES = {"Low", "Medium", "High"}

    @classmethod
    def resolve_model_dir(cls, custom_dir: Optional[str] = None) -> str:
        # 1. Custom directory passed explicitly
        if custom_dir:
            return os.path.abspath(custom_dir)

        # 2. Environment variable MODEL_DIR
        env_dir = os.environ.get("MODEL_DIR")
        if env_dir:
            return os.path.abspath(env_dir)

        # 3. Settings configuration
        try:
            from app.config import get_settings
            settings = get_settings()
            if getattr(settings, "model_dir", None):
                return os.path.abspath(settings.model_dir)
        except Exception:
            pass

        # 4. Standard candidate paths
        # Candidate 1: <root_backend>/models
        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidate_1 = os.path.join(backend_root, "models")
        if os.path.isdir(candidate_1) and os.path.exists(os.path.join(candidate_1, "random_forest_pipeline.joblib")):
            return os.path.abspath(candidate_1)

        # Candidate 2: sibling haven-backend/models if running from heaven/haven-backend
        parent_dir = os.path.dirname(backend_root)
        candidate_2 = os.path.join(parent_dir, "haven-backend", "models")
        if os.path.isdir(candidate_2) and os.path.exists(os.path.join(candidate_2, "random_forest_pipeline.joblib")):
            return os.path.abspath(candidate_2)

        # Candidate 3: parent models directory
        candidate_3 = os.path.join(parent_dir, "models")
        if os.path.isdir(candidate_3) and os.path.exists(os.path.join(candidate_3, "random_forest_pipeline.joblib")):
            return os.path.abspath(candidate_3)

        # Fallback to candidate_1 if it exists, else candidate_2, else candidate_1
        if os.path.isdir(candidate_1):
            return os.path.abspath(candidate_1)
        if os.path.isdir(candidate_2):
            return os.path.abspath(candidate_2)
        return os.path.abspath(candidate_1)

    @classmethod
    def get_instance(cls, model_dir: Optional[str] = None, reload: bool = False):
        if cls._instance is None or reload:
            resolved_dir = cls.resolve_model_dir(model_dir)
            cls._instance = cls(
                model_dir=resolved_dir,
                pipeline_path=os.path.join(resolved_dir, "random_forest_pipeline.joblib"),
                metadata_path=os.path.join(resolved_dir, "random_forest_metadata.json"),
                features_path=os.path.join(resolved_dir, "feature_columns.json")
            )
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def __init__(
        self,
        pipeline_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
        features_path: Optional[str] = None,
        model_dir: Optional[str] = None,
        injected_pipeline: Any = None,
        injected_metadata: Optional[dict] = None,
        injected_features: Optional[Union[list, dict]] = None
    ):
        if pipeline_path and not model_dir:
            self.model_dir = os.path.dirname(os.path.abspath(pipeline_path))
        else:
            self.model_dir = self.resolve_model_dir(model_dir)

        self.pipeline_path = pipeline_path or os.path.join(self.model_dir, "random_forest_pipeline.joblib")
        self.metadata_path = metadata_path or os.path.join(self.model_dir, "random_forest_metadata.json")
        self.features_path = features_path or os.path.join(self.model_dir, "feature_columns.json")

        self.forbidden_columns = {
            "employee_hash",
            "week_start_date",
            "week_start",
            "burnout_score",
            "burnout_risk",
            "schema_version",
            "data_completeness",
            "source_timestamp",
            "label_source"
        }

        self._is_loaded = False
        self._load_error: Optional[str] = None
        self._pipeline = injected_pipeline
        self._metadata = injected_metadata
        self._feature_columns: Optional[List[str]] = None

        if self._pipeline is not None and self._metadata is not None and injected_features is not None:
            # Validate classes on injected pipeline
            classes = getattr(self._pipeline, "classes_", None)
            if classes is not None and not self.REQUIRED_CLASSES.issubset(set(classes)):
                raise ValueError(f"Pipeline classes {list(classes)} do not contain required classes {self.REQUIRED_CLASSES}")
            self._process_features(injected_features)
            self._is_loaded = True
        else:
            self.load_model()

    def _process_features(self, raw_features: Union[list, dict]):
        features_list = []
        if isinstance(raw_features, list):
            features_list = raw_features
        elif isinstance(raw_features, dict):
            if "numeric_columns" not in raw_features or "categorical_columns" not in raw_features:
                raise ValueError("feature_columns.json must contain numeric_columns and categorical_columns")
            numeric = raw_features["numeric_columns"]
            categorical = raw_features["categorical_columns"]
            if not isinstance(numeric, list) or not isinstance(categorical, list):
                raise ValueError("numeric_columns and categorical_columns must be lists")
            features_list = numeric + categorical
        else:
            raise ValueError("feature_columns.json must contain a list or an object with numeric_columns and categorical_columns")

        # Reject duplicates
        if len(features_list) != len(set(features_list)):
            raise ValueError("Duplicate feature names found in feature_columns.json")

        # Reject forbidden columns
        for col in features_list:
            if col in self.forbidden_columns:
                raise ValueError(f"Forbidden column '{col}' found in feature_columns.json")

        self._feature_columns = features_list

    def load_model(self):
        try:
            missing_artifacts = []
            if not os.path.exists(self.pipeline_path):
                missing_artifacts.append(os.path.basename(self.pipeline_path))
            if not os.path.exists(self.metadata_path):
                missing_artifacts.append(os.path.basename(self.metadata_path))
            if not os.path.exists(self.features_path):
                missing_artifacts.append(os.path.basename(self.features_path))

            if missing_artifacts:
                error_msg = f"Missing required model artifact(s) in {self.model_dir}: {', '.join(missing_artifacts)}"
                logger.warning("Model artifacts missing. Prediction service unavailable.", missing=missing_artifacts, model_dir=self.model_dir)
                self._is_loaded = False
                self._load_error = error_msg
                return

            import sklearn.compose._column_transformer
            if not hasattr(sklearn.compose._column_transformer, '_RemainderColsList'):
                class _RemainderColsList(list): pass
                sklearn.compose._column_transformer._RemainderColsList = _RemainderColsList

            self._pipeline = joblib.load(self.pipeline_path)

            # Patch SimpleImputer for scikit-learn 1.9.1 compatibility
            try:
                if hasattr(self._pipeline, 'steps'):
                    preprocessor = dict(self._pipeline.steps).get('preprocessor')
                    if preprocessor and hasattr(preprocessor, 'transformers_'):
                        for name, transformer, cols in preprocessor.transformers_:
                            if hasattr(transformer, 'steps'):
                                for sub_name, sub_step in transformer.steps:
                                    if type(sub_step).__name__ == 'SimpleImputer':
                                        if hasattr(sub_step, '_fit_dtype') and not hasattr(sub_step, '_fill_dtype'):
                                            sub_step._fill_dtype = sub_step._fit_dtype

                    for step_name, step_obj in self._pipeline.steps:
                        if type(step_obj).__name__ == 'RandomForestClassifier':
                            step_obj.n_jobs = 1
            except Exception:
                pass # Best effort patching

            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self._metadata = json.load(f)
                if not isinstance(self._metadata, dict):
                    raise ValueError("Metadata must be a dictionary")

            with open(self.features_path, 'r', encoding='utf-8') as f:
                raw_features = json.load(f)

            self._process_features(raw_features)

            # Verify classes on the loaded pipeline
            classes = getattr(self._pipeline, "classes_", None)
            if classes is None or not self.REQUIRED_CLASSES.issubset(set(classes)):
                raise ValueError(f"Pipeline classes {list(classes) if classes is not None else None} do not contain required classes {self.REQUIRED_CLASSES}")

            self._is_loaded = True
            self._load_error = None
            logger.info("Model artifacts loaded successfully.", version=self._get_version(), model_dir=self.model_dir)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON model artifacts: {str(e)}"
            logger.error("Failed to parse JSON artifacts", error=str(e))
            self._is_loaded = False
            self._load_error = error_msg
        except Exception as e:
            error_msg = f"Failed to load model artifacts: {str(e)}"
            logger.error("Failed to load model artifacts", error=str(e))
            self._is_loaded = False
            self._load_error = error_msg

    def _get_version(self) -> str:
        if self._metadata is None:
            return "unknown"
        return str(self._metadata.get("model_version", self._metadata.get("version", self._metadata.get("schema_version", "1.0"))))

    def get_model_name(self) -> str:
        if self._metadata and isinstance(self._metadata, dict):
            return str(self._metadata.get("model_type", "RandomForestClassifier"))
        return "RandomForestClassifier"

    def get_model_version(self) -> str:
        return self._get_version()

    def get_load_error(self) -> Optional[str]:
        return self._load_error

    def get_model_dir(self) -> str:
        return self.model_dir

    def is_available(self) -> bool:
        return self._is_loaded and self._pipeline is not None

    def predict(self, metrics: Union[Dict[str, Any], BaseModel]) -> Tuple[str, Dict[str, float], str, str]:
        if not self.is_available():
            raise ModelNotAvailableError(self._load_error or "Model artifacts are not loaded.")

        if isinstance(metrics, BaseModel):
            metrics_dict = metrics.model_dump()
        else:
            metrics_dict = metrics

        # 1. Exclude non-features to prevent leaking identity or target labels to model
        filtered_metrics = {k: v for k, v in metrics_dict.items() if k not in self.forbidden_columns}

        # 2. Preserve exact feature order from feature_columns.json and handle missing
        ordered_features = {}
        for col in self._feature_columns:
            ordered_features[col] = filtered_metrics.get(col, None)

        # 3. Create DataFrame with ordered features
        df = pd.DataFrame([ordered_features])

        # 4. Predict probabilities
        probabilities = self._pipeline.predict_proba(df)[0]
        classes = getattr(self._pipeline, "classes_", ["Low", "Medium", "High"])

        prob_dict = {str(c): float(p) for c, p in zip(classes, probabilities)}

        final_probs = {
            "Low": prob_dict.get("Low", 0.0),
            "Medium": prob_dict.get("Medium", 0.0),
            "High": prob_dict.get("High", 0.0)
        }

        predicted_class = max(final_probs.items(), key=lambda x: x[1])[0]
        model_type = self.get_model_name()

        return predicted_class, final_probs, model_type, self.get_model_version()
