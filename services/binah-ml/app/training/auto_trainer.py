"""
Auto-trainer - Automatically trains ML models with MLflow integration
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)
import xgboost as xgb
import mlflow
import mlflow.sklearn
import mlflow.xgboost

logger = logging.getLogger(__name__)


class AutoTrainer:
    """
    Automatic model trainer with MLflow integration
    Handles feature engineering, model training, evaluation, and registration
    """

    def __init__(
        self,
        tenant_id: str,
        model_type: str,
        entity_type: str,
        mlflow_tracking_uri: str
    ):
        """
        Initialize the auto-trainer

        Args:
            tenant_id: Tenant identifier
            model_type: Type of model to train
            entity_type: Entity type the model is for
            mlflow_tracking_uri: MLflow tracking server URI
        """
        self.tenant_id = tenant_id
        self.model_type = model_type
        self.entity_type = entity_type
        self.mlflow_tracking_uri = mlflow_tracking_uri

        # Configure MLflow
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)

        # Determine if this is a classification or regression task
        self.is_classification = model_type in [
            'churn_prediction',
            'maintenance_prediction'
        ]

        self.scaler: Optional[StandardScaler] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}

    async def train(self, training_data: List[Dict[str, Any]]) -> Dict:
        """
        Train a model on the provided data

        Args:
            training_data: List of training records

        Returns:
            Model information dictionary
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(training_data)

            logger.info(f"Training dataset shape: {df.shape}")

            # Feature engineering
            X, y, feature_names = self._prepare_features(df)

            logger.info(f"Feature matrix shape: {X.shape}, Target shape: {y.shape}")

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Start MLflow run
            experiment_name = f"{self.tenant_id}_{self.model_type}"
            mlflow.set_experiment(experiment_name)

            with mlflow.start_run(run_name=f"auto_train_{datetime.utcnow().isoformat()}"):
                # Log parameters
                mlflow.log_param("tenant_id", self.tenant_id)
                mlflow.log_param("model_type", self.model_type)
                mlflow.log_param("entity_type", self.entity_type)
                mlflow.log_param("training_samples", len(X_train))
                mlflow.log_param("test_samples", len(X_test))
                mlflow.log_param("features", feature_names)
                mlflow.log_param("is_classification", self.is_classification)

                # Train model
                model = self._train_model(X_train, y_train)

                # Evaluate model
                metrics = self._evaluate_model(model, X_test, y_test)

                # Log metrics
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(metric_name, metric_value)

                # Log model
                if isinstance(model, xgb.XGBModel):
                    mlflow.xgboost.log_model(model, "model")
                else:
                    mlflow.sklearn.log_model(model, "model")

                # Register model
                model_name = f"{self.tenant_id}_{self.model_type}"
                run_id = mlflow.active_run().info.run_id

                # Register in model registry
                model_uri = f"runs:/{run_id}/model"
                registered_model = mlflow.register_model(model_uri, model_name)

                logger.info(
                    f"Model registered: {model_name}, "
                    f"Version: {registered_model.version}"
                )

                return {
                    "model_name": model_name,
                    "version": registered_model.version,
                    "run_id": run_id,
                    "metrics": metrics,
                    "feature_count": len(feature_names),
                    "training_samples": len(X_train),
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            raise

    def _prepare_features(self, df: pd.DataFrame):
        """
        Prepare features for training

        Args:
            df: Input DataFrame

        Returns:
            Tuple of (X, y, feature_names)
        """
        # Drop non-feature columns
        drop_cols = ['id', 'created_at', 'updated_at', 'tenant_id', 'target']
        feature_cols = [col for col in df.columns if col not in drop_cols]

        # Extract target
        if 'target' not in df.columns:
            raise ValueError("No 'target' column found in training data")

        y = df['target'].values

        # Handle categorical features
        X_encoded = df[feature_cols].copy()

        for col in X_encoded.columns:
            if X_encoded[col].dtype == 'object':
                # Encode categorical features
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()

                # Handle missing values
                X_encoded[col] = X_encoded[col].fillna('MISSING')

                # Fit and transform
                X_encoded[col] = self.label_encoders[col].fit_transform(
                    X_encoded[col]
                )

        # Handle missing numeric values
        X_encoded = X_encoded.fillna(X_encoded.mean())

        # Scale features
        self.scaler = StandardScaler()
        X = self.scaler.fit_transform(X_encoded)

        feature_names = feature_cols

        return X, y, feature_names

    def _train_model(self, X_train: np.ndarray, y_train: np.ndarray):
        """
        Train the model based on model type

        Args:
            X_train: Training features
            y_train: Training target

        Returns:
            Trained model
        """
        if self.is_classification:
            # Classification model
            model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                use_label_encoder=False,
                eval_metric='logloss'
            )
        else:
            # Regression model
            model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )

        # Train
        model.fit(X_train, y_train)

        logger.info(f"Model trained successfully: {type(model).__name__}")

        return model

    def _evaluate_model(
        self,
        model,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate the trained model

        Args:
            model: Trained model
            X_test: Test features
            y_test: Test target

        Returns:
            Dictionary of metrics
        """
        metrics = {}

        # Make predictions
        y_pred = model.predict(X_test)

        if self.is_classification:
            # Classification metrics
            metrics['accuracy'] = accuracy_score(y_test, y_pred)
            metrics['precision'] = precision_score(
                y_test, y_pred, average='weighted', zero_division=0
            )
            metrics['recall'] = recall_score(
                y_test, y_pred, average='weighted', zero_division=0
            )
            metrics['f1_score'] = f1_score(
                y_test, y_pred, average='weighted', zero_division=0
            )

            # ROC AUC for binary classification
            if len(np.unique(y_test)) == 2:
                y_pred_proba = model.predict_proba(X_test)[:, 1]
                metrics['roc_auc'] = roc_auc_score(y_test, y_pred_proba)

        else:
            # Regression metrics
            metrics['rmse'] = np.sqrt(mean_squared_error(y_test, y_pred))
            metrics['mae'] = mean_absolute_error(y_test, y_pred)
            metrics['r2_score'] = r2_score(y_test, y_pred)

            # MAPE (Mean Absolute Percentage Error)
            # Avoid division by zero
            mask = y_test != 0
            if mask.any():
                mape = np.mean(
                    np.abs((y_test[mask] - y_pred[mask]) / y_test[mask])
                ) * 100
                metrics['mape'] = mape

        logger.info(f"Evaluation metrics: {metrics}")

        return metrics

    def _hyperparameter_tuning(self, X: np.ndarray, y: np.ndarray):
        """
        Perform basic hyperparameter tuning using cross-validation

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Best parameters
        """
        # This is a simplified version
        # In production, you'd use GridSearchCV or RandomizedSearchCV

        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 6, 9],
            'learning_rate': [0.01, 0.1, 0.3]
        }

        best_score = -np.inf
        best_params = {}

        for n_est in param_grid['n_estimators']:
            for max_d in param_grid['max_depth']:
                for lr in param_grid['learning_rate']:
                    if self.is_classification:
                        model = xgb.XGBClassifier(
                            n_estimators=n_est,
                            max_depth=max_d,
                            learning_rate=lr,
                            random_state=42,
                            use_label_encoder=False
                        )
                        scoring = 'accuracy'
                    else:
                        model = xgb.XGBRegressor(
                            n_estimators=n_est,
                            max_depth=max_d,
                            learning_rate=lr,
                            random_state=42
                        )
                        scoring = 'r2'

                    # Cross-validation
                    scores = cross_val_score(
                        model, X, y, cv=3, scoring=scoring
                    )
                    mean_score = scores.mean()

                    if mean_score > best_score:
                        best_score = mean_score
                        best_params = {
                            'n_estimators': n_est,
                            'max_depth': max_d,
                            'learning_rate': lr
                        }

        logger.info(f"Best hyperparameters: {best_params}, Score: {best_score}")

        return best_params
