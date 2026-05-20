# Implementation Status

Last updated: 2025-05-20

## Phase 0 (Complete)
- WeCom message channel (HTTP callback, not WebSocket)
- LLM integration (qwen3-coder-plus via DashScope coding endpoint)
- Basic health endpoint (/api/health)
- ECS deployment (Docker Compose)
- SSL/HTTPS (Let's Encrypt via certbot)
- One-click deploy workflow (deploy.sh)

## Phase 1 (Complete)
- Xiao Ban persona system prompt (warm elderly companion personality)
- Conversation persistence (PostgreSQL, conversations table)
- Multi-tenant elder resolution (WeCom user ID → elder record → UUID tenant key)
- PKE memory integration (capture conversations + use for context, Node.js subprocess)
- Celery Beat proactive scheduling
- Morning greeting (08:00 Asia/Shanghai daily)
- Daily PKE compile (03:00 Asia/Shanghai daily)

## Phase 2 (Not Started)
- Weather/calendar-aware trigger engine
- Phone call integration (Alibaba Cloud Voice)
- Enhanced PKE compile (Light/REM/Deep sleep cycles)
- Frequency control (max 2 proactive touches daily)
- Multi-modal responses (voice notes)

## Phase 3 (Not Started)
- Operations dashboard (React admin panel)
- Configurer mini-program (family member app)
- Emergency notification workflow
- Analytics and elder wellbeing dashboard

## Architecture Deviations from Original Tech Spec

| Original Plan | Actual Implementation | Reason |
|---|---|---|
| Fork Hermes Agent | Custom FastAPI monolith | Simpler, full control, no WebSocket complexity |
| WeCom WebSocket gateway | HTTP callback endpoint | Verified working, simpler to maintain, less infra |
| Hermes Cron scheduler | Celery Beat | Native integration with existing Celery task queue |
| Qwen-Max (primary LLM) | qwen3-coder-plus | Available via DashScope coding endpoint, good quality |
| SQLite (from Hermes) | PostgreSQL 15 | Better for multi-tenant, concurrent access, already in Docker |

## Service Architecture

```
WeCom Server → HTTPS → Nginx → FastAPI (app)
                                    ├── PostgreSQL (conversation + elder data)
                                    ├── Redis (Celery broker + cache)
                                    ├── Celery Worker (async PKE capture)
                                    └── Celery Beat (scheduled greetings + compile)
```
