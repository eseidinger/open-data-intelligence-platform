# syntax=docker/dockerfile:1

FROM python:3.12-alpine AS builder
WORKDIR /build

COPY workers/data-worker/pyproject.toml workers/data-worker/uv.lock ./
COPY workers/data-worker/src ./src
RUN pip install --no-cache-dir uv==0.12.17 && uv sync --frozen --no-dev --no-editable

FROM python:3.12-alpine
RUN addgroup -g 10001 -S odip && adduser -u 10001 -S -G odip odip

COPY --from=builder /build/.venv /build/.venv
ENV PATH="/build/.venv/bin:$PATH"
COPY contracts/vendor/contract-kit-v1.0.0/contract-kit /opt/contract-kit
ENV ODIP_CONTRACT_KIT=/opt/contract-kit ODIP_IDENTITY_MODE=platform
USER odip
ENTRYPOINT ["odip-ingest"]
