"""Use stage — qmd query → memory injection into LLM prompt.

On each incoming message:
1. Build semantic query from user message + recent context
2. qmd query against user_{elder_id} collection
3. Return Top-5 results above relevance threshold (0.7)
4. Timeout at 250ms — skip gracefully if slow
5. Format results for prompt injection
"""
