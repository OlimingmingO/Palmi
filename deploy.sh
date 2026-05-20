#!/bin/bash
set -e

ECS_HOST="root@47.99.158.71"
LOCAL_REPO="/Users/lizhentao/Elder/Palmi"

echo "[1/4] Pulling latest code from GitHub..."
cd "$LOCAL_REPO"
git pull origin main

echo "[2/4] Cleaning macOS metadata files..."
find . -name "._*" -delete

echo "[3/4] Packaging and uploading to ECS..."
tar czf /tmp/palmi.tar.gz \
  --exclude='.env' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='node_modules' \
  .
scp /tmp/palmi.tar.gz "$ECS_HOST":/tmp/palmi.tar.gz

echo "[4/4] Running remote deployment..."
ssh "$ECS_HOST" 'bash /opt/scripts/palmi_deploy.sh'

echo "Done! Deployment complete."
