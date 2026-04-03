"""AutoSRE CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from autosre import __version__

app = typer.Typer(
    name="autosre",
    help="Research-backed, OTel-native anomaly detection for SRE teams.",
    no_args_is_help=True,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    if version:
        console.print(f"autosre {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def init(
    output: Path = typer.Option("autosre.yaml", "--output", "-o", help="Config file path"),
):
    """Generate a default AutoSRE configuration file."""
    from autosre.config import AutoSREConfig

    if output.exists():
        overwrite = typer.confirm(f"{output} already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    config = AutoSREConfig()
    config.to_yaml(output)
    console.print(f"[green]Config written to {output}[/green]")
    console.print("Edit the file to configure your telemetry endpoint, models, and alerting.")


@app.command()
def train(
    data: Path = typer.Argument(..., help="Path to telemetry data (Parquet or CSV)"),
    config: Path = typer.Option("autosre.yaml", "--config", "-c", help="Config file"),
    output: Path = typer.Option("./models", "--output", "-o", help="Model output directory"),
    signal: str = typer.Option("metrics", "--signal", "-s", help="Signal type to train on"),
):
    """Train anomaly detection models on telemetry data."""
    import numpy as np
    import pandas as pd

    from autosre.config import AutoSREConfig
    from autosre.detection.models import ModelRegistry

    cfg = AutoSREConfig.from_yaml(config) if config.exists() else AutoSREConfig()

    console.print(f"[bold]Loading data from {data}...[/bold]")
    if data.suffix == ".parquet":
        df = pd.read_parquet(data)
    else:
        df = pd.read_csv(data)

    metadata_cols = {
        "service",
        "timestamp",
        "label",
        "fault_type",
        "phase",
        "run_id",
        "rep",
        "testbed",
        "count",
        "fold",
    }
    feature_cols = [
        c
        for c in df.columns
        if c not in metadata_cols and df[c].dtype in ("float64", "float32", "int64")
    ]
    X = df[feature_cols].values.astype(np.float32)

    console.print(f"  Features: {len(feature_cols)}, Samples: {len(X)}")

    models_to_train = cfg.detection.models
    if "auto" in models_to_train:
        models_to_train = ModelRegistry.list_models()

    output.mkdir(parents=True, exist_ok=True)

    for model_name in models_to_train:
        console.print(f"\n[bold cyan]Training {model_name}...[/bold cyan]")
        model_cls = ModelRegistry.get(model_name)
        detector = model_cls(n_features=len(feature_cols))
        detector.fit(X)
        model_path = output / f"{model_name}_{signal}.joblib"
        detector.save(model_path)
        console.print(f"  [green]Saved to {model_path}[/green]")

    n = len(models_to_train)
    console.print(f"\n[bold green]Training complete. {n} models saved to {output}/[/bold green]")


@app.command()
def detect(
    data: Path = typer.Argument(..., help="Path to telemetry data to score"),
    model_dir: Path = typer.Option("./models", "--model-dir", "-m", help="Trained model directory"),
    config: Path = typer.Option("autosre.yaml", "--config", "-c", help="Config file"),
    threshold: float = typer.Option(0.5, "--threshold", "-t", help="Anomaly threshold"),
):
    """Run anomaly detection on telemetry data."""
    import numpy as np
    import pandas as pd

    from autosre.detection.models.base import BaseDetector

    console.print(f"[bold]Loading data from {data}...[/bold]")
    if data.suffix == ".parquet":
        df = pd.read_parquet(data)
    else:
        df = pd.read_csv(data)

    metadata_cols = {
        "service",
        "timestamp",
        "label",
        "fault_type",
        "phase",
        "run_id",
        "rep",
        "testbed",
        "count",
        "fold",
    }
    feature_cols = [
        c
        for c in df.columns
        if c not in metadata_cols and df[c].dtype in ("float64", "float32", "int64")
    ]
    X = df[feature_cols].values.astype(np.float32)

    model_files = sorted(model_dir.glob("*.joblib"))
    if not model_files:
        console.print(f"[red]No models found in {model_dir}. Run 'autosre train' first.[/red]")
        raise typer.Exit(1)

    table = Table(title="Anomaly Detection Results")
    table.add_column("Model", style="cyan")
    table.add_column("Anomalies", style="red")
    table.add_column("Total", style="dim")
    table.add_column("Rate", style="yellow")

    for model_file in model_files:
        detector = BaseDetector.load(model_file)
        scores = detector.score(X)
        n_anomalies = int((scores >= threshold).sum())
        table.add_row(
            model_file.stem,
            str(n_anomalies),
            str(len(scores)),
            f"{n_anomalies / max(len(scores), 1) * 100:.1f}%",
        )

    console.print(table)


@app.command()
def status():
    """Show AutoSRE status and available models."""
    from autosre.detection.models import ModelRegistry

    table = Table(title="Available Detection Models")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")

    classical = ["isolation_forest", "ocsvm"]
    for name in ModelRegistry.list_models():
        model_type = "classical" if name in classical else "deep (sequence)"
        table.add_row(name, model_type)

    console.print(table)
    console.print(f"\n[dim]AutoSRE v{__version__} | https://autosre.dev[/dim]")


@app.command()
def models():
    """List all registered detection models."""
    status()


if __name__ == "__main__":
    app()
