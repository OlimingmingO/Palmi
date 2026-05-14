"""Multi-tenant access validation middleware.

Enforces data isolation:
- Validates elder_id ownership for configurator requests
- Scopes all queries to the resolved tenant
- Rejects cross-tenant access attempts
"""
