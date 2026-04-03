"""Deep learning anomaly detection models (PyTorch).

Ported from Paper 5: "Evaluating ML-based anomaly detection on unified
OpenTelemetry telemetry" (IEEE Access, 2026).

All models are autoencoders trained on normal data. Anomaly scores are
derived from reconstruction error, normalized to [0, 1] via sigmoid of
z-scores. Degenerate (constant) reconstructions are penalized with
score=1.0.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from autosre.detection.models.base import BaseDetector, ModelRegistry

SEQ_LENGTH = 30
BATCH_SIZE = 512
EPOCHS = 50
PATIENCE = 10


def _get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def create_sequences(X: np.ndarray, seq_length: int = SEQ_LENGTH) -> np.ndarray:
    """Create sliding window sequences for temporal models."""
    if len(X) < seq_length:
        return np.array([])
    return np.array([X[i : i + seq_length] for i in range(len(X) - seq_length + 1)])


# ---------------------------------------------------------------------------
# PyTorch model architectures
# ---------------------------------------------------------------------------


class LSTMAutoencoder(nn.Module):
    def __init__(
        self, n_features: int, hidden_dim: int = 64, n_layers: int = 2, dropout: float = 0.1
    ):
        super().__init__()
        self.encoder = nn.LSTM(
            n_features,
            hidden_dim,
            n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.decoder = nn.LSTM(
            hidden_dim,
            hidden_dim,
            n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.output_layer = nn.Linear(hidden_dim, n_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, (h, c) = self.encoder(x)
        decoder_input = h[-1].unsqueeze(1).repeat(1, x.size(1), 1)
        decoder_out, _ = self.decoder(decoder_input, (h, c))
        return self.output_layer(decoder_out)


class TransformerAutoencoder(nn.Module):
    def __init__(
        self,
        n_features: int,
        d_model: int = 64,
        nhead: int = 4,
        n_layers: int = 2,
        dropout: float = 0.1,
        seq_len: int = SEQ_LENGTH,
    ):
        super().__init__()
        self.input_proj = nn.Linear(n_features, d_model)
        self.pos_encoding = nn.Parameter(torch.randn(1, seq_len, d_model) * 0.1)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=n_layers)
        self.output_proj = nn.Linear(d_model, n_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_proj = self.input_proj(x) + self.pos_encoding[:, : x.size(1), :]
        memory = self.encoder(x_proj)
        decoded = self.decoder(x_proj, memory)
        return self.output_proj(decoded)


class CNN1DAutoencoder(nn.Module):
    def __init__(
        self,
        n_features: int,
        filters: int = 64,
        kernel_size: int = 5,
        n_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        enc_layers: list[nn.Module] = []
        in_ch = n_features
        self._bottleneck_ch = 0
        for i in range(n_layers):
            out_ch = max(filters // (2**i) if i > 0 else filters, 8)
            enc_layers.extend(
                [
                    nn.Conv1d(in_ch, out_ch, kernel_size, padding=kernel_size // 2),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                ]
            )
            in_ch = out_ch
        self.encoder = nn.Sequential(*enc_layers)
        self._bottleneck_ch = in_ch

        dec_layers: list[nn.Module] = []
        for i in range(n_layers - 1, -1, -1):
            out_ch = max(filters // (2**i) if i > 0 else filters, 8)
            if i == 0:
                out_ch = n_features
            dec_layers.extend(
                [
                    nn.Conv1d(in_ch, out_ch, kernel_size, padding=kernel_size // 2),
                    nn.ReLU() if i > 0 else nn.Identity(),
                ]
            )
            in_ch = out_ch
        self.decoder = nn.Sequential(*dec_layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded.transpose(1, 2)


class LSTMVariationalAutoencoder(nn.Module):
    def __init__(
        self,
        n_features: int,
        hidden_dim: int = 64,
        n_layers: int = 2,
        latent_dim: int = 32,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.encoder = nn.LSTM(
            n_features,
            hidden_dim,
            n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        self.fc_decode = nn.Linear(latent_dim, hidden_dim)
        self.decoder = nn.LSTM(
            hidden_dim,
            hidden_dim,
            n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.output_layer = nn.Linear(hidden_dim, n_features)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        return mu + torch.randn_like(std) * std

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        _, (h, _) = self.encoder(x)
        h_last = h[-1]
        mu = self.fc_mu(h_last)
        logvar = self.fc_logvar(h_last)
        z = self.reparameterize(mu, logvar)
        z_proj = self.fc_decode(z)
        decoder_input = z_proj.unsqueeze(1).repeat(1, x.size(1), 1)
        h0 = z_proj.unsqueeze(0).repeat(self.n_layers, 1, 1)
        c0 = torch.zeros_like(h0)
        decoder_out, _ = self.decoder(decoder_input, (h0, c0))
        return self.output_layer(decoder_out), mu, logvar


def _vae_loss(
    recon_x: torch.Tensor,
    x: torch.Tensor,
    mu: torch.Tensor,
    logvar: torch.Tensor,
    beta: float = 0.1,
) -> torch.Tensor:
    mse = nn.functional.mse_loss(recon_x, x, reduction="mean")
    kl = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return mse + beta * kl


# ---------------------------------------------------------------------------
# Detector wrappers
# ---------------------------------------------------------------------------


class _DeepDetectorBase(BaseDetector):
    """Shared training and scoring logic for all autoencoder detectors."""

    def __init__(
        self,
        seq_length: int = SEQ_LENGTH,
        epochs: int = EPOCHS,
        batch_size: int = BATCH_SIZE,
        lr: float = 1e-3,
        **_: Any,
    ):
        self.seq_length = seq_length
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self._model: nn.Module | None = None
        self._device = _get_device()
        self._train_mse_mean: float = 0.0
        self._train_mse_std: float = 1.0

    def _build_model(self, n_features: int) -> nn.Module:
        raise NotImplementedError

    def fit(self, X_normal: np.ndarray, X_val: np.ndarray | None = None) -> None:
        X_seq = create_sequences(X_normal, self.seq_length)
        if len(X_seq) == 0:
            raise ValueError(f"Not enough data for seq_length={self.seq_length}")
        n_features = X_seq.shape[2]
        self._model = self._build_model(n_features).to(self._device)

        X_val_seq = create_sequences(X_val, self.seq_length) if X_val is not None else None
        self._train_loop(X_seq, X_val_seq)
        self._compute_train_stats(X_seq)

    def _train_loop(self, X_train_seq: np.ndarray, X_val_seq: np.ndarray | None) -> None:
        assert self._model is not None
        optimizer = torch.optim.Adam(self._model.parameters(), lr=self.lr)
        criterion = nn.MSELoss()
        loader = DataLoader(
            TensorDataset(torch.FloatTensor(X_train_seq)),
            batch_size=self.batch_size,
            shuffle=True,
        )

        best_val_loss = float("inf")
        patience_counter = 0

        for _ in range(self.epochs):
            self._model.train()
            for (batch,) in loader:
                batch = batch.to(self._device)
                optimizer.zero_grad()
                recon = self._forward(batch)
                loss = criterion(recon, batch)
                loss.backward()
                optimizer.step()

            if X_val_seq is not None and len(X_val_seq) > 0:
                val_loss = self._eval_loss(X_val_seq, criterion)
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= PATIENCE:
                        break

        self._free_cache()

    def _forward(self, batch: torch.Tensor) -> torch.Tensor:
        assert self._model is not None
        return self._model(batch)

    def _eval_loss(self, X_seq: np.ndarray, criterion: nn.Module) -> float:
        assert self._model is not None
        self._model.eval()
        total_loss = 0.0
        n = 0
        with torch.no_grad():
            for i in range(0, len(X_seq), self.batch_size):
                xb = torch.FloatTensor(X_seq[i : i + self.batch_size]).to(self._device)
                rb = self._forward(xb)
                total_loss += criterion(rb, xb).item() * len(xb)
                n += len(xb)
        return total_loss / max(n, 1)

    def _compute_train_stats(self, X_train_seq: np.ndarray) -> None:
        assert self._model is not None
        self._model.eval()
        all_mse: list[np.ndarray] = []
        with torch.no_grad():
            for i in range(0, len(X_train_seq), self.batch_size):
                xb = torch.FloatTensor(X_train_seq[i : i + self.batch_size]).to(self._device)
                rb = self._forward(xb)
                mse = torch.mean((xb - rb) ** 2, dim=(1, 2)).cpu().numpy()
                all_mse.append(mse)
        train_mse = np.concatenate(all_mse)
        self._train_mse_mean = float(np.mean(train_mse))
        self._train_mse_std = float(np.std(train_mse))
        self._free_cache()

    def score(self, X: np.ndarray) -> np.ndarray:
        assert self._model is not None, "Model not fitted. Call fit() first."
        X_seq = create_sequences(X, self.seq_length)
        if len(X_seq) == 0:
            return np.array([])

        self._model.eval()
        all_mse: list[np.ndarray] = []
        all_degenerate: list[np.ndarray] = []
        with torch.no_grad():
            for i in range(0, len(X_seq), self.batch_size):
                xb = torch.FloatTensor(X_seq[i : i + self.batch_size]).to(self._device)
                rb = self._forward(xb)
                mse = torch.mean((xb - rb) ** 2, dim=(1, 2)).cpu().numpy()
                all_mse.append(mse)
                recon_var = torch.var(rb, dim=(1, 2)).cpu().numpy()
                all_degenerate.append(recon_var < 1e-6)

        mse = np.concatenate(all_mse)
        degenerate_mask = np.concatenate(all_degenerate)
        z_scores = (mse - self._train_mse_mean) / (self._train_mse_std + 1e-8)
        scores = _sigmoid(z_scores)
        scores[degenerate_mask] = 1.0
        self._free_cache()
        return scores

    def _free_cache(self) -> None:
        if self._device == "mps":
            torch.mps.empty_cache()
        elif self._device == "cuda":
            torch.cuda.empty_cache()


@ModelRegistry.register
class LSTMAutoencoderDetector(_DeepDetectorBase):
    """LSTM Autoencoder detector. Paper 5: sequence-based, semi-supervised."""

    name = "lstm_ae"

    def __init__(
        self,
        n_features: int = 0,
        hidden_dim: int = 64,
        n_layers: int = 2,
        dropout: float = 0.1,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.dropout = dropout

    def _build_model(self, n_features: int) -> nn.Module:
        return LSTMAutoencoder(n_features, self.hidden_dim, self.n_layers, self.dropout)

    def get_params(self) -> dict[str, Any]:
        return {"hidden_dim": self.hidden_dim, "n_layers": self.n_layers, "dropout": self.dropout}


@ModelRegistry.register
class TransformerAutoencoderDetector(_DeepDetectorBase):
    """Transformer Autoencoder detector. Paper 5 best: traces AUC=0.800."""

    name = "transformer_ae"

    def __init__(
        self,
        n_features: int = 0,
        d_model: int = 64,
        nhead: int = 4,
        n_layers: int = 2,
        dropout: float = 0.1,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.d_model = d_model
        self.nhead = nhead
        self.n_layers = n_layers
        self.dropout = dropout

    def _build_model(self, n_features: int) -> nn.Module:
        return TransformerAutoencoder(
            n_features,
            self.d_model,
            self.nhead,
            self.n_layers,
            self.dropout,
            self.seq_length,
        )

    def get_params(self) -> dict[str, Any]:
        return {
            "d_model": self.d_model,
            "nhead": self.nhead,
            "n_layers": self.n_layers,
            "dropout": self.dropout,
        }


@ModelRegistry.register
class CNN1DAutoencoderDetector(_DeepDetectorBase):
    """1D-CNN Autoencoder detector. Paper 5: periodic pattern detection."""

    name = "cnn1d_ae"

    def __init__(
        self,
        n_features: int = 0,
        filters: int = 64,
        kernel_size: int = 5,
        n_layers: int = 2,
        dropout: float = 0.1,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.filters = filters
        self.kernel_size = kernel_size
        self.n_layers = n_layers
        self.dropout = dropout

    def _build_model(self, n_features: int) -> nn.Module:
        return CNN1DAutoencoder(
            n_features, self.filters, self.kernel_size, self.n_layers, self.dropout
        )

    def get_params(self) -> dict[str, Any]:
        return {
            "filters": self.filters,
            "kernel_size": self.kernel_size,
            "n_layers": self.n_layers,
            "dropout": self.dropout,
        }


@ModelRegistry.register
class LSTMVAEDetector(_DeepDetectorBase):
    """LSTM Variational Autoencoder detector. Paper 5: uncertainty quantification."""

    name = "lstm_vae"

    def __init__(
        self,
        n_features: int = 0,
        hidden_dim: int = 64,
        n_layers: int = 2,
        latent_dim: int = 32,
        dropout: float = 0.1,
        beta: float = 0.1,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.latent_dim = latent_dim
        self.dropout = dropout
        self.beta = beta

    def _build_model(self, n_features: int) -> nn.Module:
        return LSTMVariationalAutoencoder(
            n_features,
            self.hidden_dim,
            self.n_layers,
            self.latent_dim,
            self.dropout,
        )

    def _forward(self, batch: torch.Tensor) -> torch.Tensor:
        assert self._model is not None
        recon, _, _ = self._model(batch)
        return recon

    def _train_loop(self, X_train_seq: np.ndarray, X_val_seq: np.ndarray | None) -> None:
        assert self._model is not None
        optimizer = torch.optim.Adam(self._model.parameters(), lr=self.lr)
        loader = DataLoader(
            TensorDataset(torch.FloatTensor(X_train_seq)),
            batch_size=self.batch_size,
            shuffle=True,
        )

        best_val_loss = float("inf")
        patience_counter = 0

        for _ in range(self.epochs):
            self._model.train()
            for (batch,) in loader:
                batch = batch.to(self._device)
                optimizer.zero_grad()
                recon, mu, logvar = self._model(batch)
                loss = _vae_loss(recon, batch, mu, logvar, beta=self.beta)
                loss.backward()
                optimizer.step()

            if X_val_seq is not None and len(X_val_seq) > 0:
                self._model.eval()
                total_loss = 0.0
                n = 0
                with torch.no_grad():
                    for i in range(0, len(X_val_seq), self.batch_size):
                        xb = torch.FloatTensor(X_val_seq[i : i + self.batch_size]).to(self._device)
                        rb, v_mu, v_logvar = self._model(xb)
                        total_loss += _vae_loss(rb, xb, v_mu, v_logvar, self.beta).item() * len(xb)
                        n += len(xb)
                val_loss = total_loss / max(n, 1)
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= PATIENCE:
                        break

        self._free_cache()

    def get_params(self) -> dict[str, Any]:
        return {
            "hidden_dim": self.hidden_dim,
            "n_layers": self.n_layers,
            "latent_dim": self.latent_dim,
            "dropout": self.dropout,
            "beta": self.beta,
        }
