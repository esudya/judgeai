# Dependency Inventory Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; TDD and final independent review.

**Goal:** Deliver the independent technical inventory slice of T19.
**Architecture:** Offline standard-library generator, reviewed evidence, deterministic CycloneDX + report.
**Tech Stack:** Python 3.11+, unittest; no new dependencies.
**Spec:** docs/superpowers/specs/2026-10-28-dependency-inventory-design.md

## Global constraints
- No app/model/parser/matching/schema or installed dependency changes.
- Never read credentials/private case files; no invented Python versions, licenses or rights approval.
- T19 remains partial until unresolved decisions and runtime inventory are addressed.

## Review focus
- Range lower bounds must not become exact installed versions.
- Nested/scoped npm packages and SRI hashes retain unique identities/provenance.
- Missing license/lock entries and invalid source credentials must not become silent approval.
- Check mode is read-only and nonzero on drift; byte-identical output for identical inputs.
- Upstream license metadata is evidence, not version-specific legal certification.

### Task 1: Generator and evidence
- [x] Write failing offline tests for declarations, locked identities/hashes, missing metadata, secrets and drift.
- [x] Implement tools/dependency_inventory.py with pure build_inventory(root) and CLI generate/check.
- [x] Read primary license/model/data artifacts and commit public evidence only.
- [x] Generate SBOM/report; run full standalone tests, lint and primary-schema validation.

### Task 2: Delivery
- [x] Document installation reproducibility limits, owner decisions and refresh steps; mark T19 partial.
- [x] Independent review, regression fixes if required, fresh verification and standalone Draft MR.
