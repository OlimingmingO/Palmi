# 实施状态 / Implementation Status

Last updated: 2026-05-23

## 当前实施状态 / Current Implementation State

### Phase 0 — 渠道验证 / Channel Validation — ✅ COMPLETE

- WeCom HTTP callback at `/api/wechat/callback` (GET verification + POST message handling)
- LLM integration: `qwen-max` primary, `deepseek-v3` fallback (via DashScope / DeepSeek APIs)
- Conversation persistence (PostgreSQL 15)
- Multi-tenant elder resolution (`wechat_user_id` → Elder UUID)
- PKE memory system (file-based vault: raw capture + wiki compilation)
- Basic reply flow working end-to-end

### Phase 1 — 核心能力 / Core Features — ✅ COMPLETE

- Proactive triggers: morning greeting (08:00), weather alerts, silence detection
- Celery Beat scheduler for cron jobs
- Intent classification (LLM-based tag assignment on user messages)
- Unmet needs detection (automatic surfacing from conversations)
- PKE vault compilation (daily 03:00 cron)
- Trigger frequency controls (max per day, silence hours, min gap)

### Phase 3 — 运营 + 配置者 + 客服渠道 / Ops + Configurator + KF Channel — 🟡 MOSTLY COMPLETE

#### 运营后台 / Ops Console (React + Tailwind, port 3000)

- F1 User list with engagement status classification
- F2 Conversation browser (date-grouped, per-elder)
- F4 Tag review queue (low-confidence tags, manual correction)
- F7 Unmet needs aggregation + drill-down + dismiss
- F10 Tenant detail: WeChat identity, configurator list, profile content, binding controls, tag distribution pie chart, trigger history, PKE status
- Dashboard overview stats (DAU, WAU, status breakdown)
- Full-text conversation search

#### 配置者端 / Configurator Web Console (React + Tailwind, port 3001)

- F1 Elder onboarding: login → create elder → submit profile text → LLM generates understanding doc
- Profile append/merge (version-tracked)

#### 微信客服渠道 / WeCom KF Channel Integration

- Callback routing: detects `kf_msg_or_event` event type
- Message pull: cursor-based `sync_msg` with Redis deduplication
- Reply: `send_msg` via KF API
- Contact way link generation (admin endpoint)

#### 老人身份绑定 / Elder Identity Binding

- Auto nickname matching (fetch WeCom display name, match unbound `web_` elders)
- Manual binding (ops console UI + merge logic for duplicates)

## 实际架构 / Architecture (Actual — differs from original PRD)

- **Backend**: Python 3.11 + FastAPI + Uvicorn (custom monolith, NOT a Hermes WebSocket fork)
- **Task Queue**: Celery workers + Celery Beat (NOT Hermes cron/scheduler)
- **Database**: PostgreSQL 15 (asyncpg)
- **Cache / Broker**: Redis 7
- **Frontend**: Two React 18 + Vite + Tailwind CSS apps (`ops-dashboard`, `configurator`)
- **Deployment**: Docker Compose on Alibaba Cloud ECS (7 containers)
- **Messaging Channel**: WeCom Customer Service (微信客服) API via bound app secret

## 部署服务 / Deployed Services (ECS: 47.99.158.71)

| Service | Container | Port | URL |
|---------|-----------|------|-----|
| Backend API | `palmi-app` | 8000 | https://palmi.aiotzz.cn/api/ |
| Ops Console | `palmi-ops-frontend` | 3000 | http://47.99.158.71:3000 |
| Configurator | `palmi-configurator-frontend` | 3001 | http://47.99.158.71:3001 |
| Celery Worker | `palmi-celery-worker` | - | - |
| Celery Beat | `palmi-celery-beat` | - | - |
| PostgreSQL | `palmi-postgres` | 5432 | localhost only |
| Redis | `palmi-redis` | 6379 | localhost only |

## 已知问题与遗留工作 / Known Issues & Remaining Work

- `palmi-scheduler` container in restart loop (stub with no main loop — non-blocking)
- Nginx upstream DNS cache: must restart `palmi-ops-frontend` after backend recreate
- WeCom KF integration awaiting end-to-end test (user needs to message 客服 account from personal WeChat)
- Phase 3 features NOT yet implemented:
  - F3 full-text search improvements
  - F5 topic stats
  - F6 activity dashboard
  - F9 PKE monitor
- Browser automation testing unreliable with React SPAs (manual testing recommended)
