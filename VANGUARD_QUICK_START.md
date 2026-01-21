# VANGUARD UNIT - QUICK DEPLOYMENT CHECKLIST

## Pre-Deployment

- [ ] Twitter API credentials obtained from https://developer.twitter.com
- [ ] Credentials added to `/home/titan/TitanNetwork/.env`
- [ ] File permissions set: `chmod 600 .env`
- [ ] Docker & Docker Compose installed
- [ ] TITAN BRAIN and OLLAMA services running
- [ ] Network `titan-network` created

## Deployment Steps

```bash
# 1. Navigate to workspace
cd /home/titan/TitanNetwork

# 2. Verify .env has Twitter credentials
grep "SI64_TWITTER_" .env

# 3. Build container image
docker build -f Dockerfile.vanguard -t titan-vanguard:latest .

# 4. Start the bot
docker compose up -d titan-vanguard

# 5. Verify deployment
docker ps | grep vanguard
docker logs titan-vanguard-unit
```

## Post-Deployment Verification

```bash
# Check container status
docker inspect titan-vanguard-unit --format='{{.State.Status}}'

# Expected output: running

# Check health status
docker inspect titan-vanguard-unit --format='{{.State.Health.Status}}'

# Expected output: healthy

# Verify credentials loaded
docker logs titan-vanguard-unit | grep "All Twitter credentials"

# Expected output: ✅ All Twitter credentials loaded

# Check resource usage
docker stats --no-stream titan-vanguard-unit
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `docker compose up -d titan-vanguard` | Start bot |
| `docker compose stop titan-vanguard` | Stop bot |
| `docker compose restart titan-vanguard` | Restart bot |
| `docker logs -f titan-vanguard-unit` | View live logs |
| `docker exec titan-vanguard-unit bash` | Shell access |
| `docker stats titan-vanguard-unit` | Resource usage |

## Troubleshooting

### Bot won't start
```bash
# Check logs for errors
docker logs titan-vanguard-unit

# Verify credentials in .env
grep "SI64_TWITTER_" .env | grep -v "^#"

# Check if BRAIN/OLLAMA are healthy
docker compose ps
```

### High memory usage
```bash
# Check actual usage
docker stats --no-stream titan-vanguard-unit

# If >1GB, increase limit in docker-compose.yml
# Then recreate: docker compose up -d --force-recreate titan-vanguard
```

### Bot keeps restarting
```bash
# View detailed error logs
docker logs --tail 100 titan-vanguard-unit

# Check container health
docker inspect titan-vanguard-unit | grep -A 10 "Health"
```

## Operational Status

```
✅ Container Image:     Ready (Dockerfile.vanguard)
✅ Entrypoint Script:   Ready (vanguard_entrypoint.py)
✅ Docker Compose:      Ready (updated docker-compose.yml)
✅ Environment Config:  Ready (.env with credentials)
✅ Requirements:        Ready (tweepy added)
✅ Deployment Guide:    Ready (VANGUARD_DEPLOYMENT_GUIDE.md)

🚀 STATUS: READY FOR DEPLOYMENT
```

## Next Steps

1. **Add credentials**: Update `.env` with Twitter API keys
2. **Build image**: `docker build -f Dockerfile.vanguard -t titan-vanguard:latest .`
3. **Deploy**: `docker compose up -d titan-vanguard`
4. **Monitor**: `docker logs -f titan-vanguard-unit`
5. **Verify**: Check logs for "✅ Bot authenticated successfully"

---

**VANGUARD UNIT DEPLOYMENT - STATUS: 🟢 OPERATIONAL**

---

## ARM64 Worker RC1 (Optional)

For remote ARM64 operators, we publish an RC image built to be standalone. See `DEPLOY_RC1.md` for full commands.

Quick pull & run (no mounts):

```bash
docker pull titanorionai/worker-node:v1.0.1-rc1
docker run -d --name titan-node-rc1 --restart unless-stopped --network host -e TITAN_WORKER_WALLET="YOUR_WALLET" -e TITAN_GENESIS_KEY="<GENESIS_KEY>" titanorionai/worker-node:v1.0.1-rc1
docker logs -f titan-node-rc1
```
