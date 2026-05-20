# Implementation Backlog

> Generated from PRD Section 10 (Release Plan) and Section 5 (Feature Specification)
> Last updated: 2026-05-06

## Summary
- Total items: 68
- Phases covered: 1–10
- Current status: **Phase 6 Complete** — Phases 1–5 deliverables are fully implemented in `pke.mjs`. Phase 6 (Self-Improvement) is complete: retrieval tuning proposals, acceptance-rate-based confidence adjustment, usage pattern analysis, daily proposal rate-limiting, and batch-safe fast-path approval are all operational. Phases 7–10 are not yet started.

---

## Phase 1: Foundation (Week 1–2)

**Purpose:** Establish core CLI infrastructure, vault structure, and qmd integration.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P1-01 | Implement `pke help` with full command list and governance principles | Must | Done | `pke help` prints all commands, global options, and principles; exits 0. See §7.1 `pke help`. | None |
| P1-02 | Implement `pke status` with vault health and qmd connectivity check | Must | Done | `pke status` reports vault path, baseline, tracked files, wiki count, template compliance; runs `qmd status`. Per US-06, §7.1 `pke status`. | None |
| P1-03 | Implement `pke use` for natural-language knowledge retrieval via qmd | Must | Done | `pke use "question"` delegates to `qmd query`; no files modified; error on empty query. Per US-02, §7.1 `pke use`. | None |
| P1-04 | Implement `pke capture` with preview-only default and `--write` mode | Must | Done | Preview shows source/target/write status; `--write` copies to `raw/_captures/` with timestamp; wiki not modified; error on missing source. Per US-01, §7.1 `pke capture`. | None |
| P1-05 | Implement `pke changed` with SHA-256 baseline diffing and `--save` | Must | Done | Reports added/modified/removed files vs. baseline; `--save` persists new baseline to `state.json`. Per §7.1 `pke changed`. | None |
| P1-06 | Initialize vault structure with `raw/`, `wiki/`, `.pke/` directories | Must | Done | Vault directories created on first use; `state.json` created in `.pke/`. Per §10.1 Phase 1. | None |
| P1-07 | Implement global CLI option parsing (`--vault`, `--collection`, `--state`, `--json`) | Must | Done | All global options override defaults correctly; boolean flags parsed without values. See §7.4. | None |
| P1-08 | Implement error handling pattern (main catch, `pke:` prefix, exit code 1) | Must | Done | Unknown commands produce actionable error; missing args produce usage message. See §7.3. | None |

### Phase Exit Criteria
- [x] `pke use` returns relevant qmd results for common queries
- [x] `pke capture` previews and copies evidence files
- [x] `pke changed` detects file changes against saved baseline
- [x] `pke status` confirms healthy state with qmd connectivity
- [x] Basic capture → index → query loop working end-to-end

---

## Phase 2: Knowledge Building (Week 3–4)

**Purpose:** Populate the vault with sufficient content for meaningful retrieval testing.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P2-01 | Implement `pke daily` for daily compilation proposal with change review | Must | Done | Reports changes since baseline; lists compile candidates with kind/hints; mode labeled "proposal-only"; `--save` updates baseline. Per US-03, §7.1 `pke daily`. | P1-05 |
| P2-02 | Index 50+ raw files in qmd collection | Must | Done | `qmd status` shows 50+ documents in the configured collection. Per §10.1 Phase 2 exit criteria. | P1-06 |
| P2-03 | Create 10+ wiki pages following the 7-section template | Must | Done | `pke status` reports 10+ wiki pages; template compliance tracked. Per §10.1 Phase 2 exit criteria. | P1-02 |
| P2-04 | Implement template compliance checking in `pke status` | Must | Done | `pke status` reports compliant/non-compliant pages and lists missing sections. Per §5.1 Capability 2. | P1-02 |
| P2-05 | Establish daily workflow habit (5+ consecutive workdays of `pke daily`) | Should | Done | Event log shows 5+ consecutive `pke daily` invocations. Per §9.5 Phase 2→3 gate. | P2-01 |

### Phase Exit Criteria
- [x] 50+ raw files indexed in qmd
- [x] 10+ wiki pages created following 7-section template
- [x] `pke daily` operational for daily change review
- [x] `pke changed --save` baseline management working
- [x] Retrieval returns relevant results for common queries

---

## Phase 3: Compilation Engine (Week 5–7)

**Purpose:** Implement automated knowledge synthesis via the proposal workflow.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P3-01 | Implement `pke compile` with proposal-only compile plan and change report | Must | Done | Queries qmd for topic context; produces change report (before/after scan + baseline diff); mode "proposal-only"; zero wiki writes. Per US-05, §7.1 `pke compile`. | P1-03 |
| P3-02 | Implement `pke learn` for draft-vs-final document comparison | Must | Done | Computes line-level diff; classifies into 4 categories (Product Judgment, Factual, Style, Other); proposes compile actions; no wiki writes. Per US-04, §7.1 `pke learn`. | None |
| P3-03 | Implement `pke candidates` to list compile-trigger events | Must | Done | Filters events by compile-trigger types; shows event_type, source_file, reason, suggested_target; newest first, max 50. Per US-07, §7.1 `pke candidates`. | P5-01 |
| P3-04 | Implement `pke propose` from `--path` or `--event` with append-only patches | Must | Done | Creates proposal with unique ID, patch operations targeting safe sections (Evidence, Open Questions, Conflicts, Stale Claims); writes to `.pke/proposals/`. Per US-07, §7.1 `pke propose`. | P3-03 |
| P3-05 | Implement `pke apply` with backup, patch, status update, and qmd refresh | Must | Done | Validates pending status + target existence; backs up target page; applies append-only patches; updates qmd; archives to `.pke/applied/`. Per US-08, §7.1 `pke apply`. | P3-04 |
| P3-06 | Implement `pke reject` with status update and archival | Must | Done | Sets status "rejected"; records `rejectedAt`; copies to `.pke/rejected/`. Per US-08, §7.1 `pke reject`. | P3-04 |
| P3-07 | Implement `pke proposals` to list all proposals with optional status filter | Must | Done | Lists proposals from `.pke/proposals/` with id, status, source, target, reason; `--status` filter. Per US-07, §7.1 `pke proposals`. | P3-04 |
| P3-08 | Implement `pke proposal <id>` to show full proposal details | Must | Done | Shows all fields including patch operations; error on missing proposal. Per US-07, §7.1 `pke proposal`. | P3-04 |
| P3-09 | Implement idempotent patch application (skip duplicate content) | Must | Done | `applyPatchOperation` checks if content already exists before appending. See §7.1 `pke apply`. | P3-05 |

### Phase Exit Criteria
- [x] `pke compile` generates compile context for any topic
- [x] `pke learn` classifies draft-vs-final changes
- [x] `pke propose` / `pke apply` / `pke reject` working end-to-end
- [x] Atomic write pattern with backup-before-mutation implemented
- [x] qmd refresh after successful apply

---

## Phase 4: Governance & Quality (Week 8–9)

**Purpose:** Implement quality gates, staleness detection, and conflict management.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P4-01 | Implement `pke stale` for topic staleness review via qmd | Must | Done | Queries qmd with stale/risky keywords; streams results with "proposal-only" label; no file writes. Per §7.1 `pke stale`. | P1-03 |
| P4-02 | Implement template compliance checking (7-section validation) | Must | Done | `pke status` scans wiki pages for all 7 required sections; reports compliant/non-compliant counts and missing pages. Per §5.1 Capability 2. | P1-02 |
| P4-03 | Implement confidence levels in proposals | Must | Done | Proposals include `confidence` field (medium when target known, low otherwise). Per §10.1 Phase 4. | P3-04 |
| P4-04 | Enforce proposal-only mode (no code path writes wiki without `pke apply`) | Must | Done | All compile/propose/daily/learn commands are proposal-only; only `pke apply` writes wiki. Per ADR-01. | P3-05 |
| P4-05 | Implement conflict detection in wiki section diffs | Must | Done | `conclusion_changed` events emitted when `Current Understanding` has both additions and removals; `conflict_detected` for Conflicts section changes. Per §5.3 Workflow E. | P5-01 |
| P4-06 | Add time-based confidence degradation for wiki pages | Should | Todo | Pages not reviewed in 30+ days auto-flagged; confidence auto-degrades. Per R-13 mitigation, planned for Phase 4. | P4-02 |

### Phase Exit Criteria
- [x] `pke stale` reviews staleness of any topic
- [x] Template compliance checking in `pke status`
- [x] Quality scoring (confidence levels) in proposals
- [x] Update permission gates enforced (proposal-only)
- [x] Conflict detection in wiki section diffs
- [ ] Template compliance >= 80%

---

## Phase 5: Monitoring & Analytics (Week 10–12)

**Purpose:** Continuous vault observation, event classification, and knowledge health reporting.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P5-01 | Implement `pke monitor` one-shot scan with event generation | Must | Done | Scans vault; diffs against previous snapshot; classifies events semantically; appends to `events.jsonl`; writes markdown report. Per US-06, §7.1 `pke monitor`. | P1-05 |
| P5-02 | Implement `pke monitor --watch --path` for scoped realtime monitoring | Must | Done | Requires `--path`; polls at configurable interval; prints timestamped summaries; Ctrl-C to stop. Per US-06, §7.1 `pke monitor`. | P5-01 |
| P5-03 | Implement `pke events` to browse the knowledge event log | Must | Done | Reads `events.jsonl`; returns last N events (default 20); `--limit` and `--json` supported. Per §7.1 `pke events`. | P5-01 |
| P5-04 | Implement `pke report latest\|today` for monitor report viewing | Must | Done | Lists markdown reports; `latest` selects most recent; `today` filters by date. Per §7.1 `pke report`. | P5-01 |
| P5-05 | Implement `pke dashboard` with web-based knowledge health UI | Must | Done | HTTP server with `/api/dashboard`, `/api/scan`, `/api/propose`, `/api/apply`, `/api/reject`; metrics, event filtering, proposal approve/reject from browser. Per US-09, §7.1 `pke dashboard`. | P5-01, P3-04 |
| P5-06 | Implement section-level semantic event classification | Must | Done | Events classified by wiki section: `conclusion_added`, `conflict_detected`, `stale_claim_detected`, `open_question_added`, `evidence_added`, `evidence_link_added`, `conclusion_changed`, `knowledge_section_updated`. Per §5.3 Workflow E. | P5-01 |
| P5-07 | Implement scoped monitoring with `--path` (no false removal reports) | Must | Done | Scoped scan preserves out-of-scope state; `--path wiki/` doesn't report `raw/` removals. Per US-06. | P5-01 |
| P5-08 | Enforce file size limit (10 MB max, skip with warning) | Should | Done | Files > 10 MB skipped during vault scan with warning logged. Per §8.2 Scalability. | P5-01 |
| P5-09 | Implement event log rotation (100,000 event cap) | Should | Done | When `events.jsonl` exceeds 100,000 lines, oldest events archived to a dated backup file. Per §8.2. | P5-03 |
| P5-10 | Implement proposal limit enforcement (200 pending cap) | Should | Done | Warn when pending proposals exceed 200; auto-flag oldest for review. Per §8.2. | P3-07 |
| P5-11 | Implement report retention policy (90-day archival) | Should | Done | Reports older than 90 days moved to archive directory or deleted. Per §8.2. | P5-04 |
| P5-12 | Implement candidates queue cap (100 candidates, 30-day expiry) | Should | Done | Oldest candidates auto-expire after 30 days; queue capped at 100. Per §8.2. | P3-03 |
| P5-13 | Add `--sensitivity` parameter for staleness detection tuning | Could | Done | `pke stale --sensitivity <low\|medium\|high>` adjusts staleness heuristic thresholds. Per R-07 mitigation. | P4-01 |

### Phase Exit Criteria
- [x] `pke monitor` running reliably in one-shot and watch mode
- [x] Dashboard showing health metrics
- [x] All events classified correctly by semantic type
- [ ] Scalability limits enforced (file size, event rotation, proposal cap, report retention)
- [ ] Monitor reliable for 2+ weeks continuous use

---

## Phase 6: Self-Improvement (Week 13–14)

**Purpose:** PKE learns from usage patterns to improve retrieval and compilation quality.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P6-01 | Implement retrieval tuning proposals based on query patterns | Must | Done | Analyze event log for low-quality query results; generate proposals to add/improve wiki pages for frequently queried topics. Per §10.1 Phase 6. | P5-03 |
| P6-02 | Implement compile strategy refinement from acceptance/rejection history | Must | Done | Track proposal acceptance rate over time; adjust confidence scoring and candidate ranking based on historical patterns. Per §10.1 Phase 6. | P3-07, P5-03 |
| P6-03 | Implement usage pattern analysis from event logs | Must | Done | Aggregate query patterns, compile frequencies, and approval rates from `events.jsonl`; surface insights via `pke report` or dashboard. Per §10.1 Phase 6. | P5-03 |
| P6-04 | Implement rate-limiting for proposals (max 5 per daily compilation) | Should | Done | `pke daily` generates at most 5 proposals per run; prioritizes by confidence and evidence strength. Per R-03 mitigation. | P2-01, P3-04 |
| P6-05 | Implement fast-path approval for high-confidence append-only proposals | Could | Done | High-confidence proposals for safe sections (Evidence, Open Questions) can be batch-approved with reduced friction. Per R-04 mitigation, OQ-1. | P3-05 |

### Phase Exit Criteria
- [x] At least one approved self-improvement proposal applied
- [x] Retrieval tuning demonstrated with measurable improvement
- [x] Self-improvement proposals subject to same approval gates

---

## Phase 7: Session Intelligence (Week 15–16)

**Purpose:** Automatic session boundary detection and session-scoped knowledge capture.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P7-01 | Improve `pke close-session` signal detection beyond keyword matching | Must | Todo | Use NLP-based or heuristic detection (time gaps, topic shifts, argument structure) instead of simple regex; detect durable conclusions with >= 80% accuracy. Per §10.1 Phase 7. | None |
| P7-02 | Implement heuristic session boundary detection | Must | Todo | Detect session boundaries from timestamps, topic shifts, and activity gaps in transcripts. Per §10.1 Phase 7. | P7-01 |
| P7-03 | Integrate session-derived signals into compile pipeline | Must | Todo | Durable signals from `close-session` automatically become compile candidates; proposals generated for strong signals. Per §10.1 Phase 7. | P7-01, P3-03 |
| P7-04 | Add session metadata tracking (duration, topics, outcome) | Should | Todo | Each `close-session` run records session metadata in `events.jsonl` for usage analysis. Per §9.3 session capture rate metric. | P7-01 |

### Phase Exit Criteria
- [ ] Session boundaries detected with >= 80% accuracy
- [ ] `pke close-session` producing useful compile candidates
- [ ] Session-based learning integrated with compile pipeline

---

## Phase 8: Multi-Source Adapters (Week 17–20)

**Purpose:** Extend capture beyond local files to external knowledge sources.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P8-01 | Define adapter interface (input format, metadata schema, output to `raw/`) | Must | Todo | Interface documented with required fields: source type, metadata format, output path pattern, scheduling config. Per §10.1 Phase 8. | None |
| P8-02 | Implement adapter configuration in `.pke/adapters.json` | Must | Todo | Adapters configured via JSON with source, schedule, and output path; validated on load. Per §10.1 Phase 8. | P8-01 |
| P8-03 | Implement first adapter (DingTalk export, browser bookmarks, or clipboard) | Must | Todo | At least one adapter reliably feeds external content into `$PKE_VAULT/raw/` with proper metadata. Per §10.1 Phase 8. | P8-01, P8-02 |
| P8-04 | Implement automated capture scheduling for adapter sources | Should | Todo | Adapters run on configurable schedule (cron-like or interval-based); results captured automatically. Per §10.1 Phase 8. | P8-02, P8-03 |

### Phase Exit Criteria
- [ ] Adapter interface defined and documented
- [ ] At least one external source reliably feeding into `raw/`
- [ ] Adapter configuration in `.pke/adapters.json`

---

## Phase 9: Collaboration & Sharing (Week 21–24)

**Purpose:** Optional, selective knowledge sharing with trusted collaborators.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P9-01 | Implement Markdown bundle export format | Must | Todo | Wiki pages exportable as a self-contained Markdown bundle with metadata and evidence links preserved. Per §10.1 Phase 9. | None |
| P9-02 | Implement JSON knowledge graph export | Must | Todo | Export wiki pages + relationships as a JSON graph for programmatic consumption. Per §10.1 Phase 9. | None |
| P9-03 | Implement selective page sharing (allowlist-based) | Must | Todo | User specifies which pages to share via allowlist; excluded pages never exposed. Per §10.1 Phase 9. | P9-01 |
| P9-04 | Implement import and merge from external PKE instances | Must | Todo | Import external PKE export; merge into local vault with conflict detection. Per §10.1 Phase 9. | P9-01 |
| P9-05 | Implement merge conflict resolution for shared pages | Must | Todo | Conflicting edits to shared pages detected; user chooses resolution strategy (keep mine, keep theirs, merge). Per §10.1 Phase 9. | P9-04 |

### Phase Exit Criteria
- [ ] Knowledge exportable in Markdown and JSON formats
- [ ] Selective sharing via allowlist operational
- [ ] Import and merge working without data corruption
- [ ] Merge conflicts handled gracefully

---

## Phase 10: Platform Integration (Week 25+)

**Purpose:** Deep integration with development tools for real-time knowledge augmentation.

### Backlog Items

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies |
|----|------|----------|--------|---------------------|-------------|
| P10-01 | Define IDE plugin interface (Qoder, Cursor, VS Code) | Must | Todo | Interface spec covers: activation triggers, query API, suggestion display, and knowledge context injection. Per §10.1 Phase 10. | None |
| P10-02 | Implement context-aware `pke use` invocation from editor | Must | Todo | Editor plugin calls `pke use` with cursor context; results displayed inline or in panel; latency < 2s. Per §10.1 Phase 10. | P10-01 |
| P10-03 | Implement real-time knowledge suggestions during coding/writing | Should | Todo | Plugin surfaces relevant wiki content as the user types or navigates code. Per §10.1 Phase 10. | P10-01, P10-02 |
| P10-04 | Implement bi-directional sync between IDE sessions and PKE vault | Should | Todo | IDE session activity feeds back to PKE as events; PKE knowledge available in IDE context. Per §10.1 Phase 10. | P10-02 |

### Phase Exit Criteria
- [ ] PKE suggestions appearing in at least one IDE workflow
- [ ] Latency < 2s for in-editor queries
- [ ] IDE plugin interface documented

---

## Cross-Cutting Concerns

Items that span multiple phases and should be addressed incrementally.

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies | Target Phase |
|----|------|----------|--------|---------------------|-------------|-------------|
| CC-01 | Replace hardcoded vault path with `$PKE_VAULT` env variable support | Must | Done | `pke.mjs` reads `PKE_VAULT` env var; falls back to `--vault` flag; falls back to `~/MyKnowledge`. Current code hardcodes `/Users/lizhentao/MyKnowledge`. Per §7.4. | None | Phase 1 (overdue) |
| CC-02 | Replace hardcoded qmd PATH with configurable discovery | Should | Done | qmd path discovery reads from env or config instead of hardcoding `/opt/homebrew/bin`. Per §7.4. | None | Phase 1 (overdue) |
| CC-03 | Add `--json` support to `pke stale` | Should | Todo | `pke stale` outputs structured JSON when `--json` is passed. Per §7.2 (currently noted as unsupported). | P4-01 | Phase 4 |
| CC-04 | Implement automated success metric collection via `--json` output | Should | Todo | Metrics from §9.1–9.3 collected automatically via JSON output piped to event logs. Per §9.4. | P5-03 | Phase 5 |
| CC-05 | Add `--since` and `--type` filters to `pke events` | Should | Todo | `pke events --since 2026-05-01 --type conflict_detected` filters events by date and type. Per §7.1 `pke events`. | P5-03 | Phase 5 |
| CC-06 | Implement 50-query benchmark suite for retrieval quality measurement | Should | Todo | Benchmark file maintained in `raw/`; run monthly; results scored 1–5. Per §9.4. | P2-02 | Phase 3 |
| CC-07 | Standardize error messages with actionable next-step guidance | Should | Todo | All error messages include what went wrong, why, and what command to run next. Per §7.3, §9.3 error recovery metric. | P1-08 | Ongoing |
| CC-08 | Add `pke init` command for vault initialization | Could | Todo | `pke init [path]` creates vault structure (`raw/`, `wiki/`, `.pke/`) and initial `state.json`. Per §10.1 Phase 1 deliverables. | None | Phase 1 (overdue) |

---

## Technical Debt

Items identified from the validation checklist, implementation review, and NFR gaps.

| ID | Item | Priority | Status | Acceptance Criteria | Dependencies | Target Phase |
|----|------|----------|--------|---------------------|-------------|-------------|
| TD-01 | Implement atomic write pattern (write-to-temp + rename) for `pke apply` | Must | Todo | `applyProposal` writes to temp file then renames; prevents partial writes on interrupt. Per §8.3 Reliability. | P3-05 | Phase 4 |
| TD-02 | Add file locking or concurrent invocation guard | Should | Todo | Warn if another `pke` process is running; prevent state corruption from concurrent access. Per §8.3 (currently: "not supported"). | None | Phase 5 |
| TD-03 | Implement vault scan performance optimization for large vaults | Should | Todo | `pke changed`/`pke daily` scan completes in < 10s for 50,000 files; consider incremental hashing. Per §8.1 Performance targets. | P1-05 | Phase 5 |
| TD-04 | Add non-Markdown file type support (`.txt`, `.markdown` already supported; consider PDF/image metadata) | Could | Todo | Vault scan handles additional file types or defers to adapters. Per OQ-8. | None | Phase 8 |
| TD-05 | Implement wiki page size limit and auto-split recommendation | Could | Todo | Warn when wiki pages exceed a configurable threshold; suggest splitting. Per OQ-3. | None | Phase 5 |
| TD-06 | Implement conflicting proposal detection for same target page | Should | Todo | Warn when multiple pending proposals target the same wiki page; suggest resolution. Per OQ-4. | P3-07 | Phase 4 |
| TD-07 | Add proposal expiry policy (stale proposals auto-flagged) | Should | Todo | Proposals older than configurable threshold flagged or auto-expired. Per OQ-6. | P3-07 | Phase 5 |
| TD-08 | Implement `pke capture` event recording for future compilation tracking | Should | Todo | Each capture writes an event to `events.jsonl` for capture-to-compile conversion tracking. Per §9.2 capture-to-compile metric. | P1-04, P5-01 | Phase 5 |

---

## Prioritization Notes

### How to Read This Backlog

1. **Work phase-by-phase in order.** Phases 1–5 are sequential. Phases 6 and 7 can run in parallel after Phase 5. Phase 8 requires both 6 and 7. See §10.2 Phase Dependencies.

2. **Within a phase, complete "Must" items before "Should", and "Should" before "Could."** MoSCoW priority indicates relative importance within each phase.

3. **Phase exit criteria must ALL pass before advancing.** See §9.5 Launch Readiness Criteria and §10.4 Go/No-Go Criteria for formal gates.

4. **Cross-cutting concerns and technical debt** can be addressed alongside their target phase or as capacity allows. Items marked "overdue" (CC-01, CC-02, CC-08) should be prioritized in the next available cycle.

5. **Reference PRD sections for full specifications.** Each backlog item includes cross-references (e.g., "See §7.1 `pke use`" or "Per US-03"). Consult `docs/prd.md` for complete requirements.

6. **Status is based on `pke.mjs` implementation as of 2026-05-06.** "Done" means the feature exists and works as specified. "In Progress" means partial implementation. "Todo" means not yet started.

### Current Priority

Phase 6 (Self-Improvement) is now complete. The immediate priority is Phase 7 (Session Intelligence) and addressing remaining cross-cutting concerns and technical debt. Phases 7 and 8 can proceed per the dependency graph in §10.2.
