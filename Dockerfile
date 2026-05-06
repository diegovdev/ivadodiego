# Stage 1: builder
FROM python:3.12-alpine AS builder

# Compile deps for pandas/numpy/scikit-learn on musl
RUN apk add --no-cache gcc musl-dev g++ libffi-dev openblas-dev

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install production deps only (no dev group)
RUN uv sync --no-dev

# Stage 2: runtime
FROM python:3.12-alpine AS runtime

# Runtime shared libs for numpy/scikit-learn
RUN apk add --no-cache libstdc++ openblas

RUN adduser -D -u 1000 appuser

WORKDIR /app

COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src /app/src

ENV PATH="/app/.venv/bin:$PATH"

USER 1000

EXPOSE 8000

CMD ["uvicorn", "museums.api:app", "--host", "0.0.0.0", "--port", "8000"]
