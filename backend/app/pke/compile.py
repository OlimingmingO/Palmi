"""Compile stage — raw/ → wiki/ knowledge extraction.

Triggered daily at 03:00 via Hermes cron → Celery task:
1. Read recent raw/ files since last compile
2. LLM extraction: identify key facts, preferences, health updates
3. Generate wiki update proposals (proposal-only mode)
4. Apply approved proposals to wiki/ pages
5. Update qmd index for new/modified wiki pages
"""
