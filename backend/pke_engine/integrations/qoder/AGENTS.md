# Personal Knowledge Engine Instructions

When working in `/Users/lizhentao/MyKnowledge`, automatically use the local Personal Knowledge Engine.

- Vault: `/Users/lizhentao/MyKnowledge`
- Wiki knowledge: `/Users/lizhentao/MyKnowledge/wiki`
- Raw evidence: `/Users/lizhentao/MyKnowledge/raw`
- CLI: `/Users/lizhentao/Documents/Codex/2026-05-03/i-ve-been-installed-https-github/personal-knowledge-engine-mvp/bin/pke`
- qmd collection: `myknowledge`

Before answering product, strategy, QoderWork, wiki, raw-note, stale-claim, conflict, or synthesis questions, query the vault:

```bash
PATH=/opt/homebrew/bin:$PATH qmd query "topic" -c myknowledge -n 8
```

After editing local knowledge files, run a scoped scan:

```bash
/Users/lizhentao/Documents/Codex/2026-05-03/i-ve-been-installed-https-github/personal-knowledge-engine-mvp/bin/pke monitor --path wiki/
```

Use `--path raw/` for raw-note edits or a specific file path when possible.

Governance:

- Raw files are evidence, not truth; rarely edit them.
- Wiki files are current synthesized knowledge.
- Do not silently promote raw notes into wiki conclusions.
- Wiki updates require explicit user intent or approval.
- Report what changed, what conflicts appeared, what claims may be stale, and what still needs review.

