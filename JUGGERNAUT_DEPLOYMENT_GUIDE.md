# JUGGERNAUT V5.0 - DEPLOYMENT GUIDE

## What is JUGGERNAUT V5.0?

**TITAN VANGUARD | CLASS: JUGGERNAUT (V5.0)** is a cyberpunk-themed Twitter/X bot that:

- Autonomously generates high-octane tweets about SI64.NET network metrics
- Uses OLLAMA AI inference to create personality-driven content
- Fetches live data from TITAN BRAIN with fallback simulations
- Implements graceful shutdown and health monitoring
- Operates with a "Digital Hustler" persona inspired by GTA V and The Matrix

---

## Quick Start (3 Steps)

### 1. Add Twitter/X Credentials

```bash
vim /home/titan/TitanNetwork/.env

# Fill in your X/Twitter API v2 credentials:
X_API_KEY=your_api_key_here
X_API_SECRET=your_api_secret_here
X_ACCESS_TOKEN=your_access_token_here
X_ACCESS_SECRET=your_access_secret_here
```

Get credentials from: https://developer.twitter.com/en/portal/dashboard

### 2. Build & Deploy

```bash
cd /home/titan/TitanNetwork

# Build container
docker build -f Dockerfile.vanguard -t titan-vanguard:latest .

# Deploy
docker compose up -d titan-vanguard

# Monitor
docker logs -f titan-vanguard-unit
```

### 3. Verify Deployment

Expected log output:
```
=== TITAN JUGGERNAUT V5.0 ONLINE ===
[COMMS] AUTHENTICATED AS: @your_handle
>>> IT'S SHOWTIME <<<
[INTEL] LIVE DATA ACQUIRED: XX NODES
[NEURAL] SPINNING UP THE HYPE ENGINE...
[NEURAL] PAYLOAD GENERATED (XXXms)
[COMMS] BLASTED: [tweet text here]
[TIMER] CHILLING FOR XXX MINS
```

---

## Architecture

```
┌────────────────────────────────────┐
│  VANGUARD JUGGERNAUT V5.0 (Bot)    │
├────────────────────────────────────┤
│                                    │
│  1. TitanUplink                    │
│     ├─ Fetches network stats       │
│     └─ Fallback: Simulation data   │
│                                    │
│  2. PsyOpsGenerator                │
│     ├─ Calls OLLAMA for LLM        │
│     ├─ Cleans output               │
│     └─ Generates tweet (240 chars) │
│                                    │
│  3. XComms (Twitter/X API)         │
│     ├─ Authenticates               │
│     └─ Posts to timeline           │
│                                    │
└──────┬──────────────┬──────────────┘
       ↓              ↓
   BRAIN API    OLLAMA LLM
  (Stats)      (Generation)
```

---

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `X_API_KEY` | (required) | Twitter API Key |
| `X_API_SECRET` | (required) | Twitter API Secret |
| `X_ACCESS_TOKEN` | (required) | Access Token |
| `X_ACCESS_SECRET` | (required) | Access Secret |
| `BOT_MODE` | `DIGITAL_JUGGERNAUT` | Bot persona mode |
| `POST_INTERVAL_MIN` | `60` | Min seconds between posts |
| `POST_INTERVAL_MAX` | `180` | Max seconds between posts |
| `TITAN_BRAIN_URL` | `http://titan-brain:8000/api/stats` | Stats endpoint |
| `TITAN_OLLAMA_URL` | `http://titan-ollama-engine:11434/api/generate` | LLM endpoint |

### Adjust Post Frequency

Edit docker-compose.yml:

```yaml
environment:
  - POST_INTERVAL_MIN=30    # Post every 30-90 seconds (rapid fire)
  - POST_INTERVAL_MAX=90
```

Or conservative:

```yaml
environment:
  - POST_INTERVAL_MIN=600   # Post every 10-30 minutes
  - POST_INTERVAL_MAX=1800
```

Then restart:
```bash
docker compose up -d --force-recreate titan-vanguard
```

---

## Persona & Tone

The JUGGERNAUT persona is:

- **Tone**: High-octane, street-level cyberpunk
- **Style**: Arrogant but charming, confident
- **Slang**: "Preem", "Zeroed", "Gonk", "Nova", "Blasted"
- **Attitude**: Mocks idle GPUs, flexes network dominance
- **References**: GTA V Radio Host meets The Matrix

Example generated tweets:

```
Wake up the Silicon! 🔥 128 units, 1200+ jobs pending, 42 SOL flowing.
You got ARM? We got the net. -VANGUARD

Zeroed out another batch. ARMY at full strength, queues PREEM.
Gonks with idle GPU? We don't know her. $SOL to the moon.
```

---

## Data Sources

### Network Stats (TitanUplink)

Fetches from BRAIN API:
- `fleet_size`: Number of compute units
- `queue_depth`: Pending jobs count  
- `total_revenue`: SOL yield
- `simulated`: Flag if using fallback data

If BRAIN is offline, uses simulation data to keep bot operational during development.

### Tweet Generation (PsyOpsGenerator)

Uses OLLAMA + Llama3 with:
- Temperature: 0.95 (creative)
- Top-K: 50 (diverse)
- Max tokens: 128
- Prompt: Juggernaut personality + stats

Output cleaning removes:
- LLM conversational fluff
- Prefix phrases ("Here is the tweet:")
- Trailing quotes

---

## Operational Features

### Graceful Shutdown

The bot catches `SIGINT` and `SIGTERM` signals:

```bash
# Clean shutdown
docker compose stop titan-vanguard

# Or kill the process
pkill -f vanguard_bot.py
```

### Health Monitoring

Writes heartbeat file every cycle:

```bash
cat /tmp/vanguard_heartbeat  # Shows last update timestamp
```

Docker health check verifies bot is still running.

### Error Handling

- **BRAIN offline**: Uses simulated stats
- **OLLAMA offline**: Skips generation, retries next cycle
- **Twitter auth failed**: Logs error, continues
- **Tweet post failed**: Logs error, continues next cycle
- **Critical error**: Logs and waits 60 seconds before retry

---

## Troubleshooting

### Bot won't authenticate

```bash
# Check credentials in .env
grep "X_API" /home/titan/TitanNetwork/.env

# Verify they're valid at: https://developer.twitter.com
```

### No tweets being posted

```bash
# Check logs
docker logs -f titan-vanguard-unit

# Look for:
# [COMMS] AUTH FAILED: ... → Credentials issue
# [NEURAL] FAILURE: ... → OLLAMA not responding
# [COMMS] JAMMED: ... → Twitter API issue
```

### OLLAMA not responding

```bash
# Check OLLAMA health
docker logs titan-ollama-engine | tail -20

# Verify Llama3 model loaded
docker exec titan-ollama-engine ollama list
```

### High latency in tweet generation

Check OLLAMA resource usage:
```bash
docker stats titan-ollama-engine
```

Llama3 needs ~4GB memory. Increase if needed:
```yaml
ollama:
  mem_limit: 16g
  cpus: '4.0'
```

---

## Advanced Customization

### Modify the Prompt

Edit `/home/titan/TitanNetwork/vanguard_bot.py`, find `PsyOpsGenerator.generate_broadcast()`:

```python
prompt = (
    f"SYSTEM: You are Titan Vanguard (Juggernaut Class V5). "
    # ... modify tone, style, guidelines here
)
```

Then rebuild:
```bash
docker build -f Dockerfile.vanguard -t titan-vanguard:latest .
docker compose up -d --force-recreate titan-vanguard
```

### Use Different LLM Model

Edit the payload in `generate_broadcast()`:

```python
payload = {
    "model": "mistral",  # or neural-chat, starling, etc.
    # ...
}
```

### Add Custom Slang/Phrases

Add to the prompt guidelines:

```python
f"5. Add custom phrases: 'PREEM', 'ZEROED', 'GONK'. Use liberally.\n"
```

---

## Performance Metrics

- **Image Size**: ~400-500 MB
- **Memory Usage**: 256 MB reserved → 1 GB max
- **CPU Usage**: 0.25 core reserved → 1.0 core max
- **Startup Time**: ~10 seconds (OLLAMA warm-up)
- **Tweet Generation**: 500-2000ms (depends on model)
- **Post Frequency**: 1-3 posts per hour (configurable)

---

## Operations Commands

```bash
# Start bot
docker compose up -d titan-vanguard

# View logs
docker logs -f titan-vanguard-unit

# Stop bot (graceful)
docker compose stop titan-vanguard

# Restart bot
docker compose restart titan-vanguard

# Check status
docker ps | grep vanguard

# Check resource usage
docker stats --no-stream titan-vanguard-unit

# Execute command in container
docker exec titan-vanguard-unit python -c "import tweepy; print('tweepy installed')"

# View heartbeat
docker exec titan-vanguard-unit cat /tmp/vanguard_heartbeat
```

---

## Security Notes

✅ **Credentials**: Loaded from `.env`, never in Dockerfile  
✅ **Non-root**: Runs as UID 1000 (vanguard user)  
✅ **Network**: Internal Docker network only  
✅ **Resources**: CPU/memory isolated  
✅ **Graceful**: Handles signals properly  

---

## Support

For issues:

1. Check logs: `docker logs titan-vanguard-unit`
2. Check credentials in `.env`
3. Verify BRAIN and OLLAMA are healthy
4. Check internet connectivity
5. Review troubleshooting section above

---

**JUGGERNAUT V5.0 is operational. Network dominance via social media engaged.** 🚀

