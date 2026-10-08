# syntax=docker/dockerfile:1

FROM node:22-alpine AS web-builder
WORKDIR /workspace/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

FROM eclipse-temurin:21-jdk-alpine AS api-builder
WORKDIR /workspace/platform-api

COPY services/platform-api/gradlew services/platform-api/build.gradle.kts services/platform-api/settings.gradle.kts ./
COPY services/platform-api/gradle ./gradle
RUN chmod +x gradlew && ./gradlew --no-daemon dependencies

COPY services/platform-api/src ./src
COPY --from=web-builder /workspace/web/dist/odip-web/browser/ ./src/main/resources/static/
RUN ./gradlew --no-daemon bootJar

FROM eclipse-temurin:21-jre-alpine AS platform
RUN apk add --no-cache curl \
    && addgroup --gid 10001 --system odip && adduser --uid 10001 --system --ingroup odip odip

WORKDIR /app
COPY --from=api-builder /workspace/platform-api/build/libs/*.jar /app/platform-api.jar

USER odip
ENV SPRING_PROFILES_ACTIVE=prod \
    SERVER_PORT=8080 \
    JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=/tmp"
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8080/actuator/health/liveness || exit 1
ENTRYPOINT ["java", "-jar", "/app/platform-api.jar"]
