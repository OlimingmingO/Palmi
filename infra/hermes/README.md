# Hermes Agent Fork Files

This directory is the staging area for files forked from [Hermes Agent](https://github.com/OlimingmingO/hermes-agent).

## Setup Instructions

1. Clone the Hermes Agent repository:
   ```bash
   git clone https://github.com/OlimingmingO/hermes-agent.git /tmp/hermes-agent
   ```

2. Copy the required files into the Palmi backend:
   ```bash
   # Enterprise WeChat Gateway (65KB)
   cp /tmp/hermes-agent/gateway/platforms/wecom.py ../backend/app/gateway/wecom.py

   # Message Encryption (5KB)
   cp /tmp/hermes-agent/gateway/platforms/wecom_crypto.py ../backend/app/gateway/wecom_crypto.py

   # Cron Scheduler (77KB)
   cp /tmp/hermes-agent/cron/scheduler.py ../backend/app/cron/scheduler.py

   # Job Management (41KB)
   cp /tmp/hermes-agent/cron/jobs.py ../backend/app/cron/jobs.py
   ```

3. Apply Palmi modifications:
   - `wecom.py`: Add `user_id` routing dimension to session management
   - `scheduler.py`: Add per-user job registration support
   - `jobs.py`: Extend job metadata with `user_id` and `trigger_type` fields

## Files to Fork

| Source File | Size | Target | Modifications |
|------------|------|--------|---------------|
| `gateway/platforms/wecom.py` | 65KB | `backend/app/gateway/wecom.py` | Add multi-tenant routing |
| `gateway/platforms/wecom_crypto.py` | 5KB | `backend/app/gateway/wecom_crypto.py` | None |
| `cron/scheduler.py` | 77KB | `backend/app/cron/scheduler.py` | Add per-user tasks |
| `cron/jobs.py` | 41KB | `backend/app/cron/jobs.py` | Extend metadata |

## Configuration

After copying, configure in `.env`:
```
WECOM_BOT_ID=your-bot-id
WECOM_SECRET=your-secret
```

And in `config.yaml` (if using Hermes config format):
```yaml
platforms:
  wecom:
    enabled: true
    extra:
      bot_id: "${WECOM_BOT_ID}"
      secret: "${WECOM_SECRET}"
      multi_tenant: true
      user_vault_root: "/data/users"
```
