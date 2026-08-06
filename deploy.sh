#!/bin/bash

# Configuration
VPS_IP="151.244.228.104"
VPS_USER="root"
# Note: You can use sshpass if you want to automate password login, but using SSH keys is recommended.
# sshpass -p 'g2AjLzx1drew4ozpArNe' ssh ...

echo "Deploying AI Orchestrator to VPS ($VPS_IP)..."

sshpass -p 'g2AjLzx1drew4ozpArNe' rsync -avz -e "ssh -o StrictHostKeyChecking=no" --exclude '.venv' --exclude '__pycache__' --exclude '.git' --exclude '.worktrees' ./ $VPS_USER@$VPS_IP:/opt/ai_orchestrator/

# 2. Run deployment commands on VPS
sshpass -p 'g2AjLzx1drew4ozpArNe' ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP << 'EOF'
  cd /opt/ai_orchestrator

  echo "Starting Redis and LiteLLM via Docker Compose..."
  docker compose up -d || docker-compose up -d

  echo "Setting up Python environment..."
  # Ensure uv is installed
  if ! command -v /root/.local/bin/uv &> /dev/null; then
      curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  source $HOME/.local/bin/env

  /root/.local/bin/uv sync
  /root/.local/bin/uv pip install pytest pytest-asyncio

  echo "Restarting PM2 Services..."
  # Install PM2 if not present
  if ! command -v pm2 &> /dev/null; then
      npm install -g pm2
  fi

  pm2 delete all || true

  export GOOGLE_APPLICATION_CREDENTIALS=/opt/ai_orchestrator/vertex_sa.json
  export VERTEX_PROJECT_ID=my-project-28666-8-5-26-0-crm

  # Start FastAPI
  pm2 start "/root/.local/bin/uv run uvicorn api:app --host 0.0.0.0 --port 8000" --name "ai-api" --cwd /opt/ai_orchestrator --update-env
  
  # Start Celery Worker
  pm2 start "/root/.local/bin/uv run celery -A tasks worker --loglevel=info --concurrency=2" --name "ai-celery" --cwd /opt/ai_orchestrator --update-env

  pm2 save
  echo "Deployment Complete!"
EOF
