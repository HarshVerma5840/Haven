from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import structlog

logger = structlog.get_logger(__name__)

def evaluate_classification_model(y_true, y_pred, labels=["Low", "Medium", "High"]):
    """
    Computes required baseline classification metrics.
    """
    accuracy = accuracy_score(y_true, y_pred)
    
    # We use weighted metrics since class distribution might be imbalanced
    precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    
    conf_matrix = confusion_matrix(y_true, y_pred, labels=labels)
    
    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "confusion_matrix": conf_matrix.tolist()
    }
    
    logger.info("Evaluation Complete", 
                accuracy=round(accuracy, 3),
                f1_score=round(f1, 3))
                
    return metrics
