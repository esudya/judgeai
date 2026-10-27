# Local Verdict Analysis Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with TDD and whole-branch review.

**Goal:** Complete a local upload-to-result workflow with explicit legal-check limitations.
**Architecture:** Keep existing FastAPI routes and JSON persistence. Add domain rules to legal_core and map API facts to domain values. Replace cabinet mock calls with an asynchronous adapter.
**Tech Stack:** Python, FastAPI, PostgreSQL, React, TypeScript, Vite.
**Spec:** docs/superpowers/specs/2026-10-27-local-analysis-design.md

## Global Constraints
- No production deployment, secret logging, destructive migration or removal of existing functionality.
- Existing stack and cabinet design; new UI copy in English.
- Legal results require review; missing evidence gives insufficient_data.

## Review Focus
- Long paragraphs and context overflow: retain text in chunks; report context omitted.
- Failed multi-file uploads: clean files already written by the rejected request.
- Missing or fabricated citations: do not produce conclusive legal checks.
- Navigation during polling: stale responses must not replace the selected case.
- Null results, empty arrays and server errors: readable UI without fabricated values.

### Task 1: Document integrity
Files: src/services/knowledge_service.py, case_analyzer.py, api/chats.py, tests/test_documents.py, tests/test_api.py.
Interfaces: build_chunks(str)->list[str]; build_user_prompt(...)->str unchanged.
- [x] Write regressions for long paragraphs, truncation warnings and multi-file cleanup; run RED.
- [x] Implement bounded chunks, explicit LLM context warning, cleanup rejected uploads; run full API suite GREEN.

### Task 2: Evidence-backed legal checks
Files: packages/legal_core/legal_core/rules/art18.py, tests/test_art18.py, src/schemas/analysis.py, src/services/legal_checks.py, case_analyzer.py, Dockerfile.
Interfaces: classify_recidivism(current, priors)->Recidivism; build_legal_checks(facts, source_text)->list[LegalCheck].
- [x] Write boundary and exclusion tests for art.18 and unsupported/missing fact evidence; run RED.
- [x] Implement domain classification and conservative evidence adapter; install local legal_core in Docker; run both suites GREEN.

### Task 3: Live cabinet
Files: verdikt-web/src/api/client.ts, types.ts, cabinet/Cabinet.tsx, Composer.tsx, screens.tsx, components/SentenceScale.tsx.
Interfaces: listCases, createCase, getMessages, sendCase return Promises; explicit nullable results.
- [x] Add adapter tests for wire mapping, errors, null fields and multipart upload; run RED.
- [x] Implement live calls, status polling, file preservation and errors; keep demo fixtures for landing only.
- [x] Build and run desktop/mobile browser flow against isolated API and test database; verify reload and errors.

### Task 4: Verification and delivery
- [x] Run API/core tests, lint, frontend tests/build and inspect diff.
- [x] Update README with local setup and limitations; commit branch and present verified result.

## Verification record

2026-10-27: 42 API tests, 30 core tests, core coverage 99.2%, 3 web tests, production build and ruff pass. Browser: upload/result/reload, desktop/mobile, network/404/415 errors. Independent review found late-send navigation and cross-request attachment display; both reproduced RED then fixed GREEN with browser regressions.

Decisions: schema v1 additive fields; all chunks stored but embedding work bounded; shared precedent search opt-in; fake responses labelled; each request uses its own attachments with an explicit reminder. Real LLM, vector quality, auth, anonymization and DOCX remain outside this local increment.

## Продолжение по исходной концепции

Этот завершённый план описывает только локальный технический этап MR !7. Он не закрывает полное соответствие концепции. Дальнейший охват и Definition of Done записаны в [CONCEPT_ALIGNMENT.md](../../CONCEPT_ALIGNMENT.md), архитектура — [ROADMAP.md](../../ROADMAP.md), исполняемый чек-лист — [TASKS.md](../../TASKS.md), включая T13–T21. Проверка уже назначенного наказания имеет приоритет перед генерацией нового приговора.
