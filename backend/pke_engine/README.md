# Personal Knowledge Engine MVP

Personal Knowledge Engine is a local-first knowledge workflow for turning raw personal information into governed, reusable knowledge.

The MVP focuses only on local files:

- raw evidence files
- wiki knowledge pages
- local AI drafts
- human-edited final documents
- local session transcripts
- MinerU Document Explorer / `qmd`
- a small `pke` CLI

The core product loop is:

```text
Capture evidence.
Compile knowledge.
Use knowledge naturally.
```

## Why This Exists

Raw notes are not truth. They can be stale, partial, duplicated, or contradictory. The wiki should contain judged knowledge: current understanding, principles, evidence, conflicts, stale claims, open questions, and related pages.

This MVP protects that distinction:

- raw files are evidence and are rarely edited
- wiki files are compiled knowledge
- semantic retrieval is used for discovery
- wiki writes require a definite update clue
- answers should expose uncertainty instead of hiding it

## Install

Requirements:

- Node.js
- `qmd` from MinerU Document Explorer
- a local vault with `raw/` and `wiki/` folders

Run directly:

```bash
./bin/pke help
```

Optional local link:

```bash
npm link
pke status
```

## Commands

```bash
pke status
pke use "question"
pke changed [--save]
pke daily [--save]
pke learn draft.md final.md
pke capture path/to/source.md [--write]
pke compile "topic or page"
pke close-session transcript.md
pke stale "topic or page"
pke monitor [--path wiki/]
pke monitor --watch --path wiki/
pke events [--limit 20]
pke report latest|today
pke dashboard [--port 8787] [--path raw/] [--auto-scan]
pke candidates
pke propose --path raw/note.md [--target wiki/page.md]
pke propose --event event-id [--target wiki/page.md]
pke proposals
pke proposal proposal-id
pke apply proposal-id
pke reject proposal-id
```

## Governance

Wiki writes are intentionally conservative.

A wiki update requires one of:

- explicit user command to update, save, write, revise, ingest, upgrade, or compile
- explicit approval of a proposed update
- session close summary with update permission
- scheduled or explicit daily compilation / staleness review

Without that clue, the engine should answer or propose. It should not silently write knowledge.

## Documentation

- [PRD](docs/prd.md)
- [Agent Workflow](docs/agent-workflow.md)
- [Codex Skill](skills/personal-knowledge-engine.SKILL.md)

## Current MVP Status

Implemented:

- local qmd retrieval through `pke use`
- changed-file baseline through `pke changed`
- proposal-only daily review through `pke daily`
- draft-final learning proposal through `pke learn`
- capture preview / evidence copy through `pke capture`
- proposal-only compile with an explicit change report
- proposal-only stale review command
- knowledge monitor event log through `pke monitor`
- section-level semantic detection for conclusions, conflicts, stale claims, evidence, and open questions
- scoped realtime monitoring through `pke monitor --watch --path <vault-relative-path>`
- monitor history through `pke events` and markdown reports through `pke report`
- local browser dashboard through `pke dashboard`
- controlled self-improvement through candidates, proposals, approval, apply, and reject
- Codex skill instructions for automatic Personal Knowledge Engine use

Not implemented yet:

- automatic wiki writing
- DingTalk connector
- Qoder/QoderWork native plugin
- Cursor or Anthropic CoWork integrations
- background daemon/service installation

## Knowledge Monitor

The monitor makes knowledge changes observable.

One-shot monitor:

```bash
pke monitor
pke monitor --path wiki/qoderwork商业化思考.md
```

Scoped realtime monitor:

```bash
pke monitor --watch --path wiki/
```

Watch mode requires `--path` and the path must stay inside the configured vault. The current implementation uses scoped polling so it works consistently across local environments without watching the whole vault.

Monitor artifacts:

```text
.pke/events.jsonl
.pke/monitor-state.json
.pke/reports/
```

Detected event types include:

```text
raw_added
raw_modified
wiki_added
wiki_modified
conclusion_added
conclusion_changed
conflict_detected
stale_claim_detected
open_question_added
evidence_link_added
knowledge_section_updated
```

Local dashboard:

```bash
pke dashboard --port 8787
```

The dashboard shows monitor totals, recent events, conflicts, stale claims, open questions, conclusions, and recent reports. It reads local `.pke` monitor artifacts and refreshes automatically.

By default, the dashboard is a viewer plus a manual scanner. Use **Scan Now** in the browser to run a monitor scan. If you want browser refresh to scan a specific folder/file, start it with a scoped path:

```bash
pke dashboard --path raw/ --auto-scan
```

## Controlled Self-Improvement

The engine can now create approved, append-only wiki improvements from monitor events.

```bash
pke candidates
pke propose --path raw/【ChatGPT专题】.md --target wiki/ai-llm-research.md
pke proposals
pke proposal proposal-id
pke apply proposal-id
pke reject proposal-id
```

Self-improvement is approval-gated:

```text
monitor event
-> compile candidate
-> proposal with exact patch
-> user approval
-> append-only wiki patch
-> backup + audit record
-> qmd refresh attempt
```

The first patch strategy is conservative. It appends to safe sections such as `Evidence`, `Open Questions`, `Conflicts / Evolution`, or `Stale Or Risky Claims`. It does not rewrite `Current Understanding` from raw evidence without approval.
