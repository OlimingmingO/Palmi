# 小伴 (Palmi) — 老人陪伴 AI 后端

Xiao Ban is a warm WeCom-based AI companion for elderly users. The backend persists every conversation, learns each elder's life context through a Personal Knowledge Engine (PKE), and proactively reaches out (morning greeting, daily memory compile) on a schedule.

This repository contains the production backend, deployment scripts, and product documentation.

---

## Tech Stack

- **Backend framework**: Python 3.11 + FastAPI + Uvicorn
- **Channel**: WeCom (企业微信) HTTP callback (GET verification + POST message), AES + SHA1 crypto
- **LLM**: `qwen3-coder-plus` via DashScope coding endpoint (`https://coding.dashscope.aliyuncs.com/v1`)
- **Database**: PostgreSQL 15 (async via `asyncpg`, sync via `psycopg2` for Alembic / Celery)
- **Cache / queue broker**: Redis 7
- **Async tasks**: Celery Worker (PKE capture, side effects)
- **Scheduler**: Celery Beat (morning greeting 08:00, daily PKE compile 03:00, Asia/Shanghai)
- **Memory**: Personal Knowledge Engine (PKE) — Node.js CLI invoked as subprocess from Python (fail-open, 1s timeout)
- **Migrations**: Alembic
- **Reverse proxy / TLS**: Nginx + Let's Encrypt (certbot)
- **Runtime**: Docker Compose on Alibaba Cloud ECS (Ubuntu)

---

## Architecture Overview

```
WeCom Server ──HTTPS──► Nginx ──► FastAPI (app)
                                    ├── PostgreSQL    (elders, conversations, tasks)
                                    ├── Redis         (Celery broker + cache)
                                    ├── Celery Worker (async PKE capture)
                                    └── Celery Beat   (proactive schedules)
```

**Inbound message flow (HTTP callback):**

1. WeCom posts an encrypted XML payload to `/api/wechat/callback`.
2. FastAPI verifies signature, decrypts with `WECOM_TOKEN` + `WECOM_ENCODING_AES_KEY`.
3. WeCom user ID is resolved to an `elder` row (multi-tenant via UUID tenant key).
4. Conversation history is loaded from PostgreSQL; PKE memory is fetched (Node CLI, fail-open).
5. `qwen3-coder-plus` generates Xiao Ban's reply with the warm-companion system prompt.
6. Reply is sent back via WeCom API; the turn is persisted; Celery captures it into PKE asynchronously.

**Proactive flow (Celery Beat):**

- 08:00 Asia/Shanghai — morning greeting per active elder.
- 03:00 Asia/Shanghai — daily PKE compile (consolidate yesterday's captures).

---

## Deploy

One-click deploy from your Mac:

```bash
./deploy.sh
```

This will:

1. `git pull` to make sure the local tree is current.
2. `tar` the repo and `scp` it to the ECS host.
3. SSH into the ECS host and run `infra/scripts/palmi_deploy.sh`, which:
   - extracts the tarball,
   - `docker-compose build` and `docker-compose up -d` for `postgres`, `redis`, `app`, `celery-worker`, `celery-beat`,
   - runs `alembic upgrade head` inside the `app` container.

Domain: `palmi.aiotzz.cn` (Let's Encrypt SSL, fronted by Nginx on the ECS host).

The full ECS bootstrap (Docker, Nginx, certbot, firewall) is documented in [infra/ecs-setup/README.md](./infra/ecs-setup/README.md).

---

## Project Structure

```
Palmi/
├── backend/                    # FastAPI service
│   ├── app/
│   │   ├── api/                # HTTP routes (wechat callback, admin, configurator, health)
│   │   ├── gateway/            # WeCom crypto, callback handler, WeCom API client
│   │   ├── services/           # Dialogue, conversation, elder, memory, guardian, ops
│   │   ├── pke/                # PKE capture / use / compile / governance bridge
│   │   ├── tasks/              # Celery task definitions
│   │   ├── cron/               # Celery Beat schedules
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── celery_app.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── migrations/             # Alembic migrations
│   ├── pke_engine/             # Bundled PKE Node.js CLI
│   ├── tests/
│   ├── Dockerfile
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── configurator/           # WeChat Mini-Program (family configurer) — Phase 3
│   └── ops-dashboard/          # React admin panel — Phase 3
├── infra/
│   ├── ecs-setup/              # ECS bootstrap notes, .env template, nginx + daemon configs
│   ├── nginx/                  # Application-level nginx config
│   └── scripts/                # init-db.sh, seed-data.sh, palmi_deploy.sh
├── docs/
│   ├── prd/                    # Product requirements
│   ├── tech-spec/              # Technical specifications
│   ├── 小伴-技术选型决策文档.md
│   └── IMPLEMENTATION_STATUS.md
├── data/                       # Local PKE vault (gitignored)
├── docker-compose.yml
├── deploy.sh
└── README.md
```

---

## Documentation

- [Implementation status](./docs/IMPLEMENTATION_STATUS.md) — what is actually built vs. planned
- [PRDs](./docs/prd/) — 老人端 / 配置者端 / 运营后台
- [Tech specs](./docs/tech-spec/) — 基础架构 / 老人端 / 配置者端 / 运营后台
- [技术选型决策文档](./docs/小伴-技术选型决策文档.md)
- [ECS 部署指南](./infra/ecs-setup/README.md)

---

## License

Private — all rights reserved.
