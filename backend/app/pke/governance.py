"""Governance — proposal-only wiki update control.

Prevents LLM hallucination from silently corrupting knowledge:
- All wiki modifications go through proposal stage
- Proposals include: source evidence, confidence score, change diff
- Auto-approve for high-confidence factual updates
- Flag for review: health-related claims, contradictions
"""
