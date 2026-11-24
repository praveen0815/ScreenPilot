FROM python:3.12-slim

WORKDIR /app

# Slow or flaky PyPI connections otherwise fail the layer with ReadTimeoutError.
ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_RETRIES=15

COPY pyproject.toml .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --timeout 300 --retries 15 --prefer-binary .

EXPOSE 8000

CMD ["python", "-m", "app.bootstrap"]
