# JudgeAI Engineering Rules

Scope: all project engineering work. These rules supplement the user's session instructions.

## Plan and evidence
- Read docs/TASKS.md and the relevant implementation plan before starting.
- Update the plan at task start and after every completed, verifiable step.
- Use [ ] pending, [~] in progress, [!] blocked, [x] verified complete.
- Distinguish implementation in a draft MR, passing checks, merged code and accepted functionality.
- Mark a parent task complete only when its full Definition of Done is satisfied.
- Record dates, commit/MR references, checks, failures and unverified requirements.
- Coordinate ownership; do not change T24–T27 scope/files while another task owns them.

## Architecture and reuse
- Separate domain/business rules, application use cases, infrastructure adapters and presentation.
- Domain code must not depend on FastAPI, SQLAlchemy, React, HTTP clients or environment settings.
- Application use cases orchestrate domain behavior through narrow interfaces/ports.
- Database, files, queues and LLM clients implement infrastructure adapters.
- HTTP handlers validate/translate requests, invoke use cases and map responses; keep business rules out.
- Frontend API/state logic is separate from view components. UI must not duplicate legal calculations.
- Dependencies point inward: presentation/infrastructure -> application -> domain.
- Inspect existing function bodies and contracts before adding alternatives; reuse suitable functions.
- Extract shared behavior when it has actual callers; avoid copy-paste and speculative frameworks.
- Preserve existing architecture while improving touched boundaries in small, reviewable changes.
- Document remaining boundary violations; do not label an unreviewed implementation clean architecture.

## Tests and safety
- Cover changed behavior with tests; use TDD when practical.
- Domain: independent deterministic unit tests, including missing/contradictory/boundary inputs.
- Use cases/adapters: integration and failure tests; access controls need cross-user negative tests.
- Frontend: behavior tests, typecheck/build and desktop/mobile inspection for UI changes.
- Keep existing coverage thresholds and required checks; never disable them to obtain green status.
- Report exactly which checks ran and which could not; a compile/lint pass does not prove functionality.
- Require a migration/backfill/rollback plan before schema changes; preserve existing private records.
- Never commit credentials, private case material or local runtime env files.
- No production deployment or merge without explicit authorization and required green checks.
