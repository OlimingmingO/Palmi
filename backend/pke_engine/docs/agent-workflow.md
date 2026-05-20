---
status: current
confidence: medium
last_reviewed: 2026-05-03
page_type: workflow
engine_layer: agent
source_count: 3
---

# Personal Knowledge Engine Workflows

## Current Understanding

This page is the operating manual for the Personal Knowledge Engine agent. It turns the Phase 2 knowledge schema into Phase 3 behavior.

## Key Principles

- Needs synthesis into durable principles; original content is preserved below.

## Evidence

- Original page content is preserved below for provenance.

## Conflicts / Evolution

- Not yet reviewed for contradictions or evolution across sources.

## Stale Or Risky Claims

- Not yet reviewed for stale or time-sensitive claims.

## Open Questions

- What current conclusion should this page preserve?
- Which evidence would change the current understanding?

## Related Pages

- [[personal-knowledge-engine]]
- [[knowledge-page-template]]
- [[personal-clusters-hub]]
- [[ai-llm-research]]
- [[strategy-research]]
- [[qoderwork商业化思考]]

## Original Content

## Current Understanding

This page is the operating manual for the Personal Knowledge Engine agent. It turns the Phase 2 knowledge schema into Phase 3 behavior.

The agent's job is not only to answer questions. Its job is to search, read, synthesize, decide whether new reusable knowledge was created, and then update the wiki so the knowledge base compounds over time.

## Agent Contract

The agent should use the Personal Knowledge Engine automatically when the user's request touches their notes, wiki, knowledge base, QoderWork, AI/LLM strategy, product/business thinking, decisions, stale assumptions, contradictions, or reusable knowledge.

The user should not need to explicitly say "Use my Personal Knowledge Engine." If the request is probably knowledge-base-related, the agent should silently activate the engine, retrieve context, and answer from the knowledge layer. Mention activation only when useful for transparency.

When operating, the agent should treat the system as four layers:

```text
raw notes = evidence and memory traces
wiki pages = synthesized living knowledge
qmd index + embeddings = retrieval and recall
agent workflow = behavior that reads, reasons, writes, updates
```

The agent should prefer upgraded wiki pages for current understanding, then inspect raw notes as evidence. If wiki pages and raw notes conflict, the agent should expose the conflict instead of silently choosing one.

## Update Governance

The engine must protect the distinction between evidence and knowledge.

Raw files should rarely be updated. They are evidence records: what was seen, thought, copied, discussed, or saved at a point in time. The agent should not rewrite raw notes to make them correct, current, or more elegant.

Raw files may be updated only for:

- new raw-note ingestion requested by the user
- mechanical repair such as encoding, malformed Markdown, duplicate frontmatter, broken resource paths, or missing metadata
- append-only processing notes that preserve the original content

Wiki files are curated knowledge, but they should not be updated opportunistically. A wiki update requires a definite update clue:

- the user explicitly asks to update, save, write, revise, ingest, upgrade, or consolidate the wiki
- the user explicitly approves a proposed wiki update
- the user asks to close/end/summarize a session and update the wiki from the chat history
- a scheduled or explicit review workflow is running, such as daily compilation or staleness review

Without a definite update clue, the agent should answer normally and may propose what could be updated, but must not write to the wiki.

## Common Commands

Use Homebrew Node so qmd uses the correct runtime:

```bash
PATH=/opt/homebrew/bin:$PATH qmd status
PATH=/opt/homebrew/bin:$PATH qmd query "topic" -c myknowledge -n 8
PATH=/opt/homebrew/bin:$PATH qmd search "exact terms" -c myknowledge -n 8
PATH=/opt/homebrew/bin:$PATH qmd get qmd://myknowledge/wiki/page.md
PATH=/opt/homebrew/bin:$PATH qmd update
PATH=/opt/homebrew/bin:$PATH qmd embed -c myknowledge
PATH=/opt/homebrew/bin:$PATH qmd wiki lint
```

## Research Mode

Use when the user asks a topic question.

### Trigger

```text
Any topic question where the user's accumulated knowledge may matter.

Examples:
- QoderWork 第一批目标用户应该是谁？
- 我过去关于企业服务和 AI 的判断是什么？
- 帮我写一个产品战略 memo。
- 这个想法和我之前的笔记冲突吗？
```

### Behavior

1. Search wiki and raw notes with `qmd query`.
2. Read the most relevant wiki pages first.
3. Read raw notes as evidence.
4. Produce an answer with:
   - current understanding
   - evidence
   - conflicts or evolution
   - stale/risky claims
   - open questions
5. If the answer creates reusable knowledge, propose a wiki update. Apply it only when there is a definite update clue.

## Upgrade Mode

Use when a page is thin, mechanical, or only a summary.

### Trigger

```text
Any request to improve, clean, rewrite, strengthen, review, or make a wiki page more useful.

Examples:
- 这个页面太薄了，帮我改好。
- 整理 saas-business-model。
- 把这篇变成真正的知识页。
```

### Behavior

1. Read the target page.
2. Find linked raw notes and related pages.
3. Rewrite using:
   - Current Understanding
   - Key Principles
   - Evidence
   - Conflicts / Evolution
   - Stale Or Risky Claims
   - Open Questions
   - Related Pages
4. Preserve useful links.
5. Mark weak evidence explicitly.
6. Run `qmd update` and `qmd embed -c myknowledge` after the user asks for or approves the upgrade.

## Ingest Mode

Use when adding a new note, meeting record, article, transcript, or idea.

### Trigger

```text
Any new note, meeting record, article, transcript, feedback, chat excerpt, or idea that should become part of the knowledge base.

Examples:
- 这是今天的会议记录，整理一下。
- 这段用户反馈有什么知识值得沉淀？
- 把这篇文章放进我的知识系统。
```

### Behavior

1. Classify the input.
2. Extract durable claims, evidence, decisions, contradictions, stale facts, and open questions.
3. Search for related wiki pages.
4. Decide one of:
   - update an existing page
   - create a new knowledge page
   - leave as raw evidence only
5. Update only when the ingestion itself was requested or the user approves the update.
6. Reindex and re-embed if pages changed.

## Decision Mode

Use when the user needs judgment.

### Trigger

```text
Any decision or tradeoff question in a domain covered by the vault.

Examples:
- QoderWork 应该先做企业还是一人公司？
- 这个方向值得投入吗？
- 这几个方案怎么选？
```

### Behavior

1. Pull current thesis pages and raw evidence.
2. Compare options.
3. Separate:
   - known evidence
   - assumptions
   - risks
   - unknowns
   - reversible decisions
4. Recommend a direction.
5. Propose updates to the relevant thesis page if the decision becomes durable knowledge. Apply only when the user asks for or approves the update.

## Staleness Review Mode

Use to keep the wiki honest.

### Trigger

```text
Any request asking whether a claim, page, thesis, or old note is still reliable.

Examples:
- 这个判断还成立吗？
- 找出这里过时的假设。
- 这篇 wiki 有哪些风险？
```

### Behavior

1. Find related wiki pages.
2. Review `Stale Or Risky Claims`.
3. Mark outdated, unverified, or time-sensitive claims.
4. Create verification questions.
5. Update page status/confidence only when the review was explicitly requested or approved.

## Daily Compilation Mode

Use for maintenance.

### Trigger

```text
Run daily knowledge compilation.
```

### Behavior

1. Find recently changed raw and wiki notes.
2. Cluster changes by topic.
3. Promote durable insights to wiki pages because daily compilation is an explicit update workflow.
4. Leave one-off information alone.
5. Report:
   - pages updated
   - stale claims found
   - open questions added
   - pages needing human review

## Update Rules

Propose wiki updates when the work produces:

- a durable thesis
- a reusable model
- a decision framework
- a changed belief
- a meaningful contradiction
- a stale/risky claim
- an open question worth tracking

Do not update the wiki for:

- one-off answers
- temporary command output
- weak speculation
- current facts that require web verification unless marked as stale/risky

Even when content is durable, do not write it unless a definite update clue is present.

## Related Pages

- [[personal-knowledge-engine]]
- [[knowledge-page-template]]
- [[personal-clusters-hub]]
- [[ai-llm-research]]
- [[strategy-research]]
- [[qoderwork商业化思考]]
