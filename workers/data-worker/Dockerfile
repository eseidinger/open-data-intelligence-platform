# syntax=docker/dockerfile:1

FROM python:3.12-alpine AS builder
WORKDIR /build

COPY pyproject.toml uv.lock ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-alpine
RUN addgroup -g 10001 -S odip && adduser -u 10001 -S -G odip odip

COPY --from=builder /install /usr/local
USER odip
ENTRYPOINT ["odip-ingest"]
