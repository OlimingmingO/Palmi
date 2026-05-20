#!/bin/bash
set -e

echo "[1/5] Backing up .env files..."
cp /opt/Palmi/.env /tmp/palmi_root.env.bak 2>/dev/null || true
cp /opt/Palmi/backend/.env /tmp/palmi_backend.env.bak 2>/dev/null || true

echo "[2/5] Extracting new code..."
tar xzf /tmp/palmi.tar.gz -C /opt/Palmi

echo "[3/5] Restoring .env files..."
cp /tmp/palmi_root.env.bak /opt/Palmi/.env
cp /tmp/palmi_backend.env.bak /opt/Palmi/backend/.env

echo "[4/5] Cleaning macOS metadata files..."
find /opt/Palmi -name "._*" -delete

echo "[5/5] Rebuilding and restarting services..."
cd /opt/Palmi
docker-compose build
docker-compose down
docker-compose up -d postgres redis app celery-worker celery-beat

echo "Deployment complete!"
docker-compose ps
