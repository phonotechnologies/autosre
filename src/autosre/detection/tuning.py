"""Optuna-based hyperparameter tuning for all 6 detection models.

Ported from Paper 5 (IEEE Access, 2026). Search spaces match the paper's
1,800-trial Optuna setup across Isolation Forest, One-Class SVM, LSTM-AE,
Transformer-AE, CNN1D-AE, and LSTM-VAE.

Usage:
    tuner = HyperparameterTuner(n_trials=300)
    best_params = tuner.tune("isolation_forest", X_train, X_val, y_val)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import optuna
from sklearn.metrics import roc_auc_score

from autosre.detection.models.base import ModelRegistry

logger = logging.getLogger(__name__)

# Suppress Optuna's verbose trial logging; we log summaries ourselves.
optuna.logging.set_verbosity(optuna.logging.WARNING)

# Maps model names to their objective methods.
_MODEL_OBJECTIVES = {
    "isolation_forest": "_objective_isolation_forest",
    "ocsvm": "_objective_ocsvm",
    "lstm_ae": "_objective_lstm_ae",
    "transformer_ae": "_objective_transformer_ae",
    "cnn1d_ae": "_objective_cnn1d_ae",
    "lstm_vae": "_objective_lstm_vae",
}


class HyperparameterTuner:
    """Optuna-based hyperparameter tuning for all detection models.

    Each model has a dedicated objective function with search spaces derived
    from Paper 5's Optuna configuration.
    """

    def __init__(self, n_trials: int = 300, seed: int = 42):
        self.n_trials = n_trials
        self.seed = seed

    def tune(
        self,
        model_name: str,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> dict[str, Any]:
        """Run Optuna optimization and return best params.

        Args:
            model_name: one of the 6 registered model names.
            X_train: training data (normal samples only).
            X_val: validation data (mix of normal and anomalous).
            y_val: binary labels for validation data (0=normal, 1=anomaly).

        Returns:
            Dictionary of best hyperparameters found.

        Raises:
            ValueError: if model_name has no associated objective function.
        """
        if model_name not in _MODEL_OBJECTIVES:
            available = ", ".join(sorted(_MODEL_OBJECTIVES.keys()))
            raise ValueError(f"No tuning objective for '{model_name}'. Available: {available}")

        objective_method = getattr(self, _MODEL_OBJECTIVES[model_name])

        def objective(trial: optuna.Trial) -> float:
            return objective_method(trial, X_train, X_val, y_val)

        sampler = optuna.samplers.TPESampler(seed=self.seed)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        logger.info(
            "Tuning complete for %s: best AUC=%.4f after %d trials",
            model_name,
            study.best_value,
            len(study.trials),
        )
        return study.best_params

    def _score_model(
        self,
        model_name: str,
        params: dict[str, Any],
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> float:
        """Instantiate model with params, fit, score, and compute AUC."""
        model_cls = ModelRegistry.get(model_name)
        detector = model_cls(**params)
        detector.fit(X_train)
        scores = detector.score(X_val)

        # Deep models may produce fewer scores than labels (sequence windowing).
        if len(scores) < len(y_val):
            y_eval = y_val[len(y_val) - len(scores) :]
        else:
            y_eval = y_val

        if len(np.unique(y_eval)) < 2:
            return 0.5

        return float(roc_auc_score(y_eval, scores))

    # ------------------------------------------------------------------
    # Classical model objectives
    # ------------------------------------------------------------------

    def _objective_isolation_forest(
        self,
        trial: optuna.Trial,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> float:
        """Paper 5 search space: IF."""
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "contamination": trial.suggest_float("contamination", 0.01, 0.15),
            "max_features": trial.suggest_float("max_features", 0.5, 1.0),
            "max_samples": trial.suggest_float("max_samples", 0.5, 1.0),
        }
        return self._score_model("isolation_forest", params, X_train, X_val, y_val)

    def _objective_ocsvm(
        self,
        trial: optuna.Trial,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> float:
        """Paper 5 search space: One-Class SVM."""
        params = {
            "nu": trial.suggest_float("nu", 0.01, 0.2),
            "kernel": trial.suggest_categorical("kernel", ["rbf", "poly", "sigmoid"]),
            "gamma": trial.suggest_categorical("gamma", ["scale", "auto"]),
        }
        return self._score_model("ocsvm", params, X_train, X_val, y_val)

    # ------------------------------------------------------------------
    # Deep model objectives
    # ------------------------------------------------------------------

    def _objective_lstm_ae(
        self,
        trial: optuna.Trial,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> float:
        """Paper 5 search space: LSTM Autoencoder."""
        params = {
            "n_features": X_train.shape[1],
            "hidden_dim": trial.suggest_int("hidden_dim", 32, 128, step=16),
            "n_layers": trial.suggest_int("n_layers", 1, 3),
            "dropout": trial.suggest_float("dropout", 0.05, 0.3),
            "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
            "epochs": trial.suggest_int("epochs", 20, 50),
        }
        return self._score_model("lstm_ae", params, X_train, X_val, y_val)

    def _objective_transformer_ae(
        self,
        trial: optuna.Trial,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> float:
        """Paper 5 search space: Transformer Autoencoder."""
        d_model = trial.suggest_int("d_model", 32, 128, step=16)
        nhead = trial.suggest_categorical("nhead", [2, 4, 8])
        # Ensure d_model is divisible by nhead.
        d_model = max(d_model, nhead)
        d_model = d_model - (d_model % nhead)

        params = {
            "n_features": X_train.shape[1],
            "d_model": d_model,
            "nhead": nhead,
            "n_layers": trial.suggest_int("n_layers", 1, 3),
            "dropout": trial.suggest_float("dropout", 0.05, 0.3),
            "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
            "epochs": trial.suggest_int("epochs", 20, 50),
        }
        return self._score_model("transformer_ae", params, X_train, X_val, y_val)

    def _objective_cnn1d_ae(
        self,
        trial: optuna.Trial,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> float:
        """Paper 5 search space: CNN1D Autoencoder."""
        params = {
            "n_features": X_train.shape[1],
            "filters": trial.suggest_int("filters", 32, 128, step=16),
            "kernel_size": trial.suggest_categorical("kernel_size", [3, 5, 7]),
            "n_layers": trial.suggest_int("n_layers", 1, 3),
            "dropout": trial.suggest_float("dropout", 0.05, 0.3),
            "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
            "epochs": trial.suggest_int("epochs", 20, 50),
        }
        return self._score_model("cnn1d_ae", params, X_train, X_val, y_val)

    def _objective_lstm_vae(
        self,
        trial: optuna.Trial,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> float:
        """Paper 5 search space: LSTM Variational Autoencoder."""
        params = {
            "n_features": X_train.shape[1],
            "hidden_dim": trial.suggest_int("hidden_dim", 32, 128, step=16),
            "n_layers": trial.suggest_int("n_layers", 1, 3),
            "latent_dim": trial.suggest_int("latent_dim", 16, 64, step=8),
            "dropout": trial.suggest_float("dropout", 0.05, 0.3),
            "beta": trial.suggest_float("beta", 0.01, 1.0, log=True),
            "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
            "epochs": trial.suggest_int("epochs", 20, 50),
        }
        return self._score_model("lstm_vae", params, X_train, X_val, y_val)
