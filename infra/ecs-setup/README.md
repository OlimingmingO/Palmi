# ECS Setup Guide

This directory contains configuration files and setup instructions for deploying Palmi to Alibaba Cloud ECS (Ubuntu 22.04).

**Server**: 47.99.158.71  
**Domain**: palmi.aiotzz.cn  
**OS**: Ubuntu 22.04 LTS

---

## One-Time ECS Setup

### 1. Install dependencies

```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx git
systemctl enable docker && systemctl start docker
```

### 2. Configure Docker CN mirrors (Docker Hub is blocked in China)

```bash
cp docker-daemon.json /etc/docker/daemon.json
systemctl daemon-reload && systemctl restart docker
```

### 3. Clone / upload code

GitHub is blocked in China ECS. Upload from Mac instead:

```bash
# On Mac:
cd /path/to/Palmi
./deploy.sh
```

### 4. Configure environment

```bash
mkdir -p /opt/Palmi/backend
cp .env.template /opt/Palmi/.env
cp .env.template /opt/Palmi/backend/.env
# Edit both files and fill in all secrets
nano /opt/Palmi/.env
nano /opt/Palmi/backend/.env
```

### 5. Configure nginx

```bash
cp nginx-palmi.conf /etc/nginx/sites-available/palmi
ln -s /etc/nginx/sites-available/palmi /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

### 6. Get SSL certificate (Let's Encrypt - free)

```bash
certbot --nginx -d palmi.aiotzz.cn --non-interactive --agree-tos -m YOUR_EMAIL
```

### 7. Create deploy script on ECS

```bash
mkdir -p /opt/scripts
# Copy palmi_deploy.sh from this repo to /opt/scripts/palmi_deploy.sh
chmod +x /opt/scripts/palmi_deploy.sh
```

---

## Known Issues & Fixes

| Problem | Fix |
|---|---|
| GitHub clone blocked in China ECS | Use `./deploy.sh` from Mac (SCP-based) |
| Docker Hub blocked in China | `/etc/docker/daemon.json` with CN mirrors (see above) |
| PyPI blocked in China during Docker build | Dockerfile uses `-i https://mirrors.aliyun.com/pypi/simple/` |
| Docker Compose V1 only (not V2) | Use `docker-compose` (hyphenated), not `docker compose` |
| `--force-recreate` crashes Docker Compose V1 | Use `docker-compose down && docker-compose up -d` instead |
| macOS `._*` metadata files corrupt Docker image | Always run `find . -name "._*" -delete` before packaging |
| `.env` must exist in project root | Keep both `/opt/Palmi/.env` and `/opt/Palmi/backend/.env` |
| Alembic null byte error from `._*` files | deploy script runs `find /opt/Palmi -name "._*" -delete` |
| `npm ci` fails (frontend not needed for Phase 0) | Start only `postgres redis app` services |
| Certbot requires a real email | Use a real email, not placeholder |

---

## Recurring Deploy Workflow

After making code changes and pushing to GitHub:

```bash
cd /Users/lizhentao/Elder/Palmi
./deploy.sh
```

---

## Service Health Check

```bash
# Check containers
docker-compose -f /opt/Palmi/docker-compose.yml ps

# Check app health
curl https://palmi.aiotzz.cn/api/health

# View app logs
docker-compose -f /opt/Palmi/docker-compose.yml logs --tail=50 app
```
