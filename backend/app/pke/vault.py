"""Per-user vault lifecycle management.

Responsibilities:
- Initialize vault on elder registration (create directories + qmd collection)
- Resolve vault path from elder_id
- Archive old raw files (beyond PKE_MAX_RAW_FILES)
- Vault health check and repair
"""
