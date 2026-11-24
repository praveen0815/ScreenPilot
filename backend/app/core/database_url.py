"""Build a SQLAlchemy-safe DATABASE_URL from discrete Postgres env vars."""

from __future__ import annotations

import os
from urllib.parse import quote_plus


def apply_compose_database_url(environ: dict[str, str] | None = None) -> str | None:
    """Percent-encode user/password so characters like `@` are not parsed as host.

    Docker Compose interpolates POSTGRES_PASSWORD into DATABASE_URL without
    encoding. SQLAlchemy splits on the first `@`, so a password containing `@`
    becomes a bogus hostname and DNS fails.

    When POSTGRES_HOST and the other POSTGRES_* parts are set (Compose),
    rewrite DATABASE_URL in-place and return it. Otherwise leave the
    existing DATABASE_URL alone.
    """

    env = os.environ if environ is None else environ
    host = env.get("POSTGRES_HOST")
    user = env.get("POSTGRES_USER")
    password = env.get("POSTGRES_PASSWORD")
    database = env.get("POSTGRES_DB")
    port = env.get("POSTGRES_PORT") or "5432"
    if not (host and user and password and database):
        return None
    url = (
        f"postgresql+asyncpg://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}"
    )
    env["DATABASE_URL"] = url
    return url
