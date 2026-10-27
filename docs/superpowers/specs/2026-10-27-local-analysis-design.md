# Local verdict analysis

Approved direction: user's “делай” accepts the recommended local analysis flow.
Keep FastAPI, PostgreSQL, existing routes and cabinet design. No production deployment.

Deliverable: upload/text -> stored chat -> asynchronous analysis -> actual result after reload.
Preserve document content when chunking. Bound LLM context explicitly and report omitted text.
Facts used for legal checks must carry exact source excerpts; unsupported facts yield insufficient_data.
Add art. 18 domain rules and expose art. 15/18 checks with needs_legal_review=true.
Do not infer absence of convictions from missing data. No DOCX promise without an export route.
Existing JSON results remain readable: additive fields, schema_version=1, no SQL migration.

Approaches: (1) local end-to-end analysis (selected); (2) authentication first (deferred).
Risks: incomplete conviction histories, LLM extraction, law edition, scanned documents, process restarts.
Done: regression tests, API suite, core tests, frontend build, desktop/mobile inspection.
