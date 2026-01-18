# VANGUARD UNIT - SI64 Twitter Bot Containerization
## Complete Deployment Index

---

## 📋 What is VANGUARD?

VANGUARD is the **containerized Twitter bot** for SI64.NET - a production-grade service that handles:
- Autonomous social media management
- Scheduled posting and engagement
- Community growth and brand dominance
- Seamless TITAN ecosystem integration

---

## 📦 What Was Created

### Core Files
| File | Size | Purpose |
|------|------|---------|
| `Dockerfile.vanguard` | 937 bytes | Container image definition |
| `vanguard_entrypoint.py` | 6.2 KB | Container initialization orchestration |
| `docker-compose.yml` | UPDATED | Added titan-vanguard service |
| `.env` | UPDATED | Twitter API credentials & config |
| `requirements.txt` | UPDATED | Added tweepy dependency |

### Documentation
| File | Size | Purpose |
|------|------|---------|
| `VANGUARD_DEPLOYMENT_GUIDE.md` | 9.4 KB | Complete deployment & operations manual |
| `VANGUARD_QUICK_START.md` | 3.1 KB | 5-step quick deployment checklist |
| `VANGUARD_SUMMARY.txt` | 13 KB | Technical summary & reference |
| `VANGUARD_INDEX.md` | This file | Navigation & overview |

---

## 🚀 Quick Start (5 Steps)

### 1. Add Twitter Credentials
```bash
vim /home/titan/TitanNetwork/.env

# Add your Twitter API credentials:
SI64_TWITTER_API_KEY=your_key_here
SI64_TWITTER_API_SECRET=your_secret_here
SI64_TWITTER_ACCESS_TOKEN=your_token_here
SI64_TWITTER_ACCESS_SECRET=your_token_secret_here
```

### 2. Secure the File
```bash
chmod 600 /home/titan/TitanNetwork/.env
```

### 3. Build Container Image
```bash
cd /home/titan/TitanNetwork
docker build -f Dockerfile.vanguard -t titan-vanguard:latest .
```

### 4. Deploy the Bot
```bash
docker compose up -d titan-vanguard
```

### 5. Verify Deployment
```bash
docker ps | grep vanguard
docker logs -f titan-vanguard-unit
```

Expected output:
```
✅ All Twitter credentials loaded
✅ Bot authenticated successfully
🚀 LAUNCHING VANGUARD UNIT
✅ Automation scheduler started
🔄 VANGUARD UNIT OPERATIONAL
```

---

## 📚 Documentation Guide

### For Quick Reference
👉 Start with **VANGUARD_QUICK_START.md**
- Pre-deployment checklist
- 5-step deployment guide
- Common commands
- Troubleshooting quick fixes

### For Complete Setup
👉 Read **VANGUARD_DEPLOYMENT_GUIDE.md**
- Architecture overview
- Full setup & deployment
- Configuration reference
- Health monitoring details
- Advanced operations
- Scaling & optimization

### For Technical Details
👉 Review **VANGUARD_SUMMARY.txt**
- Deliverables overview
- Container specifications
- Operational directives
- Environment variables
- Maintenance commands
- Configuration examples
- Troubleshooting guide

---

## 🔧 Container Specifications

| Specification | Value |
|---------------|-------|
| Container Name | `titan-vanguard-unit` |
| Image Name | `titan-vanguard:latest` |
| Build File | `Dockerfile.vanguard` |
| Network | `titan-network` (internal) |
| CPU Limit | 1.0 core |
| Memory Limit | 1.0 GB |
| CPU Reserve | 0.25 core |
| Memory Reserve | 256 MB |
| Health Check Interval | 60 seconds |
| Restart Policy | `unless-stopped` |

---

## ⚙️ Operational Configuration

| Setting | Default Value |
|---------|----------------|
| Bot Mode | `STANDARD_GROWTH` |
| Bot Directive | `COMMUNITY_ENGAGEMENT` |
| Post Interval | 1800 seconds (30 minutes) |
| Reply Probability | 0.85 (85%) |
| Log Level | `INFO` |
| Max Retries | 5 attempts |
| BRAIN URL | `http://titan-brain:8000` |
| OLLAMA URL | `http://titan-ollama-engine:11434` |

---

## 🔗 Integration Points

The VANGUARD UNIT connects with:

```
┌─────────────────┐
│ VANGUARD UNIT   │
│ (Twitter Bot)   │
└────────┬────────┘
         │
    ┌────┴─────────────────┬──────────────────┐
    │                      │                  │
┌───▼─────────┐    ┌───────▼────┐    ┌──────▼────┐
│ TITAN BRAIN │    │   OLLAMA   │    │   REDIS   │
│ (API 8000)  │    │  (11434)   │    │ (Memory)  │
└─────────────┘    └────────────┘    └───────────┘
```

- **TITAN BRAIN**: Command & control API
- **OLLAMA**: AI inference for content generation
- **REDIS**: State persistence and caching
- **Internal Network**: Isolated `titan-network`

---

## 💻 Common Commands

### Deployment
```bash
# Start the bot
docker compose up -d titan-vanguard

# Stop the bot (graceful shutdown)
docker compose stop titan-vanguard

# Restart the bot
docker compose restart titan-vanguard

# Remove container (keeps image)
docker compose rm -f titan-vanguard
```

### Monitoring
```bash
# View live logs
docker logs -f titan-vanguard-unit

# View last 50 lines
docker logs --tail 50 titan-vanguard-unit

# Check resource usage
docker stats --no-stream titan-vanguard-unit

# Check health status
docker inspect titan-vanguard-unit --format='{{.State.Health.Status}}'
```

### Debugging
```bash
# Execute shell in container
docker exec -it titan-vanguard-unit bash

# Run health check manually
docker exec titan-vanguard-unit python -c 'import si64_twitter_bot; print("OK")'

# View full configuration
docker inspect titan-vanguard-unit | jq
```

---

## ⚠️ Troubleshooting

### Bot won't start
1. Check logs: `docker logs titan-vanguard-unit`
2. Verify credentials in `.env`
3. Ensure BRAIN/OLLAMA are healthy: `docker compose ps`
4. Check file permissions: `chmod 600 .env`

### Health check failing
1. View extended logs: `docker logs --tail 100 titan-vanguard-unit`
2. Check container status: `docker inspect titan-vanguard-unit | grep -A 10 Health`
3. Rebuild image if needed: `docker build -f Dockerfile.vanguard -t titan-vanguard:latest .`

### High memory/CPU usage
1. Check stats: `docker stats --no-stream titan-vanguard-unit`
2. Increase limits in `docker-compose.yml`
3. Recreate container: `docker compose up -d --force-recreate titan-vanguard`

---

## 🎯 Configuration Examples

### Aggressive Growth Mode
```yaml
environment:
  - BOT_MODE=AGGRESSIVE_GROWTH
  - BOT_DIRECTIVE=ESTABLISH_DOMINANCE
  - POST_INTERVAL_SEC=600    # 10 minutes
  - REPLY_PROBABILITY=0.95   # 95% reply rate
```

### Conservative Mode
```yaml
environment:
  - BOT_MODE=CONSERVATIVE
  - BOT_DIRECTIVE=COMMUNITY_FOCUS
  - POST_INTERVAL_SEC=3600   # 60 minutes
  - REPLY_PROBABILITY=0.3    # 30% reply rate
```

### Debug Mode
```yaml
environment:
  - LOG_LEVEL=DEBUG
  - BOT_MODE=STANDARD_GROWTH
  - POST_INTERVAL_SEC=1800
```

---

## 📊 Health Monitoring

The bot includes automated health monitoring:

```
Health Check Every 60 seconds
    ↓
Test: python -c 'import si64_twitter_bot; print("OK")'
    ↓
    ├─ PASS → Container healthy, continue
    │
    └─ FAIL (3 times) → Auto-restart container
           ↓
           Wait 30s grace period
           ↓
           Restart bot
```

**Container States:**
- `starting` (0-30s, grace period)
- `healthy` (all checks passing)
- `unhealthy` (failed checks, will restart)

---

## 🔐 Security Features

✅ **No Hardcoded Secrets**
- Credentials loaded from `.env` file
- Not included in Dockerfile
- Proper file permissions (600)

✅ **Non-Root User**
- Runs as UID 1000 (vanguard user)
- Reduces container attack surface

✅ **Resource Isolation**
- CPU limits prevent system overload
- Memory limits prevent runaway processes
- Prevents denial-of-service

✅ **Network Isolation**
- Internal Docker network only
- No exposed ports
- Service-to-service communication

---

## 📈 Performance Targets

| Metric | Target |
|--------|--------|
| Image Size | ~400-500 MB |
| Memory Usage | 256 MB (reserved) → 1 GB (max) |
| CPU Usage | 0.25 core (reserved) → 1.0 core (max) |
| Startup Time | ~30 seconds |
| Health Check Interval | 60 seconds |
| Post Frequency | Configurable (default 30 min) |

---

## 🔄 Update & Maintenance

### Update Credentials
```bash
# Edit .env file
vim /home/titan/TitanNetwork/.env

# Restart container
docker compose restart titan-vanguard
```

### Update Configuration
```bash
# Edit docker-compose.yml
vim /home/titan/TitanNetwork/docker-compose.yml

# Recreate container with new config
docker compose up -d --force-recreate titan-vanguard
```

### Rebuild Image
```bash
# Rebuild from Dockerfile
docker build -f Dockerfile.vanguard -t titan-vanguard:latest .

# Recreate container with new image
docker compose up -d --force-recreate titan-vanguard
```

### View Change History
```bash
# Check git status
git status

# View modifications
git diff docker-compose.yml
git diff .env
```

---

## 📞 Support & Help

### Quick Links
- **Quick Start**: Read `VANGUARD_QUICK_START.md`
- **Full Guide**: Read `VANGUARD_DEPLOYMENT_GUIDE.md`
- **Technical Details**: Read `VANGUARD_SUMMARY.txt`

### Common Issues
See **VANGUARD_DEPLOYMENT_GUIDE.md** → **Troubleshooting** section

### Logs for Diagnosis
```bash
# View detailed logs
docker logs -f titan-vanguard-unit

# Search for errors
docker logs titan-vanguard-unit | grep ERROR

# Export logs to file
docker logs titan-vanguard-unit > /tmp/vanguard-logs.txt
```

---

## 🎓 Learning Resources

### Docker Concepts
- Container: Isolated package of bot code + dependencies
- Image: Blueprint for creating containers
- Docker Compose: Multi-service orchestration (BRAIN, OLLAMA, VANGUARD, etc.)
- Health Checks: Automatic health monitoring & recovery

### TITAN Ecosystem
- TITAN BRAIN: Core dispatcher & API
- OLLAMA: AI inference engine
- REDIS: Memory/state persistence
- VANGUARD: Social media management

### Twitter Bot Concepts
- API Authentication: OAuth 1.1a
- Tweet Posting: Direct text to Twitter API
- Scheduled Posting: Configurable intervals
- Engagement: Monitoring & replying to mentions

---

## ✅ Verification Checklist

Before deploying, ensure:

- [ ] Docker & Docker Compose installed
- [ ] Twitter API credentials obtained
- [ ] `.env` file has credentials
- [ ] `.env` file permissions set to 600
- [ ] TITAN BRAIN service running
- [ ] OLLAMA service running
- [ ] Network `titan-network` exists
- [ ] Port 8000 (BRAIN) accessible

After deploying:

- [ ] Container is running: `docker ps | grep vanguard`
- [ ] Health status is healthy: `docker inspect ... --format='{{.State.Health.Status}}'`
- [ ] Logs show "Bot authenticated successfully"
- [ ] Logs show "VANGUARD UNIT OPERATIONAL"
- [ ] No errors in logs: `docker logs vanguard | grep ERROR`

---

## 🚀 Ready to Deploy

All components are production-ready:

✅ Container image (Dockerfile.vanguard)
✅ Initialization script (vanguard_entrypoint.py)
✅ Docker Compose integration
✅ Secure credential management
✅ Complete documentation
✅ Resource monitoring
✅ Auto-restart & health checks

**Status: 🟢 READY FOR PRODUCTION DEPLOYMENT**

---

**For questions or detailed information, see the VANGUARD documentation files in this directory.**
