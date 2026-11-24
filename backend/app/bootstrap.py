"""Container entrypoint. Runs the fixed Alembic upgrade, then the API."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    from app.core.config import get_settings
    from app.core.database_url import apply_compose_database_url
    from app.core.logging import configure_logging

    apply_compose_database_url()

    backend_root = Path(__file__).resolve().parents[1]
    settings = get_settings()
    configure_logging(settings.log_level)
    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_root,
        check=False,
    )
    if migration.returncode != 0:
        raise SystemExit(migration.returncode)
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=backend_root,
        )
    )


if __name__ == "__main__":
    main()
