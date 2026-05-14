"""Capture stage — conversation → raw/ evidence.

After each conversation turn:
1. Format conversation as structured Markdown
2. Write to /data/users/{elder_id}/raw/{date}_session_{id}.md
3. Index new file in qmd collection
"""
