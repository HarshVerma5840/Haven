import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

class BaselineModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)

    def prepare_data(self, df: pd.DataFrame):
        """
        Prepares the dataset.
        Enforces rules: DO NOT use employee_hash or week_start_date as features.
        """
        # Drop identity and date columns
        features = df.drop(columns=["employee_hash", "week_start_date", "burnout_score", "burnout_risk", "label_source", "data_completeness"])
        
        # One-hot encode categoricals
        features = pd.get_dummies(features, columns=["department", "designation", "employment_type"], dummy_na=True)
        
        # Handle missing numeric data explicitly without silently converting to zero
        # Example: Fill missing review response hours with the mean/median, or flag them.
        features.fillna(features.median(numeric_only=True), inplace=True)
        
        target = df["burnout_score"]
        return features, target

    def train(self, df: pd.DataFrame):
        X, y = self.prepare_data(df)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model.fit(X_train, y_train)
        predictions = self.model.predict(X_test)
        
        mse = mean_squared_error(y_test, predictions)
        return {"mse": mse, "score": self.model.score(X_test, y_test)}
