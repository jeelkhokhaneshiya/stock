# Cloud 24/7 Monitoring Deployment Guide

This document outlines the procedure to deploy the Phase 15 Antigravity Stock Monitoring Worker as a continuous 24/7 service on an Ubuntu Linux VPS. 

**IMPORTANT**: This deployment only enables monitoring and notification. Real automated execution remains strictly disabled. Human confirmation is required for all real-money orders.

## Prerequisites
- An Ubuntu 22.04+ VPS
- Telegram Bot Token & Chat ID
- Angel One Credentials (API Key, Client ID, Password, TOTP Secret)
- Python 3.10+

## 1. Initial Setup
SSH into your VPS and install Python and Git:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git
```

## 2. Clone and Install
Clone your private repository securely (using SSH or Personal Access Tokens).
```bash
git clone git@github.com:your-user/stock.git /opt/stock
cd /opt/stock/backend

# Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

## 3. Secure Configuration (.env)
Create the `.env` file securely. **Never commit this file to version control.**
```bash
touch .env
chmod 600 .env
nano .env
```

Add your credentials safely:
```env
# Angel One (Required)
ANGEL_ONE_API_KEY=your_real_api_key
ANGEL_ONE_CLIENT_ID=your_real_client_id
ANGEL_ONE_PASSWORD=your_real_password
ANGEL_ONE_TOTP_SECRET=your_real_totp_secret

# Telegram (Required for Notifications)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# System
MONITORING_INTERVAL_SECONDS=3600
DATABASE_URL=sqlite:///./stock.db
SECRET_KEY=generate_a_secure_random_string

# Safety Execution Flags
ENABLE_LIVE_TRADING=False
AUTONOMOUS_KILL_SWITCH=False
EXECUTION_MODE=SHADOW
```

## 4. Systemd Service Configuration
We use `systemd` to run the worker in the background securely. 

1. Create a dedicated non-root user (optional but recommended for security):
```bash
sudo useradd -r -s /bin/false stockbot
sudo chown -R stockbot:stockbot /opt/stock
```

2. Link the systemd service file (already provided in the repository under `deploy/monitoring-worker.service`):
```bash
sudo cp /opt/stock/deploy/monitoring-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## 5. Starting the Service
Start the service and enable it to run on boot:
```bash
sudo systemctl start monitoring-worker
sudo systemctl enable monitoring-worker
```

## 6. Verification & Health Check
Verify the service is running successfully:
```bash
# Check status
sudo systemctl status monitoring-worker

# Tail the logs
sudo journalctl -u monitoring-worker -f
```

### Health File
You can also verify the service health by checking the `monitoring_health.json` file generated in the working directory:
```bash
cat /opt/stock/backend/monitoring_health.json
```
This file tracks:
- `last_successful_cycle`
- `last_successful_auth`
- `status` (should be `"HEALTHY"`)

## 7. Telegram Test
Once running, you should monitor your Telegram app. The worker will send an alert on the next polling cycle if any actionable `BUY`/`SELL` decisions trigger based on your live portfolio data.

## Security Hardening
- **Root access**: Never run this service as root. It is restricted via `NoNewPrivileges=true` and `ProtectSystem=full` in systemd.
- **Environment variables**: The `.env` file is scoped strictly to `600` permissions.
- **Fail Safe**: If authentication fails or market data is unreachable, the system will mark the state as `ERROR` and optionally alert you, retrying on the next cycle gracefully.
