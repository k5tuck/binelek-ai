"""Explainability Service for ML Model Interpretability

Provides SHAP and LIME explanations for ML model predictions
to meet HIPAA and FINRA/SEC compliance requirements.
"""

import shap
import numpy as np
from typing import Dict, List, Any, Optional
from lime.lime_tabular import LimeTabularExplainer
import logging
import pickle
import joblib
from pathlib import Path

logger = logging.getLogger(__name__)


class ExplainabilityService:
    """Service for generating ML model explanations using SHAP and LIME"""

    def __init__(self):
        """Initialize the explainability service"""
        self.explainers = {}  # Cache explainers per model to improve performance
        self.models_cache = {}  # Cache loaded models
        logger.info("ExplainabilityService initialized")

    async def explain_with_shap(
        self,
        model_id: str,
        prediction_id: str,
        X_test: np.ndarray,
        feature_names: List[str],
        model_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanation for a prediction

        Args:
            model_id: ID of the ML model
            prediction_id: ID of the prediction to explain
            X_test: Input features for the prediction (2D array, even for single prediction)
            feature_names: Names of features
            model_path: Optional path to model file

        Returns:
            Dictionary with SHAP values and visualization data
        """
        try:
            logger.info(f"Generating SHAP explanation for model={model_id}, prediction={prediction_id}")

            # Load model
            model = await self._load_model(model_id, model_path)

            # Create or retrieve cached explainer
            explainer_key = f"{model_id}_shap"
            if explainer_key not in self.explainers:
                logger.info(f"Creating new SHAP explainer for model {model_id}")
                self.explainers[explainer_key] = self._create_shap_explainer(model, X_test)

            explainer = self.explainers[explainer_key]

            # Calculate SHAP values
            shap_values = explainer.shap_values(X_test)

            # Get base value (expected value)
            base_value = explainer.expected_value

            # Handle multi-output models (classification with multiple classes)
            if isinstance(shap_values, list):
                # For multi-class classification, use values for predicted class
                prediction = model.predict(X_test)
                predicted_class = int(prediction[0]) if hasattr(prediction[0], '__int__') else 0
                shap_values_for_instance = shap_values[predicted_class][0]
                base_value_for_class = base_value[predicted_class] if isinstance(base_value, (list, np.ndarray)) else base_value
            else:
                # For regression or binary classification
                shap_values_for_instance = shap_values[0] if len(shap_values.shape) > 1 else shap_values
                base_value_for_class = base_value

            # Sort features by absolute SHAP value
            feature_importance = []
            for i in range(len(feature_names)):
                feature_importance.append({
                    "feature": feature_names[i],
                    "shap_value": float(shap_values_for_instance[i]),
                    "feature_value": float(X_test[0][i]),
                    "abs_importance": abs(float(shap_values_for_instance[i]))
                })

            # Sort by absolute importance
            feature_importance.sort(key=lambda x: x["abs_importance"], reverse=True)

            # Generate waterfall data
            waterfall_data = self.generate_waterfall_data(
                shap_values_for_instance,
                feature_names,
                float(base_value_for_class)
            )

            result = {
                "method": "shap",
                "prediction_id": prediction_id,
                "model_id": model_id,
                "base_value": float(base_value_for_class),
                "feature_importance": feature_importance,
                "waterfall_data": waterfall_data,
                "explanation_type": "global" if len(X_test) > 1 else "local"
            }

            logger.info(f"SHAP explanation generated successfully for prediction {prediction_id}")
            return result

        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {str(e)}")
            raise

    async def explain_with_lime(
        self,
        model_id: str,
        prediction_id: str,
        X_train: np.ndarray,
        X_test: np.ndarray,
        feature_names: List[str],
        class_names: Optional[List[str]] = None,
        model_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate LIME explanation for a prediction

        Args:
            model_id: ID of the ML model
            prediction_id: ID of the prediction to explain
            X_train: Training data (for background distribution)
            X_test: Test instance to explain
            feature_names: Names of features
            class_names: Names of classes (for classification)
            model_path: Optional path to model file

        Returns:
            Dictionary with LIME explanation
        """
        try:
            logger.info(f"Generating LIME explanation for model={model_id}, prediction={prediction_id}")

            # Load model
            model = await self._load_model(model_id, model_path)

            # Determine mode (classification or regression)
            mode = "classification" if class_names else "regression"

            # Create LIME explainer
            explainer = LimeTabularExplainer(
                X_train,
                feature_names=feature_names,
                class_names=class_names,
                mode=mode,
                discretize_continuous=True
            )

            # Explain instance
            if mode == "classification":
                explanation = explainer.explain_instance(
                    X_test[0],
                    model.predict_proba,
                    num_features=len(feature_names)
                )
            else:
                explanation = explainer.explain_instance(
                    X_test[0],
                    model.predict,
                    num_features=len(feature_names)
                )

            # Extract feature importance
            feature_importance_list = explanation.as_list()

            # Parse feature importance (LIME returns tuples of (feature_condition, weight))
            feature_importance = []
            for feature_desc, weight in feature_importance_list:
                # Extract feature name from description like "feature_name <= 5.0"
                feature_name = feature_desc.split()[0] if ' ' in feature_desc else feature_desc
                feature_importance.append({
                    "feature": feature_name,
                    "feature_description": feature_desc,
                    "weight": float(weight),
                    "abs_importance": abs(float(weight))
                })

            # Sort by absolute importance
            feature_importance.sort(key=lambda x: x["abs_importance"], reverse=True)

            result = {
                "method": "lime",
                "prediction_id": prediction_id,
                "model_id": model_id,
                "intercept": float(explanation.intercept[0]) if mode == "regression" else None,
                "feature_importance": feature_importance,
                "prediction_score": float(explanation.score) if hasattr(explanation, 'score') else None,
                "local_prediction": float(explanation.local_pred[0]) if hasattr(explanation, 'local_pred') else None
            }

            logger.info(f"LIME explanation generated successfully for prediction {prediction_id}")
            return result

        except Exception as e:
            logger.error(f"Error generating LIME explanation: {str(e)}")
            raise

    async def compare_explanations(
        self,
        model_id: str,
        prediction_id: str,
        X_train: np.ndarray,
        X_test: np.ndarray,
        feature_names: List[str],
        class_names: Optional[List[str]] = None,
        model_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare SHAP and LIME explanations side-by-side

        Args:
            model_id: ID of the ML model
            prediction_id: ID of the prediction to explain
            X_train: Training data (for LIME)
            X_test: Test instance to explain
            feature_names: Names of features
            class_names: Names of classes (for classification)
            model_path: Optional path to model file

        Returns:
            Dictionary with both explanations and comparison metrics
        """
        try:
            logger.info(f"Comparing SHAP and LIME explanations for prediction {prediction_id}")

            # Generate both explanations
            shap_result = await self.explain_with_shap(
                model_id, prediction_id, X_test, feature_names, model_path
            )

            lime_result = await self.explain_with_lime(
                model_id, prediction_id, X_train, X_test, feature_names, class_names, model_path
            )

            # Calculate agreement score
            shap_ranking = self._rank_features(shap_result["feature_importance"], "shap")
            lime_ranking = self._rank_features(lime_result["feature_importance"], "lime")
            agreement_score = self._calculate_rank_correlation(shap_ranking, lime_ranking)

            result = {
                "shap": shap_result,
                "lime": lime_result,
                "agreement_score": agreement_score,
                "top_features_match": self._compare_top_features(shap_ranking, lime_ranking, top_n=5),
                "recommendation": self._get_recommendation(agreement_score)
            }

            logger.info(f"Comparison complete. Agreement score: {agreement_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"Error comparing explanations: {str(e)}")
            raise

    def generate_waterfall_data(
        self,
        shap_values: np.ndarray,
        feature_names: List[str],
        base_value: float
    ) -> Dict[str, Any]:
        """
        Generate data for SHAP waterfall plot
        Shows how each feature contributes to pushing prediction from base value

        Args:
            shap_values: SHAP values for features
            feature_names: Names of features
            base_value: Base value (expected value)

        Returns:
            Dictionary with waterfall plot data
        """
        # Sort features by absolute SHAP value
        sorted_indices = np.argsort(np.abs(shap_values))[::-1]

        cumulative = base_value
        features_data = []

        for i in sorted_indices:
            shap_val = float(shap_values[i])
            features_data.append({
                "name": feature_names[i],
                "shap_value": shap_val,
                "cumulative": float(cumulative + shap_val)
            })
            cumulative += shap_val

        return {
            "plot_type": "waterfall",
            "base_value": float(base_value),
            "features": features_data,
            "final_prediction": float(cumulative)
        }

    def _create_shap_explainer(self, model, X_sample: np.ndarray):
        """Create appropriate SHAP explainer based on model type"""
        model_type = type(model).__name__

        logger.info(f"Creating SHAP explainer for model type: {model_type}")

        # Tree-based models use TreeExplainer (faster and exact)
        if model_type in ["XGBClassifier", "XGBRegressor",
                          "RandomForestClassifier", "RandomForestRegressor",
                          "GradientBoostingClassifier", "GradientBoostingRegressor",
                          "LGBMClassifier", "LGBMRegressor"]:
            return shap.TreeExplainer(model)

        # Linear models use LinearExplainer
        elif model_type in ["LogisticRegression", "LinearRegression", "Ridge", "Lasso"]:
            return shap.LinearExplainer(model, X_sample)

        # For other models, use KernelExplainer (slower but model-agnostic)
        else:
            logger.warning(f"Using KernelExplainer for {model_type} - may be slower")
            # Use a sample of the data as background for KernelExplainer
            background = shap.sample(X_sample, min(100, len(X_sample)))
            return shap.KernelExplainer(model.predict, background)

    async def _load_model(self, model_id: str, model_path: Optional[str] = None):
        """Load model from cache or file"""
        if model_id in self.models_cache:
            logger.debug(f"Using cached model {model_id}")
            return self.models_cache[model_id]

        if model_path is None:
            # In production, this would load from MLflow or model registry
            raise ValueError(f"Model path not provided for model {model_id}")

        # Load model from file
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            # Try joblib first (sklearn models)
            model = joblib.load(model_path)
            logger.info(f"Loaded model {model_id} from {model_path}")
        except Exception:
            # Try pickle as fallback
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"Loaded model {model_id} from {model_path} (pickle)")

        # Cache the model
        self.models_cache[model_id] = model
        return model

    def _rank_features(self, feature_importance: List[Dict], method: str) -> List[str]:
        """Rank features by absolute importance"""
        if method == "shap":
            sorted_features = sorted(
                feature_importance,
                key=lambda x: abs(x.get("shap_value", 0)),
                reverse=True
            )
        else:  # lime
            sorted_features = sorted(
                feature_importance,
                key=lambda x: abs(x.get("weight", 0)),
                reverse=True
            )

        return [f["feature"] for f in sorted_features]

    def _calculate_rank_correlation(self, ranking1: List[str], ranking2: List[str]) -> float:
        """
        Calculate Spearman's rank correlation coefficient
        Measures agreement between two rankings
        """
        # Find common features
        common_features = set(ranking1) & set(ranking2)
        if not common_features:
            return 0.0

        # Get ranks for common features
        ranks1 = {feat: i for i, feat in enumerate(ranking1) if feat in common_features}
        ranks2 = {feat: i for i, feat in enumerate(ranking2) if feat in common_features}

        # Calculate Spearman's correlation
        n = len(common_features)
        d_squared_sum = sum((ranks1[feat] - ranks2[feat]) ** 2 for feat in common_features)

        if n <= 1:
            return 1.0

        correlation = 1 - (6 * d_squared_sum) / (n * (n**2 - 1))
        return max(0.0, min(1.0, correlation))  # Clamp to [0, 1]

    def _compare_top_features(self, ranking1: List[str], ranking2: List[str], top_n: int = 5) -> Dict[str, Any]:
        """Compare top N features between two rankings"""
        top1 = set(ranking1[:top_n])
        top2 = set(ranking2[:top_n])

        overlap = top1 & top2

        return {
            "top_n": top_n,
            "overlap_count": len(overlap),
            "overlap_percentage": (len(overlap) / top_n) * 100,
            "common_features": list(overlap),
            "shap_only": list(top1 - top2),
            "lime_only": list(top2 - top1)
        }

    def _get_recommendation(self, agreement_score: float) -> str:
        """Get recommendation based on agreement score"""
        if agreement_score >= 0.8:
            return "High agreement between SHAP and LIME. Both methods confirm the same feature importance."
        elif agreement_score >= 0.6:
            return "Moderate agreement between SHAP and LIME. Consider both explanations."
        else:
            return "Low agreement between SHAP and LIME. Use SHAP for tree models, LIME for complex models. Consider model complexity."

    def clear_cache(self):
        """Clear explainer and model caches"""
        self.explainers.clear()
        self.models_cache.clear()
        logger.info("Cleared explainability service caches")
