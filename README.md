# Palmi (小伴) — AI Companion for the Elderly

An AI-powered companion assistant for elderly users (60-75), delivering proactive care through Enterprise WeChat and phone calls. Built with a "cat-like presence" philosophy — non-intrusive but always there.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / Celery + Redis
- **Memory**: PKE (Personal Knowledge Engine) — per-user file vault + qmd semantic search
- **Gateway**: Hermes Agent fork (WeCom WebSocket + Cron scheduler)
- **LLM**: Qwen-Max (primary) + DeepSeek-V3 (backup)
- **Frontend**: React + Tailwind CSS (ops), Taro 3.6+ (configurator mini-program)
- **Database**: PostgreSQL 15+
- **Deployment**: Docker Compose on Aliyun ECS

## Quick Start

```bash
# Clone
git clone https://github.com/OlimingmingO/Palmi.git
cd Palmi

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Start all services
make docker-up

# Or develop locally
make setup    # Install dependencies
make dev      # Start development server
```

## Project Structure

```
Palmi/
├── backend/          # Python monolith (FastAPI + Celery + PKE)
├── frontend/
│   ├── ops-dashboard/    # Operations backend (React + Tailwind)
│   └── configurator/     # Mini-program for family members (Taro)
├── infra/            # Docker, Nginx, scripts
├── docs/             # PRDs, tech specs, design documents
└── data/             # PKE vault root (gitignored, runtime only)
```

## Documentation

- [Product Design](docs/design/小伴-产品设计方案.md)
- [Tech Selection Decision](docs/小伴-技术选型决策文档.md)
- [Foundation Tech Spec](docs/tech-spec/小伴-基础架构技术规格.md)

## License

Proprietary — All rights reserved.
