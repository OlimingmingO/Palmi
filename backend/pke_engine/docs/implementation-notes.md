# Implementation Notes

## Local Defaults

The current MVP defaults are intentionally opinionated for the first local deployment:

- vault: `/Users/lizhentao/MyKnowledge`
- qmd collection: `myknowledge`
- state file: `/Users/lizhentao/MyKnowledge/.pke/state.json`
- qmd runtime path prefix: `/opt/homebrew/bin`

These can be overridden with:

```bash
pke --vault /path/to/vault --collection mycollection --state /path/to/state.json status
```

## Safety Model

The CLI can inspect and copy evidence files, but wiki writing remains proposal-only in this MVP. This prevents the common failure mode where an agent pollutes durable knowledge with temporary conversation output.

Every compile run must produce a change report. Even when the command is proposal-only, the user should see:

- files changed by this compile command
- files changed since the saved review baseline
- knowledge pages written
- evidence files written

For the current MVP, `pke compile` should normally report zero writes because it does not yet perform approved wiki updates.

## Expected Workflow

```bash
pke changed
pke daily
pke use "topic"
pke learn draft.md final.md
PATH=/opt/homebrew/bin:$PATH qmd update
PATH=/opt/homebrew/bin:$PATH qmd embed -c myknowledge
```

## Next Engineering Steps

- Move local defaults into a config file.
- Add structured JSON output for every command.
- Add tests for file scanning, diff classification, and compile-candidate detection.
- Add a write-approved compile command that produces exact patches.
- Add a daily review report file.

## Knowledge Monitor Implementation

The monitor is implemented as a local observability layer, not as a writer.

State and artifacts:

```text
.pke/monitor-state.json
.pke/events.jsonl
.pke/reports/
```

`pke monitor` scans the configured vault or a scoped `--path`, compares file hashes against the previous monitor snapshot, parses wiki sections, and emits structured events.

`pke monitor --watch --path <path>` requires a scoped path inside the vault. It uses scoped polling rather than a broad filesystem watcher so it does not watch unrelated files and does not depend on platform-specific recursive watch behavior.

`pke dashboard --port 8787` starts a dependency-free local HTTP dashboard. It serves:

- `/` browser UI
- `/api/dashboard` JSON snapshot
- `/api/scan` scoped monitor scan

The dashboard reads `.pke/events.jsonl`, `.pke/monitor-state.json`, and `.pke/reports/`. It can also trigger a scoped scan through the **Scan Now** button. If started with `--path <vault-relative-path> --auto-scan`, each browser refresh/API refresh runs `pke monitor` for that scoped path. It must not auto-scan the entire vault unless the user explicitly chooses that scope.

## Controlled Self-Improvement Implementation

Self-improvement is implemented as an approval-gated proposal system.

Artifacts:

```text
.pke/proposals/
.pke/applied/
.pke/rejected/
.pke/backups/
```

Commands:

```bash
pke candidates
pke propose --path <source> --target <wiki-page>
pke propose --event <event-id> --target <wiki-page>
pke proposals
pke proposal <id>
pke apply <id>
pke reject <id>
```

Patch operations are append-only in this MVP. `pke apply` backs up the target wiki page, applies the patch, updates the proposal status, copies the applied record, and attempts `qmd update` plus `qmd embed -c <collection>`.

If qmd refresh fails, the wiki patch remains applied and the failure is recorded in the proposal change report.

Semantic classification is section-based:

- `Current Understanding` and `Key Principles` -> `conclusion_added`
- `Evidence` -> `evidence_added` or `evidence_link_added`
- `Conflicts / Evolution` -> `conflict_detected`
- `Stale Or Risky Claims` -> `stale_claim_detected`
- `Open Questions` -> `open_question_added`
- `Related Pages` or other knowledge sections -> `knowledge_section_updated`

Scoped monitoring preserves out-of-scope monitor state. For example, `pke monitor --path wiki/` must not report `raw/` files as removed.
