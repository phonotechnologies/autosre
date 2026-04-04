"""Sequential ClickHouse migration runner for AutoSRE.

Reads V*.sql files from the migrations/ directory, tracks applied versions
in schema_migrations, and applies pending migrations in order.

Usage:
    python -m infrastructure.clickhouse.migrate
    python infrastructure/clickhouse/migrate.py --host localhost --port 8123
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# V001 bootstraps the database and schema_migrations table, so it must
# be executed against the 'default' database before we can switch to
# the target database.
BOOTSTRAP_VERSION = 1


def _compute_checksum(sql: str) -> str:
    """SHA-256 of the migration SQL for drift detection."""
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _parse_version(filename: str) -> int:
    """Extract version number from V001__name.sql format."""
    match = re.match(r"V(\d+)", filename)
    if not match:
        raise ValueError(f"Invalid migration filename: {filename}")
    return int(match.group(1))


def _discover_migrations(directory: Path) -> list[tuple[int, str, Path]]:
    """Return sorted list of (version, name, path) for all V*.sql files."""
    migrations: list[tuple[int, str, Path]] = []
    for path in sorted(directory.glob("V*.sql")):
        version = _parse_version(path.name)
        name = path.stem  # e.g. V001__create_database
        migrations.append((version, name, path))
    return migrations


def _get_applied_versions(client, database: str) -> set[int]:
    """Query schema_migrations for already-applied version numbers."""
    try:
        result = client.query(f"SELECT version FROM {database}.schema_migrations")
        return {row[0] for row in result.result_rows}
    except Exception:
        return set()


def run_migrations(
    host: str = "localhost",
    port: int = 8123,
    database: str = "autosre",
) -> int:
    """Run all pending ClickHouse migrations.

    Connects via clickhouse-connect (HTTP interface), discovers V*.sql files,
    and applies any that have not yet been recorded in schema_migrations.

    Args:
        host: ClickHouse server hostname.
        port: ClickHouse HTTP port.
        database: Target database name.

    Returns:
        Number of migrations applied.
    """
    try:
        import clickhouse_connect
    except ImportError:
        print(
            "ERROR: clickhouse-connect is required. Install it with: pip install clickhouse-connect"
        )
        return -1

    migrations = _discover_migrations(MIGRATIONS_DIR)
    if not migrations:
        print("No migration files found.")
        return 0

    print(f"Connecting to ClickHouse at {host}:{port} ...")

    # Connect without a database first so we can run V001 (CREATE DATABASE)
    try:
        client = clickhouse_connect.get_client(host=host, port=port)
    except Exception as exc:
        print(f"ERROR: Failed to connect to ClickHouse: {exc}")
        return -1

    # Separate V001 (bootstrap) from the rest
    bootstrap = [m for m in migrations if m[0] == BOOTSTRAP_VERSION]
    remaining = [m for m in migrations if m[0] != BOOTSTRAP_VERSION]

    applied_count = 0

    # Phase 1: Run V001 bootstrap if needed (creates database + schema_migrations)
    if bootstrap:
        version, name, path = bootstrap[0]
        applied = _get_applied_versions(client, database)
        if version not in applied:
            sql = path.read_text()
            checksum = _compute_checksum(sql)
            print(f"  Applying {name} (bootstrap) ...")
            try:
                # V001 may contain multiple statements
                for stmt in _split_statements(sql):
                    client.command(stmt)
                # Record the migration
                client.command(
                    f"INSERT INTO {database}.schema_migrations "
                    f"(version, name, checksum) VALUES "
                    f"({version}, '{name}', '{checksum}')"
                )
                applied_count += 1
                print(f"    Applied {name}")
            except Exception as exc:
                print(f"    FAILED: {exc}")
                return -1
        else:
            print(f"  {name} already applied (skip)")

    # Phase 2: Reconnect targeting the database for remaining migrations
    try:
        client = clickhouse_connect.get_client(host=host, port=port, database=database)
    except Exception as exc:
        print(f"ERROR: Failed to connect to database '{database}': {exc}")
        return -1

    applied = _get_applied_versions(client, database)

    pending = [(v, n, p) for v, n, p in remaining if v not in applied]
    if not pending:
        total = len(migrations)
        print(f"All {total} migrations already applied. Nothing to do.")
        return applied_count

    print(f"Found {len(pending)} pending migration(s).")

    for version, name, path in pending:
        sql = path.read_text()
        checksum = _compute_checksum(sql)
        print(f"  Applying {name} ...")
        try:
            for stmt in _split_statements(sql):
                client.command(stmt)
            # Record successful migration
            client.command(
                f"INSERT INTO {database}.schema_migrations "
                f"(version, name, checksum) VALUES "
                f"({version}, '{name}', '{checksum}')"
            )
            applied_count += 1
            print(f"    Applied {name}")
        except Exception as exc:
            print(f"    FAILED on {name}: {exc}")
            print(f"  Stopping migration. {applied_count} migration(s) applied before failure.")
            return -1

    print(f"Done. {applied_count} migration(s) applied successfully.")
    return applied_count


def _split_statements(sql: str) -> list[str]:
    """Split SQL text into individual statements, skipping comments and blanks."""
    statements: list[str] = []
    current: list[str] = []

    for line in sql.splitlines():
        stripped = line.strip()
        # Skip pure comment lines
        if stripped.startswith("--") and not current:
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            # Remove trailing semicolon for clickhouse-connect
            stmt = stmt.rstrip(";").strip()
            if stmt and not all(
                ln.strip().startswith("--") or not ln.strip() for ln in stmt.splitlines()
            ):
                statements.append(stmt)
            current = []

    # Handle trailing statement without semicolon
    if current:
        stmt = "\n".join(current).strip().rstrip(";").strip()
        if stmt and not all(
            ln.strip().startswith("--") or not ln.strip() for ln in stmt.splitlines()
        ):
            statements.append(stmt)

    return statements


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run AutoSRE ClickHouse migrations")
    parser.add_argument("--host", default="localhost", help="ClickHouse host")
    parser.add_argument("--port", type=int, default=8123, help="ClickHouse HTTP port")
    parser.add_argument("--database", default="autosre", help="Target database")
    args = parser.parse_args()

    result = run_migrations(host=args.host, port=args.port, database=args.database)
    sys.exit(0 if result >= 0 else 1)
