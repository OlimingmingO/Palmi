"""Memory Service — PKE (Personal Knowledge Engine) integration.

Responsibilities:
- Capture: Write conversation evidence to per-user raw/ vault
- Use: qmd query for Top-5 relevant memory injection before LLM call
- Compile: Orchestrate daily knowledge extraction (raw/ → wiki/)
- Governance: Enforce proposal-only wiki updates

Memory layers:
- Instant: Current session context (in-memory)
- Short-term: Recent conversations in raw/ directory
- Long-term: Compiled knowledge in wiki/ directory
- Emotional: Emotional markers in wiki pages
"""
