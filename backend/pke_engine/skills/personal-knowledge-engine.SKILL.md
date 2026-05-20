---
name: personal-knowledge-engine
description: Automatically use for any request that may benefit from the user's MyKnowledge vault, personal notes, LLM Wiki, MinerU/qmd index, QoderWork knowledge, business/product/strategy research, decisions, stale-assumption review, wiki page improvement, note ingestion, or synthesis of the user's accumulated knowledge. Trigger even when the user does not explicitly say "use Personal Knowledge Engine"; stay silent about activation unless useful. Do not use for generic coding, casual chat, or questions unrelated to the user's knowledge base.
---

# Personal Knowledge Engine Agent

## Auto-Activation Policy

Use this skill automatically when the user asks about:

- their notes, wiki, vault, memory, knowledge base, or second brain
- QoderWork, AI/LLM strategy, business model, product thinking, enterprise AI, SaaS, connectors, or agent workflows
- a decision where their past thinking or notes may matter
- stale assumptions, contradictions, current thesis, evidence, or open questions
- upgrading, ingesting, reviewing, or synthesizing knowledge
- writing a memo, strategy, plan, thesis, or reflection that should draw from their accumulated knowledge

Do not require the user to say "Use my Personal Knowledge Engine." When triggered, operate quietly and just do the work. Mention that the engine was used only in the final summary or when the user needs to know what sources were consulted.

Do not use this skill for unrelated generic questions, pure coding tasks, filesystem tasks, or casual conversation unless the user asks to connect the answer to their knowledge base.

## Mission

Operate the user's Personal Knowledge Engine as a compounding knowledge system:

- raw notes are evidence, not truth
- wiki pages are synthesized, living knowledge
- answers should improve the wiki when they create reusable knowledge
- conflicts, stale claims, and uncertainty must be visible

## Local System

- Vault: `/Users/lizhentao/MyKnowledge`
- Wiki: `/Users/lizhentao/MyKnowledge/wiki`
- Raw notes: `/Users/lizhentao/MyKnowledge/raw`
- Main pages:
  - `/Users/lizhentao/MyKnowledge/wiki/personal-knowledge-engine.md`
  - `/Users/lizhentao/MyKnowledge/wiki/knowledge-page-template.md`
  - `/Users/lizhentao/MyKnowledge/wiki/personal-knowledge-engine-workflows.md`
  - `/Users/lizhentao/MyKnowledge/wiki/personal-clusters-hub.md`

Use Homebrew Node for qmd:

```bash
PATH=/opt/homebrew/bin:$PATH qmd status
```

## Operating Loop

For all PKE work:

1. Read the relevant wiki page first when one exists.
2. Use `qmd query` for semantic discovery and `qmd search` for exact terms.
3. Read raw notes only as evidence; do not treat them as final truth.
4. Separate current understanding, evidence, conflicts, stale/risky claims, and open questions.
5. Do not update wiki pages unless there is a definite update clue.
6. Run `qmd update` and `qmd embed -c myknowledge` after approved wiki edits.
7. Run `qmd wiki lint` when link structure matters.
8. Summarize what changed and what remains unresolved.
9. Every compile run must include a change report: files changed by this run, files changed since baseline, knowledge writes, evidence writes, and remaining unresolved items.
10. Use monitor reports/events when the user asks what changed inside the knowledge engine.

## Update Governance

Raw files should rarely be updated. Treat raw files as evidence records. Do not rewrite raw notes to make them cleaner, more current, or more correct. Only update raw files for:

- new raw-note ingestion requested by the user
- mechanical repair such as encoding, broken markdown, duplicate frontmatter, or missing metadata
- append-only processing notes that preserve the original content

Wiki files should not be updated merely because an answer produced an interesting idea. A wiki update requires a definite update clue:

- the user explicitly asks to update, save, write, revise, ingest, upgrade, or consolidate the wiki
- the user explicitly approves a proposed wiki update
- the user asks to close/end/summarize a session and update the wiki from the chat history
- a scheduled or explicit review workflow is running, such as daily compilation or staleness review

Without a definite update clue, answer normally and optionally say what could be updated, but do not write to the wiki.

## Modes

### Research Mode

Default mode for topic questions that touch the user's knowledge domains. Produce an answer grounded in current wiki synthesis plus raw evidence.

Steps:

1. Query the topic.
2. Read top wiki pages and source notes.
3. Identify current thesis, evidence, conflicts, stale claims, open questions.
4. Answer the user.
5. Propose wiki updates if reusable knowledge was created. Apply them only when there is a definite update clue.

### Upgrade Mode

Use when the user mentions a weak page, asks to improve a page, or a page retrieved during work is clearly thin and the answer creates reusable knowledge.

Steps:

1. Read the page.
2. Find linked raw notes and related pages.
3. Rewrite into the knowledge page standard.
4. Preserve useful links.
5. Mark weak evidence honestly.
6. Reindex and re-embed after the user asks for or approves the upgrade.

### Ingest Mode

Use when the user provides or points to a new note, meeting, article, transcript, file, idea, feedback, chat record, or process information.

Steps:

1. Classify the input.
2. Extract claims, decisions, evidence, contradictions, stale facts, and open questions.
3. Search for related wiki pages.
4. Decide whether to update existing pages, create a new page, or leave as raw evidence.
5. Update only when the ingestion itself was requested or the user approves the update.

### Decision Mode

Use when the user asks for judgment, prioritization, tradeoffs, or "what should I do" in a domain covered by the vault.

Steps:

1. Pull current thesis pages and raw evidence.
2. Compare options.
3. Separate known evidence, assumptions, risks, unknowns, and reversible decisions.
4. Recommend a direction.
5. Propose thesis-page updates if the decision becomes durable knowledge. Apply only when the user asks for or approves the update.

### Staleness Review Mode

Use when the user asks whether something is still true, current, reliable, conflicting, or risky.

Steps:

1. Find related pages.
2. Review `Stale Or Risky Claims`.
3. Mark outdated or unverified claims.
4. Create verification questions.
5. Update status/confidence metadata only when the review was explicitly requested or approved.

### Daily Compilation Mode

Use for periodic maintenance.

Steps:

1. Find recently changed raw and wiki notes.
2. Cluster them by topic.
3. Promote durable insights because daily compilation is an explicit update workflow.
4. Leave one-off information alone.
5. Report pages updated, stale claims found, and open questions.

### Knowledge Monitor Mode

Use when the user asks what changed, wants realtime monitoring, or asks for conflicts, stale claims, newly added conclusions, or recent knowledge-engine activity.

Steps:

1. Run `pke monitor` for a one-shot report, optionally scoped with `--path`.
2. Run `pke events` to inspect append-only event history.
3. Run `pke report latest` or `pke report today` for human-readable reports.
4. Run `pke dashboard` when the user asks for a visual dashboard. Use `pke dashboard --path <vault-relative-path> --auto-scan` when the dashboard should update after browser refresh for a specific folder or file.
5. For realtime monitoring, require `pke monitor --watch --path <vault-relative-path>`.
6. Do not monitor the entire vault in watch mode.
7. Treat monitor findings as observations; do not update wiki pages unless there is a definite update clue.

### Self-Improvement Mode

Use when the user asks the engine to improve itself, compile knowledge from monitor events, create proposals, or approve/reject knowledge updates.

Steps:

1. Use `pke candidates` to inspect monitor events that can trigger compile proposals.
2. Use `pke propose --event <id>` or `pke propose --path <file> --target <wiki-page>` to create an exact proposal.
3. Use `pke proposal <id>` to show the proposed patch.
4. Use `pke apply <id>` only after user approval.
5. Use `pke reject <id>` when the proposal should not be applied.
6. After apply, inspect the change report and qmd refresh result.
7. Never silently rewrite wiki pages from raw evidence.

## Update Rules

Propose wiki updates when the output contains:

- a durable thesis
- a reusable model
- a decision framework
- a changed belief
- a useful contradiction
- a stale/risky claim
- an open question worth tracking

Do not update the wiki for:

- one-off answers
- transient command output
- low-confidence speculation
- facts that require current web verification unless marked as stale/risky

Even when content is durable, do not write it unless a definite update clue is present.

## Page Standard

Knowledge pages should use:

- `Current Understanding`
- `Key Principles`
- `Evidence`
- `Conflicts / Evolution`
- `Stale Or Risky Claims`
- `Open Questions`
- `Related Pages`

Use frontmatter when creating or upgrading pages:

```yaml
---
status: draft
confidence: medium
last_reviewed: YYYY-MM-DD
page_type: thesis
engine_layer: knowledge
source_count: 0
---
```
