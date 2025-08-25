#!/usr/bin/env python3
"""
Advanced Confidence Scoring and Decision-Making System for AutoDMCA
Implements sophisticated algorithms for automated DMCA decision making
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

# Machine Learning
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

# Statistics and Analysis
from scipy import stats
from scipy.optimize import minimize_scalar
import pandas as pd

logger = logging.getLogger(__name__)

class DecisionClass(Enum):
    """Decision classes for automated DMCA processing"""
    AUTO_APPROVE = "auto_approve"      # >90% confidence - send takedown
    MANUAL_REVIEW = "manual_review"    # 60-90% confidence - human review
    AUTO_REJECT = "auto_reject"        # <60% confidence - reject/ignore

class RiskLevel(Enum):
    """Risk levels for false positive assessment"""
    VERY_LOW = "very_low"      # <1% false positive rate
    LOW = "low"                # 1-5% false positive rate
    MEDIUM = "medium"          # 5-15% false positive rate
    HIGH = "high"              # 15-30% false positive rate
    VERY_HIGH = "very_high"    # >30% false positive rate

@dataclass
class ConfidenceFeatures:
    """Feature set for confidence scoring"""
    
    # Content similarity features
    perceptual_hash_score: float = 0.0
    deep_features_score: float = 0.0
    average_hash_score: float = 0.0
    difference_hash_score: float = 0.0
    wavelet_hash_score: float = 0.0
    color_hash_score: float = 0.0
    text_similarity_score: float = 0.0
    
    # Content metadata features
    file_size_ratio: float = 0.0
    resolution_similarity: float = 0.0
    duration_similarity: float = 0.0
    
    # Platform features
    platform_reliability: float = 0.8  # Platform's historical accuracy
    content_age_days: int = 0
    source_credibility: float = 0.5
    
    # Historical features
    creator_history_score: float = 0.5
    platform_takedown_success_rate: float = 0.75
    similar_content_matches: int = 0
    
    # Contextual features
    content_popularity: float = 0.0
    reporting_user_reputation: float = 0.5
    automated_scan_confidence: float = 0.0
    
    # Technical features
    processing_quality: float = 1.0
    feature_extraction_confidence: float = 1.0
    model_uncertainty: float = 0.0
    
    def to_feature_vector(self) -> np.ndarray:
        """Convert to numpy array for ML models"""
        return np.array([
            self.perceptual_hash_score,
            self.deep_features_score,
            self.average_hash_score,
            self.difference_hash_score,
            self.wavelet_hash_score,
            self.color_hash_score,
            self.text_similarity_score,
            self.file_size_ratio,
            self.resolution_similarity,
            self.duration_similarity,
            self.platform_reliability,
            self.content_age_days / 365.0,  # Normalize
            self.source_credibility,
            self.creator_history_score,
            self.platform_takedown_success_rate,
            min(self.similar_content_matches / 10.0, 1.0),  # Normalize
            self.content_popularity,
            self.reporting_user_reputation,
            self.automated_scan_confidence,
            self.processing_quality,
            self.feature_extraction_confidence,
            self.model_uncertainty
        ])

@dataclass
class ConfidenceScore:
    """Comprehensive confidence scoring result"""
    
    overall_confidence: float
    risk_level: RiskLevel
    decision_class: DecisionClass
    
    # Component scores
    similarity_confidence: float
    contextual_confidence: float
    historical_confidence: float
    technical_confidence: float
    
    # Decision details
    reasoning: str
    key_factors: List[str]
    uncertainty_factors: List[str]
    
    # Statistical measures
    prediction_interval: Tuple[float, float]  # 95% confidence interval
    model_agreement: float  # Agreement across ensemble models
    calibration_score: float  # How well-calibrated the prediction is
    
    # Risk assessment
    false_positive_probability: float
    expected_cost: float  # Expected cost of wrong decision
    
    # Metadata
    feature_importance: Dict[str, float] = field(default_factory=dict)
    model_version: str = "1.0"
    scored_at: datetime = field(default_factory=datetime.utcnow)

class ConfidenceScoringService:
    """Advanced confidence scoring service with ML ensemble"""
    
    def __init__(self, model_path: Optional[str] = None):
        
        # Ensemble of ML models
        self.models = {
            "random_forest": RandomForestClassifier(
                n_estimators=100, 
                max_depth=10, 
                random_state=42,
                class_weight='balanced'
            ),
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            "logistic_regression": LogisticRegression(
                class_weight='balanced',
                random_state=42,
                max_iter=1000
            )
        }
        
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = Path(model_path) if model_path else Path("/tmp/autodmca_models")
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # Decision thresholds (will be optimized during training)
        self.thresholds = {
            "auto_approve": 0.90,
            "manual_review_upper": 0.90,
            "manual_review_lower": 0.60,
            "auto_reject": 0.60
        }
        
        # Risk assessment parameters
        self.risk_params = {
            "false_positive_costs": {
                "auto_approve": 100.0,  # Cost of wrongly approving
                "manual_review": 5.0,   # Cost of manual review
                "auto_reject": 1.0      # Cost of wrongly rejecting
            },
            "processing_costs": {
                "auto_approve": 0.1,
                "manual_review": 10.0,
                "auto_reject": 0.1
            }
        }
        
        # Feature weights for interpretability
        self.feature_names = [
            "perceptual_hash_score", "deep_features_score", "average_hash_score",
            "difference_hash_score", "wavelet_hash_score", "color_hash_score",
            "text_similarity_score", "file_size_ratio", "resolution_similarity",
            "duration_similarity", "platform_reliability", "content_age_normalized",
            "source_credibility", "creator_history_score", "platform_success_rate",
            "similar_content_matches", "content_popularity", "reporting_user_reputation",
            "automated_scan_confidence", "processing_quality", 
            "feature_extraction_confidence", "model_uncertainty"
        ]
        
        # Performance tracking
        self.performance_metrics = {
            "predictions_made": 0,
            "auto_approved": 0,
            "manual_reviews": 0,
            "auto_rejected": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0
        }
        
        # Try to load existing models
        self._load_models()
        
        logger.info("Confidence Scoring Service initialized")
    
    async def score_confidence(self, features: ConfidenceFeatures) -> ConfidenceScore:
        """Generate comprehensive confidence score"""
        
        try:
            # Convert features to vector
            feature_vector = features.to_feature_vector().reshape(1, -1)
            
            if self.is_trained:
                # Use trained ensemble
                confidence_score = await self._ensemble_predict(feature_vector)
            else:
                # Use rule-based scoring as fallback
                confidence_score = await self._rule_based_scoring(features)
            
            # Calculate component scores
            similarity_confidence = self._calculate_similarity_confidence(features)
            contextual_confidence = self._calculate_contextual_confidence(features)
            historical_confidence = self._calculate_historical_confidence(features)
            technical_confidence = self._calculate_technical_confidence(features)
            
            # Determine decision class and risk level
            decision_class = self._classify_decision(confidence_score)
            risk_level = self._assess_risk(confidence_score, features)
            
            # Generate reasoning and key factors
            reasoning, key_factors, uncertainty_factors = self._generate_reasoning(
                features, confidence_score, decision_class
            )
            
            # Statistical measures
            prediction_interval = self._calculate_prediction_interval(feature_vector, confidence_score)
            model_agreement = self._calculate_model_agreement(feature_vector)
            calibration_score = self._calculate_calibration(confidence_score)
            
            # Risk assessment
            false_positive_prob = self._estimate_false_positive_probability(
                confidence_score, features
            )
            expected_cost = self._calculate_expected_cost(decision_class, false_positive_prob)
            
            # Feature importance
            feature_importance = self._get_feature_importance(feature_vector)
            
            result = ConfidenceScore(
                overall_confidence=confidence_score,
                risk_level=risk_level,
                decision_class=decision_class,
                similarity_confidence=similarity_confidence,
                contextual_confidence=contextual_confidence,
                historical_confidence=historical_confidence,
                technical_confidence=technical_confidence,
                reasoning=reasoning,
                key_factors=key_factors,
                uncertainty_factors=uncertainty_factors,
                prediction_interval=prediction_interval,
                model_agreement=model_agreement,
                calibration_score=calibration_score,
                false_positive_probability=false_positive_prob,
                expected_cost=expected_cost,
                feature_importance=feature_importance
            )
            
            # Update metrics
            self.performance_metrics["predictions_made"] += 1
            if decision_class == DecisionClass.AUTO_APPROVE:
                self.performance_metrics["auto_approved"] += 1
            elif decision_class == DecisionClass.MANUAL_REVIEW:
                self.performance_metrics["manual_reviews"] += 1
            else:
                self.performance_metrics["auto_rejected"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Confidence scoring failed: {str(e)}")
            # Return conservative fallback score
            return self._create_fallback_score()
    
    async def _ensemble_predict(self, feature_vector: np.ndarray) -> float:
        """Predict using ensemble of trained models"""
        
        # Scale features
        scaled_features = self.scaler.transform(feature_vector)
        
        # Get predictions from all models
        predictions = []
        weights = {"random_forest": 0.4, "gradient_boosting": 0.4, "logistic_regression": 0.2}
        
        for name, model in self.models.items():
            if hasattr(model, 'predict_proba'):
                # Get positive class probability
                prob = model.predict_proba(scaled_features)[0][1]
                predictions.append(prob * weights[name])
            else:
                # Fallback for models without predict_proba
                pred = model.predict(scaled_features)[0]
                predictions.append(pred * weights[name])
        
        # Weighted ensemble prediction
        ensemble_score = sum(predictions)
        
        # Ensure score is in [0, 1] range
        return max(0.0, min(1.0, ensemble_score))
    
    async def _rule_based_scoring(self, features: ConfidenceFeatures) -> float:
        """Rule-based confidence scoring when models aren't trained"""
        
        # Primary similarity score (weighted average)
        similarity_weights = {
            "perceptual_hash": 0.25,
            "deep_features": 0.30,
            "average_hash": 0.15,
            "difference_hash": 0.10,
            "wavelet_hash": 0.10,
            "color_hash": 0.05,
            "text_similarity": 0.05
        }
        
        primary_score = (
            features.perceptual_hash_score * similarity_weights["perceptual_hash"] +
            features.deep_features_score * similarity_weights["deep_features"] +
            features.average_hash_score * similarity_weights["average_hash"] +
            features.difference_hash_score * similarity_weights["difference_hash"] +
            features.wavelet_hash_score * similarity_weights["wavelet_hash"] +
            features.color_hash_score * similarity_weights["color_hash"] +
            features.text_similarity_score * similarity_weights["text_similarity"]
        )
        
        # Contextual adjustments
        contextual_multiplier = (
            features.platform_reliability * 0.3 +
            features.source_credibility * 0.2 +
            features.creator_history_score * 0.2 +
            features.reporting_user_reputation * 0.1 +
            features.processing_quality * 0.1 +
            features.feature_extraction_confidence * 0.1
        )
        
        # Age penalty (older content less likely to be fresh infringement)
        age_penalty = max(0.8, 1.0 - (features.content_age_days / 365.0) * 0.2)
        
        # Technical confidence boost
        technical_boost = min(1.1, 1.0 + features.automated_scan_confidence * 0.1)
        
        # Final score calculation
        final_score = primary_score * contextual_multiplier * age_penalty * technical_boost
        
        # Apply uncertainty penalty
        uncertainty_penalty = max(0.9, 1.0 - features.model_uncertainty)
        final_score *= uncertainty_penalty
        
        return max(0.0, min(1.0, final_score))
    
    def _calculate_similarity_confidence(self, features: ConfidenceFeatures) -> float:
        """Calculate confidence based purely on similarity metrics"""
        
        similarity_scores = [
            features.perceptual_hash_score,
            features.deep_features_score,
            features.average_hash_score,
            features.difference_hash_score,
            features.wavelet_hash_score,
            features.color_hash_score,
            features.text_similarity_score
        ]
        
        # Use weighted average with higher weight for deep features
        weights = [0.25, 0.30, 0.15, 0.10, 0.10, 0.05, 0.05]
        
        return sum(score * weight for score, weight in zip(similarity_scores, weights))
    
    def _calculate_contextual_confidence(self, features: ConfidenceFeatures) -> float:
        """Calculate confidence based on contextual factors"""
        
        contextual_factors = [
            features.platform_reliability,
            features.source_credibility,
            features.content_popularity,
            features.reporting_user_reputation,
            1.0 - min(features.content_age_days / 365.0, 1.0)  # Recency bonus
        ]
        
        return np.mean(contextual_factors)
    
    def _calculate_historical_confidence(self, features: ConfidenceFeatures) -> float:
        """Calculate confidence based on historical performance"""
        
        historical_factors = [
            features.creator_history_score,
            features.platform_takedown_success_rate,
            min(features.similar_content_matches / 5.0, 1.0)  # Normalize similar matches
        ]
        
        return np.mean(historical_factors)
    
    def _calculate_technical_confidence(self, features: ConfidenceFeatures) -> float:
        """Calculate confidence based on technical quality"""
        
        technical_factors = [
            features.processing_quality,
            features.feature_extraction_confidence,
            1.0 - features.model_uncertainty,
            features.automated_scan_confidence
        ]
        
        return np.mean(technical_factors)
    
    def _classify_decision(self, confidence_score: float) -> DecisionClass:
        """Classify decision based on confidence score and thresholds"""
        
        if confidence_score >= self.thresholds["auto_approve"]:
            return DecisionClass.AUTO_APPROVE
        elif confidence_score >= self.thresholds["auto_reject"]:
            return DecisionClass.MANUAL_REVIEW
        else:
            return DecisionClass.AUTO_REJECT
    
    def _assess_risk(self, confidence_score: float, features: ConfidenceFeatures) -> RiskLevel:
        """Assess risk level for the decision"""
        
        # Base risk from confidence score
        if confidence_score >= 0.95:
            base_risk = RiskLevel.VERY_LOW
        elif confidence_score >= 0.85:
            base_risk = RiskLevel.LOW
        elif confidence_score >= 0.70:
            base_risk = RiskLevel.MEDIUM
        elif confidence_score >= 0.50:
            base_risk = RiskLevel.HIGH
        else:
            base_risk = RiskLevel.VERY_HIGH
        
        # Risk adjustments based on features
        risk_factors = [
            features.model_uncertainty,
            1.0 - features.processing_quality,
            1.0 - features.feature_extraction_confidence,
            1.0 - features.source_credibility
        ]
        
        avg_risk_factor = np.mean(risk_factors)
        
        # Adjust risk level based on risk factors
        if avg_risk_factor > 0.3:
            # Increase risk level
            risk_levels = list(RiskLevel)
            current_index = risk_levels.index(base_risk)
            if current_index < len(risk_levels) - 1:
                return risk_levels[current_index + 1]
        elif avg_risk_factor < 0.1 and base_risk != RiskLevel.VERY_LOW:
            # Decrease risk level
            risk_levels = list(RiskLevel)
            current_index = risk_levels.index(base_risk)
            if current_index > 0:
                return risk_levels[current_index - 1]
        
        return base_risk
    
    def _generate_reasoning(
        self, 
        features: ConfidenceFeatures, 
        confidence_score: float,
        decision_class: DecisionClass
    ) -> Tuple[str, List[str], List[str]]:
        """Generate human-readable reasoning for the decision"""
        
        reasoning_parts = []
        key_factors = []
        uncertainty_factors = []
        
        # Primary decision reasoning
        if decision_class == DecisionClass.AUTO_APPROVE:
            reasoning_parts.append(f"High confidence ({confidence_score:.1%}) indicates strong evidence of copyright infringement.")
        elif decision_class == DecisionClass.MANUAL_REVIEW:
            reasoning_parts.append(f"Moderate confidence ({confidence_score:.1%}) requires human review for accurate assessment.")
        else:
            reasoning_parts.append(f"Low confidence ({confidence_score:.1%}) suggests insufficient evidence of infringement.")
        
        # Key supporting factors
        if features.perceptual_hash_score > 0.8:
            key_factors.append(f"Strong perceptual similarity ({features.perceptual_hash_score:.1%})")
        if features.deep_features_score > 0.8:
            key_factors.append(f"High semantic similarity ({features.deep_features_score:.1%})")
        if features.platform_reliability > 0.8:
            key_factors.append(f"Reliable platform source ({features.platform_reliability:.1%})")
        if features.creator_history_score > 0.8:
            key_factors.append("Strong creator history")
        
        # Uncertainty factors
        if features.model_uncertainty > 0.2:
            uncertainty_factors.append(f"Model uncertainty ({features.model_uncertainty:.1%})")
        if features.processing_quality < 0.8:
            uncertainty_factors.append(f"Processing quality concerns ({features.processing_quality:.1%})")
        if features.content_age_days > 365:
            uncertainty_factors.append(f"Old content (>{features.content_age_days} days)")
        if features.source_credibility < 0.6:
            uncertainty_factors.append(f"Low source credibility ({features.source_credibility:.1%})")
        
        # Combine reasoning
        reasoning = " ".join(reasoning_parts)
        if key_factors:
            reasoning += f" Key factors: {', '.join(key_factors[:3])}."
        if uncertainty_factors:
            reasoning += f" Uncertainty factors: {', '.join(uncertainty_factors[:2])}."
        
        return reasoning, key_factors, uncertainty_factors
    
    def _calculate_prediction_interval(self, feature_vector: np.ndarray, point_estimate: float) -> Tuple[float, float]:
        """Calculate 95% prediction interval"""
        
        if not self.is_trained:
            # Conservative interval for untrained models
            margin = 0.15
            return (max(0.0, point_estimate - margin), min(1.0, point_estimate + margin))
        
        try:
            # Use ensemble variance for interval estimation
            predictions = []
            scaled_features = self.scaler.transform(feature_vector)
            
            for model in self.models.values():
                if hasattr(model, 'predict_proba'):
                    pred = model.predict_proba(scaled_features)[0][1]
                else:
                    pred = model.predict(scaled_features)[0]
                predictions.append(pred)
            
            std_dev = np.std(predictions)
            margin = 1.96 * std_dev  # 95% confidence interval
            
            lower = max(0.0, point_estimate - margin)
            upper = min(1.0, point_estimate + margin)
            
            return (lower, upper)
            
        except Exception as e:
            logger.warning(f"Prediction interval calculation failed: {str(e)}")
            margin = 0.1
            return (max(0.0, point_estimate - margin), min(1.0, point_estimate + margin))
    
    def _calculate_model_agreement(self, feature_vector: np.ndarray) -> float:
        """Calculate agreement between ensemble models"""
        
        if not self.is_trained:
            return 0.7  # Default agreement for untrained models
        
        try:
            predictions = []
            scaled_features = self.scaler.transform(feature_vector)
            
            for model in self.models.values():
                if hasattr(model, 'predict_proba'):
                    pred = model.predict_proba(scaled_features)[0][1]
                else:
                    pred = model.predict(scaled_features)[0]
                predictions.append(pred)
            
            # Calculate coefficient of variation (inverse of agreement)
            mean_pred = np.mean(predictions)
            if mean_pred == 0:
                return 1.0
            
            cv = np.std(predictions) / mean_pred
            agreement = 1.0 / (1.0 + cv)  # Convert to agreement score
            
            return max(0.0, min(1.0, agreement))
            
        except Exception as e:
            logger.warning(f"Model agreement calculation failed: {str(e)}")
            return 0.7
    
    def _calculate_calibration(self, confidence_score: float) -> float:
        """Calculate calibration score (how well-calibrated the prediction is)"""
        
        # For now, use a heuristic based on confidence score
        # In production, this would be based on historical performance
        
        if confidence_score > 0.9 or confidence_score < 0.1:
            return 0.9  # High confidence predictions are usually well-calibrated
        elif 0.4 <= confidence_score <= 0.6:
            return 0.6  # Mid-range predictions are harder to calibrate
        else:
            return 0.8  # Other ranges have moderate calibration
    
    def _estimate_false_positive_probability(self, confidence_score: float, features: ConfidenceFeatures) -> float:
        """Estimate probability of false positive"""
        
        # Base false positive rate by confidence level
        if confidence_score >= 0.95:
            base_fp_rate = 0.01
        elif confidence_score >= 0.90:
            base_fp_rate = 0.05
        elif confidence_score >= 0.80:
            base_fp_rate = 0.15
        elif confidence_score >= 0.70:
            base_fp_rate = 0.25
        else:
            base_fp_rate = 0.40
        
        # Adjust based on uncertainty factors
        uncertainty_adjustment = (
            features.model_uncertainty * 0.3 +
            (1.0 - features.processing_quality) * 0.2 +
            (1.0 - features.source_credibility) * 0.2
        )
        
        adjusted_fp_rate = base_fp_rate + uncertainty_adjustment
        return max(0.01, min(0.95, adjusted_fp_rate))
    
    def _calculate_expected_cost(self, decision_class: DecisionClass, false_positive_prob: float) -> float:
        """Calculate expected cost of the decision"""
        
        if decision_class == DecisionClass.AUTO_APPROVE:
            processing_cost = self.risk_params["processing_costs"]["auto_approve"]
            error_cost = self.risk_params["false_positive_costs"]["auto_approve"]
            return processing_cost + (false_positive_prob * error_cost)
        
        elif decision_class == DecisionClass.MANUAL_REVIEW:
            return self.risk_params["processing_costs"]["manual_review"]
        
        else:  # AUTO_REJECT
            processing_cost = self.risk_params["processing_costs"]["auto_reject"]
            # False negative cost (missing real infringement)
            false_negative_prob = 1.0 - false_positive_prob
            error_cost = self.risk_params["false_positive_costs"]["auto_reject"]
            return processing_cost + (false_negative_prob * error_cost)
    
    def _get_feature_importance(self, feature_vector: np.ndarray) -> Dict[str, float]:
        """Get feature importance scores"""
        
        if not self.is_trained:
            # Default importance weights
            return dict(zip(self.feature_names, [1/len(self.feature_names)] * len(self.feature_names)))
        
        try:
            # Use Random Forest feature importance
            if hasattr(self.models["random_forest"], 'feature_importances_'):
                importances = self.models["random_forest"].feature_importances_
                return dict(zip(self.feature_names, importances))
            else:
                return dict(zip(self.feature_names, [1/len(self.feature_names)] * len(self.feature_names)))
                
        except Exception as e:
            logger.warning(f"Feature importance calculation failed: {str(e)}")
            return dict(zip(self.feature_names, [1/len(self.feature_names)] * len(self.feature_names)))
    
    def _create_fallback_score(self) -> ConfidenceScore:
        """Create conservative fallback score on errors"""
        
        return ConfidenceScore(
            overall_confidence=0.5,
            risk_level=RiskLevel.HIGH,
            decision_class=DecisionClass.MANUAL_REVIEW,
            similarity_confidence=0.5,
            contextual_confidence=0.5,
            historical_confidence=0.5,
            technical_confidence=0.5,
            reasoning="Error in confidence calculation - defaulting to manual review",
            key_factors=["System error occurred"],
            uncertainty_factors=["Calculation failure"],
            prediction_interval=(0.3, 0.7),
            model_agreement=0.0,
            calibration_score=0.0,
            false_positive_probability=0.5,
            expected_cost=10.0
        )
    
    async def train_models(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train ensemble models with historical data"""
        
        try:
            logger.info(f"Training models with {len(training_data)} samples")
            
            # Prepare training data
            X, y = self._prepare_training_data(training_data)
            
            if len(X) < 50:
                logger.warning("Insufficient training data - models may not be reliable")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train each model
            training_results = {}
            
            for name, model in self.models.items():
                logger.info(f"Training {name}...")
                
                model.fit(X_train_scaled, y_train)
                
                # Evaluate
                train_score = model.score(X_train_scaled, y_train)
                test_score = model.score(X_test_scaled, y_test)
                
                training_results[name] = {
                    "train_score": train_score,
                    "test_score": test_score
                }
                
                logger.info(f"{name} - Train: {train_score:.3f}, Test: {test_score:.3f}")
            
            # Optimize thresholds
            await self._optimize_thresholds(X_test_scaled, y_test)
            
            # Save models
            self._save_models()
            
            self.is_trained = True
            
            return {
                "status": "success",
                "models_trained": len(self.models),
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "results": training_results,
                "thresholds": self.thresholds
            }
            
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _prepare_training_data(self, training_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML models"""
        
        X = []
        y = []
        
        for sample in training_data:
            try:
                # Extract features
                features = ConfidenceFeatures(**sample.get("features", {}))
                feature_vector = features.to_feature_vector()
                
                # Extract label (true decision: 1 for infringement, 0 for not)
                label = 1 if sample.get("is_infringement", False) else 0
                
                X.append(feature_vector)
                y.append(label)
                
            except Exception as e:
                logger.warning(f"Skipping invalid training sample: {str(e)}")
                continue
        
        return np.array(X), np.array(y)
    
    async def _optimize_thresholds(self, X_test: np.ndarray, y_test: np.ndarray):
        """Optimize decision thresholds based on cost function"""
        
        def cost_function(threshold):
            # Predict probabilities with ensemble
            ensemble_probs = []
            for model in self.models.values():
                if hasattr(model, 'predict_proba'):
                    probs = model.predict_proba(X_test)[:, 1]
                else:
                    probs = model.predict(X_test)
                ensemble_probs.append(probs)
            
            avg_probs = np.mean(ensemble_probs, axis=0)
            
            # Apply threshold
            predictions = (avg_probs >= threshold).astype(int)
            
            # Calculate cost
            false_positives = np.sum((predictions == 1) & (y_test == 0))
            false_negatives = np.sum((predictions == 0) & (y_test == 1))
            
            fp_cost = false_positives * self.risk_params["false_positive_costs"]["auto_approve"]
            fn_cost = false_negatives * self.risk_params["false_positive_costs"]["auto_reject"]
            
            return fp_cost + fn_cost
        
        # Optimize auto-approve threshold
        result = minimize_scalar(cost_function, bounds=(0.8, 0.99), method='bounded')
        if result.success:
            self.thresholds["auto_approve"] = result.x
            logger.info(f"Optimized auto-approve threshold: {result.x:.3f}")
        
        # Set other thresholds relative to auto-approve
        self.thresholds["manual_review_upper"] = self.thresholds["auto_approve"]
        self.thresholds["manual_review_lower"] = max(0.5, self.thresholds["auto_approve"] - 0.3)
        self.thresholds["auto_reject"] = self.thresholds["manual_review_lower"]
    
    def _save_models(self):
        """Save trained models to disk"""
        
        try:
            # Save models
            for name, model in self.models.items():
                model_file = self.model_path / f"{name}_model.joblib"
                joblib.dump(model, model_file)
            
            # Save scaler
            scaler_file = self.model_path / "scaler.joblib"
            joblib.dump(self.scaler, scaler_file)
            
            # Save thresholds and metadata
            metadata = {
                "thresholds": self.thresholds,
                "feature_names": self.feature_names,
                "model_version": "1.0",
                "trained_at": datetime.utcnow().isoformat()
            }
            
            metadata_file = self.model_path / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Models saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")
    
    def _load_models(self):
        """Load previously trained models"""
        
        try:
            metadata_file = self.model_path / "metadata.json"
            if not metadata_file.exists():
                return
            
            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            self.thresholds = metadata.get("thresholds", self.thresholds)
            
            # Load models
            for name in self.models.keys():
                model_file = self.model_path / f"{name}_model.joblib"
                if model_file.exists():
                    self.models[name] = joblib.load(model_file)
            
            # Load scaler
            scaler_file = self.model_path / "scaler.joblib"
            if scaler_file.exists():
                self.scaler = joblib.load(scaler_file)
            
            self.is_trained = True
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load models: {str(e)}")
            self.is_trained = False
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        
        total = self.performance_metrics["predictions_made"]
        if total == 0:
            return self.performance_metrics
        
        # Calculate rates
        auto_approve_rate = self.performance_metrics["auto_approved"] / total
        manual_review_rate = self.performance_metrics["manual_reviews"] / total
        auto_reject_rate = self.performance_metrics["auto_rejected"] / total
        
        return {
            **self.performance_metrics,
            "auto_approve_rate": auto_approve_rate,
            "manual_review_rate": manual_review_rate,
            "auto_reject_rate": auto_reject_rate,
            "is_trained": self.is_trained,
            "thresholds": self.thresholds,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def report_ground_truth(self, prediction_id: str, actual_outcome: bool, confidence_score: float):
        """Report ground truth for model improvement"""
        
        # Update performance metrics
        if actual_outcome:  # True infringement
            if confidence_score >= self.thresholds["auto_approve"]:
                # Correctly classified as infringement
                pass
            else:
                # False negative
                self.performance_metrics["false_negatives"] += 1
        else:  # Not infringement
            if confidence_score >= self.thresholds["auto_approve"]:
                # False positive
                self.performance_metrics["false_positives"] += 1
            else:
                # Correctly classified as not infringement
                pass
        
        logger.info(f"Ground truth reported for {prediction_id}: {actual_outcome}")
        
        # In production, this would trigger model retraining if enough new data