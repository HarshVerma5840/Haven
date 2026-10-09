import os
import json
import joblib
import pandas as pd
import numpy as np
import shap
import structlog
from typing import Dict, List, Any, Tuple
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class ShapServiceError(Exception):
    pass

class ShapService:
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

    def __init__(self, pipeline_path: str, metadata_path: str, features_path: str):
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
        self._pipeline = None
        self._explainer = None
        self._feature_columns = None
        self._model_version = "unknown"
        self._classes = []
        
        self.load_artifacts()

    def load_artifacts(self):
        try:
            if not os.path.exists(self.pipeline_path) or \
               not os.path.exists(self.metadata_path) or \
               not os.path.exists(self.features_path):
                logger.warning("Model artifacts missing. SHAP service unavailable.")
                return

            import sklearn.compose._column_transformer
            if not hasattr(sklearn.compose._column_transformer, '_RemainderColsList'):
                class _RemainderColsList(list): pass
                sklearn.compose._column_transformer._RemainderColsList = _RemainderColsList
                
            self._pipeline = joblib.load(self.pipeline_path)
            
            # Best effort patch for scikit-learn 1.9.1 compatibility
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
                pass
            
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
                self._model_version = metadata.get("model_version", metadata.get("version", "1.0"))
                
            with open(self.features_path, 'r') as f:
                raw_features = json.load(f)
                self._process_features(raw_features)
                
            # Initialize TreeExplainer
            classifier = self._pipeline.named_steps.get('model') or self._pipeline.named_steps.get('classifier')
            if not classifier:
                raise ShapServiceError("Could not find classifier in pipeline")
                
            self._classes = getattr(self._pipeline, "classes_", ["Low", "Medium", "High"])
            self._explainer = shap.TreeExplainer(classifier)
            self._is_loaded = True
            
            logger.info("SHAP artifacts loaded successfully.")
        except Exception as e:
            logger.error("Failed to load SHAP artifacts", error=str(e))
            self._is_loaded = False

    def _process_features(self, raw_features: list | dict):
        if isinstance(raw_features, list):
            self._feature_columns = raw_features
        elif isinstance(raw_features, dict):
            self._feature_columns = raw_features.get("numeric_columns", []) + raw_features.get("categorical_columns", [])
        else:
            raise ValueError("Invalid format for feature_columns")
            
    def is_available(self) -> bool:
        return self._is_loaded

    def _get_readable_feature_names(self) -> List[str]:
        preprocessor = self._pipeline.named_steps.get('preprocessor')
        if not preprocessor:
            return self._feature_columns
            
        try:
            raw_names = preprocessor.get_feature_names_out()
            # Clean up prefixes like 'numeric__' or 'categorical__'
            clean_names = []
            for name in raw_names:
                if '__' in name:
                    name = name.split('__', 1)[1]
                clean_names.append(name)
            return clean_names
        except Exception:
            # Fallback
            return [f"feature_{i}" for i in range(1000)]
            
    def explain(self, metrics: dict, top_k: int = 5) -> dict:
        """
        Explain a single prediction.
        Returns a dictionary mapping each class (Low, Medium, High) to its top contributing features.
        """
        if not self._is_loaded:
            raise ShapServiceError("SHAP service is not available")

        # 1. Filter out identity/forbidden columns
        filtered_metrics = {k: v for k, v in metrics.items() if k not in self.forbidden_columns}
        
        # 2. Maintain feature order
        ordered_features = {}
        for col in self._feature_columns:
            ordered_features[col] = filtered_metrics.get(col, None)
            
        df = pd.DataFrame([ordered_features])
        
        # 3. Transform using preprocessor
        preprocessor = self._pipeline.named_steps.get('preprocessor')
        X_transformed = preprocessor.transform(df)
        
        # 4. Get SHAP values
        shap_values = self._explainer.shap_values(X_transformed)
        feature_names = self._get_readable_feature_names()
        
        # shap_values is typically a list of arrays (one for each class) for Random Forest
        # Each array is of shape (n_samples, n_features)
        
        explanations = {}
        
        for i, class_name in enumerate(self._classes):
            if isinstance(shap_values, list):
                class_shap = shap_values[i][0]  # First (and only) sample
            elif len(shap_values.shape) == 3:
                class_shap = shap_values[0, :, i] # (n_samples, n_features, n_classes)
            else:
                class_shap = shap_values[0] # Binary classification fallback
                
            # Combine feature names with their shap values
            feature_impacts = list(zip(feature_names, class_shap))
            
            # Sort by absolute impact for ranking, but keep original value
            sorted_impacts = sorted(feature_impacts, key=lambda x: abs(x[1]), reverse=True)
            
            top_positive = []
            top_negative = []
            
            for feat, impact in sorted_impacts:
                if impact > 0 and len(top_positive) < top_k:
                    top_positive.append({"feature": feat, "impact": float(impact)})
                elif impact < 0 and len(top_negative) < top_k:
                    top_negative.append({"feature": feat, "impact": float(impact)})
                    
            explanations[str(class_name)] = {
                "top_positive": top_positive,
                "top_negative": top_negative
            }
            
        return {
            "model_version": self._model_version,
            "disclaimer": "SHAP values represent feature contributions to the model's prediction and are not causal explanations.",
            "explanations": explanations
        }

def get_shap_service() -> ShapService:
    return ShapService.get_instance()
