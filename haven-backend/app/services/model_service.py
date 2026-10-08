import os
import json
import joblib
import pandas as pd
from typing import Dict, Any, Tuple, Union
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

class ModelNotAvailableError(Exception):
    pass

class ModelService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
            cls._instance = cls(
                pipeline_path=os.path.join(models_dir, "random_forest_pipeline.joblib"),
                metadata_path=os.path.join(models_dir, "random_forest_metadata.json"),
                features_path=os.path.join(models_dir, "feature_columns.json")
            )
        return cls._instance

    def __init__(
        self, 
        pipeline_path: str, 
        metadata_path: str, 
        features_path: str,
        injected_pipeline: Any = None,
        injected_metadata: dict = None,
        injected_features: Union[list, dict] = None
    ):
        self.pipeline_path = pipeline_path
        self.metadata_path = metadata_path
        self.features_path = features_path
        
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
        self._pipeline = injected_pipeline
        self._metadata = injected_metadata
        self._feature_columns = None
        
        if self._pipeline and self._metadata and injected_features is not None:
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
            if not os.path.exists(self.pipeline_path) or \
               not os.path.exists(self.metadata_path) or \
               not os.path.exists(self.features_path):
                logger.warning("Model artifacts missing. Prediction service unavailable.")
                self._is_loaded = False
                return

            import sklearn.compose._column_transformer
            if not hasattr(sklearn.compose._column_transformer, '_RemainderColsList'):
                class _RemainderColsList(list): pass
                sklearn.compose._column_transformer._RemainderColsList = _RemainderColsList
                
            self._pipeline = joblib.load(self.pipeline_path)
            
            # Patch SimpleImputer for 1.9.1 compatibility
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
            
            with open(self.metadata_path, 'r') as f:
                self._metadata = json.load(f)
                if not isinstance(self._metadata, dict):
                    raise ValueError("Metadata must be a dictionary")
                
            with open(self.features_path, 'r') as f:
                raw_features = json.load(f)
                
            self._process_features(raw_features)
            
            # Verify classes on the loaded pipeline
            classes = getattr(self._pipeline, "classes_", [])
            required_classes = {"Low", "Medium", "High"}
            if not required_classes.issubset(set(classes)):
                raise ValueError(f"Pipeline classes {list(classes)} do not contain required classes {required_classes}")

            self._is_loaded = True
            logger.info("Model artifacts loaded successfully.", version=self._get_version())
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON artifacts", error=str(e))
            self._is_loaded = False
        except Exception as e:
            logger.error("Failed to load model artifacts", error=str(e))
            self._is_loaded = False

    def _get_version(self) -> str:
        if self._metadata is None:
            return "unknown"
        return self._metadata.get("model_version", self._metadata.get("version", self._metadata.get("schema_version", "1.0")))

    def is_available(self) -> bool:
        return self._is_loaded

    def predict(self, metrics: Union[Dict[str, Any], BaseModel]) -> Tuple[str, Dict[str, float], str, str]:
        if not self._is_loaded:
            raise ModelNotAvailableError("Model artifacts are not loaded.")

        if isinstance(metrics, BaseModel):
            metrics_dict = metrics.model_dump()
        else:
            metrics_dict = metrics

        # 1. Exclude non-features to prevent leaking identity to model
        filtered_metrics = {k: v for k, v in metrics_dict.items() if k not in self.forbidden_columns}
        
        # 2. Preserve exact feature order and handle missing
        ordered_features = {}
        for col in self._feature_columns:
            ordered_features[col] = filtered_metrics.get(col, None)

        # 3. Create DataFrame
        df = pd.DataFrame([ordered_features])

        # 4. Predict
        probabilities = self._pipeline.predict_proba(df)[0]
        classes = getattr(self._pipeline, "classes_", ["Low", "Medium", "High"])
        
        prob_dict = {str(c): float(p) for c, p in zip(classes, probabilities)}
        
        final_probs = {
            "Low": prob_dict.get("Low", 0.0),
            "Medium": prob_dict.get("Medium", 0.0),
            "High": prob_dict.get("High", 0.0)
        }
        
        predicted_class = max(final_probs.items(), key=lambda x: x[1])[0]
        
        model_type = self._metadata.get("model_type", "Random Forest")
        
        return predicted_class, final_probs, model_type, self._get_version()
