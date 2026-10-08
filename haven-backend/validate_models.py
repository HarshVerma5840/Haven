import os
import sys
import json
import joblib
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.schemas.metrics import WeeklyEmployeeMetricsInput

def validate_artifacts():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    pipeline_path = os.path.join(models_dir, "random_forest_pipeline.joblib")
    metadata_path = os.path.join(models_dir, "random_forest_metadata.json")
    features_path = os.path.join(models_dir, "feature_columns.json")
    
    print("--- Haven Model Artifact Validator ---")
    
    # 1. Files exist
    if not os.path.exists(pipeline_path):
        print(f"❌ Missing: {pipeline_path}")
        sys.exit(1)
    if not os.path.exists(metadata_path):
        print(f"❌ Missing: {metadata_path}")
        sys.exit(1)
    if not os.path.exists(features_path):
        print(f"❌ Missing: {features_path}")
        sys.exit(1)
    print("✅ All three artifact files exist.")
    
    # 2. Metadata is valid JSON
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        print("✅ Metadata is valid JSON.")
    except Exception as e:
        print(f"❌ Metadata JSON parsing failed: {e}")
        sys.exit(1)
        
    # Model type and target
    model_type = metadata.get("model_type", "").lower()
    if "random forest" not in model_type and "randomforest" not in model_type:
        print(f"❌ Warning: Expected RandomForest model type, got '{model_type}'")
    else:
        print(f"✅ Model type in metadata matches RandomForest.")
        
    model_version = metadata.get("model_version", metadata.get("version", metadata.get("schema_version", "unknown")))
    print(f"ℹ️ Model version: {model_version}")

    if "sklearn_version" in metadata:
        print(f"ℹ️ Recorded scikit-learn version: {metadata['sklearn_version']}")
    
    # 3. Feature list validation
    try:
        with open(features_path, 'r') as f:
            raw_features = json.load(f)
    except Exception as e:
        print(f"❌ feature_columns.json parsing failed: {e}")
        sys.exit(1)

    features = []
    if isinstance(raw_features, list):
        features = raw_features
        print("✅ feature_columns.json uses the legacy list format.")
    elif isinstance(raw_features, dict):
        if "numeric_columns" not in raw_features or "categorical_columns" not in raw_features:
            print("❌ Object format must contain 'numeric_columns' and 'categorical_columns'")
            sys.exit(1)
        
        numeric = raw_features.get("numeric_columns", [])
        categorical = raw_features.get("categorical_columns", [])
        features = numeric + categorical
        
        target = raw_features.get("target")
        if target != "burnout_risk":
            print(f"❌ Expected target 'burnout_risk', got '{target}'")
            sys.exit(1)
            
        print("✅ feature_columns.json uses the object format and target is burnout_risk.")
    else:
        print("❌ feature_columns.json must contain a list or an object.")
        sys.exit(1)

    # Feature uniqueness
    if len(features) != len(set(features)):
        print("❌ Duplicate feature names found in feature_columns.json")
        sys.exit(1)
    print("✅ Feature names are unique.")
        
    forbidden_columns = {
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
    
    for forbidden in forbidden_columns:
        if forbidden in features:
            print(f"❌ Forbidden identity/target column found in model inputs: {forbidden}")
            sys.exit(1)
    print("✅ No forbidden identity or target columns appear as model inputs.")
    
    valid_metrics = set(WeeklyEmployeeMetricsInput.model_fields.keys())
    for feature in features:
        if feature not in valid_metrics:
            print(f"❌ Feature '{feature}' does not exist in the WeeklyEmployeeMetricsInput schema.")
            sys.exit(1)
    print("✅ All features match the expected Haven schema.")
    
    # 4. Load Joblib
    try:
        import sklearn.compose._column_transformer
        if not hasattr(sklearn.compose._column_transformer, '_RemainderColsList'):
            class _RemainderColsList(list): pass
            sklearn.compose._column_transformer._RemainderColsList = _RemainderColsList
            
        pipeline = joblib.load(pipeline_path)
        
        # Patch SimpleImputer for 1.9.1 compatibility
        try:
            if hasattr(pipeline, 'steps'):
                preprocessor = dict(pipeline.steps).get('preprocessor')
                if preprocessor and hasattr(preprocessor, 'transformers_'):
                    for name, transformer, cols in preprocessor.transformers_:
                        if hasattr(transformer, 'steps'):
                            for sub_name, sub_step in transformer.steps:
                                if type(sub_step).__name__ == 'SimpleImputer':
                                    if hasattr(sub_step, '_fit_dtype') and not hasattr(sub_step, '_fill_dtype'):
                                        sub_step._fill_dtype = sub_step._fit_dtype
                
                for step_name, step_obj in pipeline.steps:
                    if type(step_obj).__name__ == 'RandomForestClassifier':
                        step_obj.n_jobs = 1
        except Exception:
            pass # Best effort patching
            
        print("✅ Model pipeline loaded successfully via joblib (with compat patches).")
    except Exception as e:
        print(f"❌ Failed to load joblib pipeline: {e}")
        sys.exit(1)
        
    # 5. Predict on small valid fixture
    try:
        fixture = {}
        for feature in features:
            fixture[feature] = 0
            
        df = pd.DataFrame([fixture])
        probs = pipeline.predict_proba(df)[0]
        
        classes = getattr(pipeline, "classes_", [])
        required_classes = {"Low", "Medium", "High"}
        if not required_classes.issubset(set(classes)):
            print(f"❌ Expected classes {required_classes} to be exposed, got {list(classes)}")
            sys.exit(1)
            
        print(f"✅ Successfully ran prediction on a small valid fixture.")
        print(f"✅ Final classifier exposes classes: {list(classes)}")
    except Exception as e:
        print(f"❌ Failed to predict on fixture: {e}")
        sys.exit(1)

    print("--- Validation Successful! The model is ready for Haven backend. ---")

if __name__ == "__main__":
    validate_artifacts()
