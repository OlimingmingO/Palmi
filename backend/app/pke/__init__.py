"""PKE (Personal Knowledge Engine) — self-built memory system.

Architecture: Capture → Compile → Use (three-stage loop)

Per-user vault structure:
    /data/users/{elder_id}/
    ├── raw/       ← Conversation evidence (auto-captured)
    ├── wiki/      ← Compiled knowledge (daily extraction)
    └── .pke/      ← Engine state (index, proposals)

Key design decisions:
- File-level isolation (one vault per elder)
- Governance: wiki updates require explicit trigger (proposal-only)
- qmd semantic search: Qwen Embedding v3, Top-5, threshold > 0.7
- 250ms query timeout (never block dialogue)
"""
