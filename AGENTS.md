# Repository conventions

These rules apply to all ODIP components; follow additional component AGENTS.md instructions.

## Validation

- API: run `./gradlew ktlintCheck` in `services/platform-api`; use `ktlintFormat` to fix formatting. Run relevant tests for behavior changes. Integration tests require PostgreSQL.
- Web: run `npm ci` after dependency changes, then `npm run lint`, `npm test -- --watch=false`, and `npm run build` in `web`. Run accessibility checks for UI changes.
- Worker and repository Python scripts: run `uv sync --locked`, `uv run --locked ruff check src tests ../../scripts`, and `uv run --locked python -m unittest discover -s tests` in `workers/data-worker`. Use Ruff's safe `--fix` option and review the diff.
- Keep package locks committed with dependency changes. CI lint checks must pass without warnings; do not suppress rules broadly or introduce baselines to hide new violations.
- Do not edit or reformat immutable vendored contract kits, generated output, or dependency directories. Validate the pinned kit using the existing verification script.

## Logging

- Emit single-line structured JSON from API and worker processes. Keep API minimized request envelopes compatible with platform collection; use the worker logging formatter for worker diagnostics.
- Record stable event names, severity, elapsed milliseconds, HTTP status where available, and opaque request/run identifiers. Scope correlation context to the request/job and clean it up on every exit, including failure.
- Log successful lifecycle transitions at INFO, recoverable problems at WARNING, and failed operations at ERROR. Avoid logging polling/health successes at INFO.
- Never log tokens, claim tokens, cookies, authorization headers, source URLs, payloads, customer data, or unfiltered exception messages/tracebacks. Log safe error types/codes; keep diagnostic detail in authorized run records.
- Browser errors should be actionable without dumping requests, responses, or identity data. Do not add production console debug/info logging.
- Add focused tests when changing correlation, failure severity, or sensitive-data filtering. Logs must not change the outcome of business operations.
