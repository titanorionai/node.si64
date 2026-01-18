# VANGUARD UNIT - SI64 Twitter Bot Container Deployment Guide

## Overview

The VANGUARD UNIT is a containerized Twitter bot service integrated into the TITAN ecosystem. It handles:

- **Autonomous Social Media Management**: Scheduled posting, engagement, and community growth
- **Psychological Operations (PsyOps)**: Content distribution, narrative control, and brand dominance
- **Service Integration**: Seamless connectivity with TITAN BRAIN and OLLAMA services
- **Operational Resilience**: Auto-restart, health monitoring, and resource isolation

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              VANGUARD UNIT (Bot Container)              │
├─────────────────────────────────────────────────────────┤
│  Dockerfile.vanguard → Builds container image           │
│  vanguard_entrypoint.py → Initialization & startup      │
│  si64_twitter_bot.py → Core bot logic                   │
│  .env → Twitter API credentials (secure)                │
└─────────────────────────────────────────────────────────┘
         ↓                          ↓
    ┌─────────────┐         ┌──────────────┐
    │ TITAN BRAIN │         │   OLLAMA     │
    │  (API 8000) │         │   (11434)    │
    └─────────────┘         └──────────────┘
         ↑                          ↑
    Internal Communication   AI Inference & Analytics
```

---

## Setup & Deployment

### 1. Populate Twitter Credentials

Edit `/home/titan/TitanNetwork/.env` and add your Twitter API credentials:

```bash
# Twitter API v2 Credentials
SI64_TWITTER_API_KEY=your_api_key_here
SI64_TWITTER_API_SECRET=your_api_secret_here
SI64_TWITTER_ACCESS_TOKEN=your_access_token_here
SI64_TWITTER_ACCESS_SECRET=your_access_token_secret_here
```

**Secure the file:**
```bash
chmod 600 /home/titan/TitanNetwork/.env
```

### 2. Build the Container Image

```bash
cd /home/titan/TitanNetwork
docker build -f Dockerfile.vanguard -t titan-vanguard:latest .
```

### 3. Deploy with Docker Compose

```bash
cd /home/titan/TitanNetwork
docker compose up -d titan-vanguard
```

### 4. Verify Deployment

```bash
# Check container status
docker ps | grep vanguard

# View logs
docker logs titan-vanguard-unit

# Check health
docker inspect titan-vanguard-unit --format='{{.State.Health.Status}}'
```

---

## Configuration

### Environment Variables (in docker-compose.yml)

| Variable | Default | Purpose |
|----------|---------|---------|
| `BOT_MODE` | `STANDARD_GROWTH` | Operating mode (AGGRESSIVE, STANDARD, CONSERVATIVE) |
| `BOT_DIRECTIVE` | `COMMUNITY_ENGAGEMENT` | Operational directive (ENGAGEMENT, GROWTH, DOMINANCE) |
| `POST_INTERVAL_SEC` | `1800` | Seconds between posts (30 min = 1800s) |
| `REPLY_PROBABILITY` | `0.85` | Probability of replying to mentions (0.0-1.0) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `MAX_NET_RETRIES` | `5` | Max retry attempts for network calls |
| `TITAN_BRAIN_URL` | `http://titan-brain:8000` | Brain API endpoint |
| `TITAN_OLLAMA_URL` | `http://titan-ollama-engine:11434` | OLLAMA inference endpoint |

**Modify via docker-compose.yml:**
```yaml
environment:
  - BOT_MODE=AGGRESSIVE_GROWTH
  - POST_INTERVAL_SEC=600  # 10 minutes
  - REPLY_PROBABILITY=0.95
```

Then redeploy:
```bash
docker compose up -d --force-recreate titan-vanguard
```

---

## Resource Limits

The container is configured with resource isolation:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # Max 1 CPU core
      memory: 1G       # Max 1GB RAM
    reservations:
      cpus: '0.25'     # Reserve 0.25 CPU
      memory: 256M     # Reserve 256MB RAM
```

This prevents the bot from consuming excessive resources and impacting other services.

---

## Health Monitoring

The container includes automated health checks:

```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c 'import si64_twitter_bot; print(\"OK\")' || exit 1"]
  interval: 60s        # Check every 60 seconds
  timeout: 10s         # Timeout after 10 seconds
  retries: 3           # Restart after 3 failures
  start_period: 30s    # Grace period on startup
```

**Manual health check:**
```bash
docker exec titan-vanguard-unit python -c "import si64_twitter_bot; print('✅ Healthy')"
```

---

## Service Dependencies

The VANGUARD unit automatically waits for dependencies:

```yaml
depends_on:
  brain:
    condition: service_healthy
  ollama:
    condition: service_healthy
```

The bot will only start once BRAIN and OLLAMA are fully operational.

---

## Logs & Monitoring

### View Live Logs
```bash
docker logs -f titan-vanguard-unit
```

### View Specific Errors
```bash
docker logs titan-vanguard-unit | grep ERROR
```

### Log File Inside Container
```bash
docker exec titan-vanguard-unit tail -f /tmp/vanguard.log
```

### System Resource Usage
```bash
docker stats titan-vanguard-unit
```

---

## Operations

### Start Bot
```bash
docker compose up -d titan-vanguard
```

### Stop Bot
```bash
docker compose stop titan-vanguard
```

### Restart Bot
```bash
docker compose restart titan-vanguard
```

### Remove Container (keeps image)
```bash
docker compose rm -f titan-vanguard
```

### View Container Processes
```bash
docker top titan-vanguard-unit
```

---

## Troubleshooting

### Bot Not Starting

**Check logs:**
```bash
docker logs titan-vanguard-unit
```

**Common issues:**
- Missing Twitter credentials → Add to .env
- BRAIN/OLLAMA not healthy → Ensure main services are running
- Port conflicts → Check docker network

### Bot Crashes on Twitter Error

The container includes automatic restart (`restart: unless-stopped`), so it will recover.

**View crash reason:**
```bash
docker logs --tail 50 titan-vanguard-unit
```

### Memory/CPU Issues

Increase limits in docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

Then recreate:
```bash
docker compose up -d --force-recreate titan-vanguard
```

---

## Scaling & Optimization

### Multiple Bot Instances

To run multiple bots with different directives:

```yaml
titan-vanguard-1:
  # ... existing config
  environment:
    - BOT_DIRECTIVE=COMMUNITY_ENGAGEMENT
    - POST_INTERVAL_SEC=1800

titan-vanguard-2:
  # ... duplicate config
  container_name: titan-vanguard-unit-2
  environment:
    - BOT_DIRECTIVE=GROWTH_ACCELERATION
    - POST_INTERVAL_SEC=900
```

### Custom Personality Matrix

Modify bot behavior by changing environment variables:

```bash
# Aggressive rapid-fire posting
BOT_MODE=AGGRESSIVE_GROWTH
POST_INTERVAL_SEC=300  # Every 5 minutes
REPLY_PROBABILITY=1.0  # Always reply

# Conservative thoughtful posting
BOT_MODE=CONSERVATIVE
POST_INTERVAL_SEC=3600  # Every hour
REPLY_PROBABILITY=0.3  # Selective replies
```

---

## Security Considerations

1. **Credentials**: Never commit `.env` file to git. It's in `.gitignore`.
2. **Container User**: Runs as non-root user `vanguard` (UID 1000)
3. **Network Isolation**: Uses internal `titan-network` for service communication
4. **Resource Limits**: Prevents DoS attacks via resource exhaustion
5. **Health Monitoring**: Auto-restarts if process fails

---

## Integration with Master Control

The bot can be triggered from the Master Control GUI:

```python
# In master_control_v2.py
def _start_twitter_automation(self):
    # Start docker container
    subprocess.run(["docker", "compose", "up", "-d", "titan-vanguard"])
    self._log("✅ VANGUARD UNIT DEPLOYED", COLOR_TEXT_SUCCESS)

def _stop_twitter_automation(self):
    # Stop docker container
    subprocess.run(["docker", "compose", "stop", "titan-vanguard"])
    self._log("⊘ VANGUARD UNIT TERMINATED", COLOR_TEXT_WARN)
```

---

## Performance Metrics

- **Container Image Size**: ~400-500 MB
- **Memory Usage**: 256 MB (reserved) → 1 GB (max)
- **CPU Usage**: 0.25 CPU (reserved) → 1.0 CPU (max)
- **Startup Time**: ~30 seconds
- **Health Check Interval**: 60 seconds
- **Post Frequency**: Configurable (default 30 min)

---

## Advanced Configuration

### Use Environment Variables from File

Create a custom `.env.vanguard`:
```bash
SI64_TWITTER_API_KEY=...
SI64_TWITTER_API_SECRET=...
# ... other vars
```

Update docker-compose.yml:
```yaml
titan-vanguard:
  env_file:
    - .env
    - .env.vanguard
```

### Custom Entrypoint

To override the entrypoint:
```yaml
entrypoint: ["python", "-u", "vanguard_entrypoint.py"]
```

### Volume Mounts for Logs

Persist logs outside container:
```yaml
volumes:
  - /var/log/titan-vanguard:/tmp/logs
```

Access logs:
```bash
tail -f /var/log/titan-vanguard/vanguard.log
```

---

## Summary

✅ **VANGUARD UNIT** is now fully containerized and production-ready:

- Auto-restarts on failure
- Resource-isolated and monitored
- Secure credential injection via .env
- Full integration with TITAN ecosystem
- Comprehensive health checks
- Scalable to multiple instances

**Start the bot:**
```bash
cd /home/titan/TitanNetwork
docker compose up -d titan-vanguard
docker logs -f titan-vanguard-unit
```

**Status:** 🚀 **OPERATIONAL** - Social media dominance protocol engaged.
