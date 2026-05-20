---
name: personal-knowledge-engine
version: 0.1.0
description: Automatically use the local Personal Knowledge Engine when working with /Users/lizhentao/MyKnowledge, QoderWork strategy, product/business decisions, wiki pages, raw notes, stale/conflicting knowledge, or reusable synthesis.
description_zh: 当处理 MyKnowledge、QoderWork、产品/商业决策、wiki、raw notes、过时/冲突知识或可复用结论时，自动使用本地 Personal Knowledge Engine。
category: knowledge-management
recommended: true
---

# Personal Knowledge Engine

Use this skill automatically when a request may benefit from the user's local knowledge vault.

## Local System

- Vault: `/Users/lizhentao/MyKnowledge`
- Wiki: `/Users/lizhentao/MyKnowledge/wiki`
- Raw notes: `/Users/lizhentao/MyKnowledge/raw`
- PKE CLI: `/Users/lizhentao/Documents/Codex/2026-05-03/i-ve-been-installed-https-github/personal-knowledge-engine-mvp/bin/pke`
- qmd collection: `myknowledge`

Use Homebrew qmd:

```bash
PATH=/opt/homebrew/bin:$PATH qmd query "topic" -c myknowledge -n 8
```

## Auto-Use Rules

Use PKE without waiting for the user to say "use my knowledge engine" when the task touches:

- `/Users/lizhentao/MyKnowledge`
- wiki pages, raw notes, local knowledge, memory, stale claims, conflicts, or open questions
- QoderWork, product strategy, business model, enterprise AI, connectors, or agent workflows
- a document or decision that should reuse the user's accumulated thinking

## Work Loop

1. Read relevant wiki pages first when they exist.
2. Use `qmd query` for semantic discovery.
3. Treat raw notes as evidence, not truth.
4. Separate current understanding, evidence, conflicts, stale/risky claims, and open questions.
5. Do not silently rewrite wiki pages unless the user explicitly asked to edit/update/write/compile.
6. After editing MyKnowledge files, run a scoped monitor scan:

```bash
/Users/lizhentao/Documents/Codex/2026-05-03/i-ve-been-installed-https-github/personal-knowledge-engine-mvp/bin/pke monitor --path wiki/
```

Use `--path raw/` if raw evidence was touched, or a specific file path when possible.

## Governance

- Raw files are evidence records and should rarely be edited.
- Wiki files are synthesized knowledge.
- Durable conclusions should become proposals first unless the user explicitly approved the update.
- Report changed files, conflicts, stale claims, newly added conclusions, and unresolved questions after knowledge work.

