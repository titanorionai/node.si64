# SI64.NET Worker Node Onboarding Guide

**Version:** 1.0  
**Date:** January 17, 2026  
**Status:** Production Ready  

---

## Overview

This guide walks a new user through joining the SI64.NET sovereign compute network as a worker node. By the end, your device will be:

- **Earning SOL** for running inference jobs
- **Connected to mainnet** (real Solana settlement)
- **Contributing compute power** to the decentralized grid
- **Ranked on the network** by uptime and performance

---

## Requirements

### Hardware
- **CPU:** 4+ cores (8+ recommended for M2/Orin)
- **Memory:** 16GB+ RAM
- **GPU (Optional):** Apple M-series, NVIDIA Jetson Orin/Thor, or similar
- **Storage:** 20GB free space for models
- **Network:** 100+ Mbps stable connection

### Software
- **OS:** Linux (Ubuntu 22.04+), macOS, or Raspberry Pi OS
- **Docker:** Installed and running (required for isolation)
- **Git:** For cloning the repository
- **Python 3.10+:** For the worker node script

### Account
- **Solana wallet:** Your earnings are paid to this address (get one from [phantom.app](https://phantom.app))
- **GitHub account:** Optional, for configuration management

---

## Quick Start (5 minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/si64-net/core.git
cd core
```

### Step 2: Initialize Configuration

```bash
mkdir -p ~/.si64
cp config.example.json ~/.si64/config.json
```

Edit `~/.si64/config.json` and set (for mainnet/production):
```json
{
  "worker_id": "your-device-name",
  "dispatcher_host": "si64.net",
  "ws_endpoint": "wss://si64.net/connect",
  "solana_wallet": "YOUR_PUBLIC_KEY_HERE",
  "hardware": {
    "cpu_cores": 8,
    "memory_gb": 64,
    "gpu": "Apple M3 Max"
  },
  "pricing": {
    "compute_rate_sol_per_hour": 0.004
  }
}
```

### Step 3: Start the Worker

```bash
python3 limb/worker_node.py \
  --config ~/.si64/config.json \
  --connect https://si64.net
```

### Step 4: Verify It's Running

From any machine with internet access:
```bash
curl https://si64.net/api/stats
```

You should see `"fleet_size": 1` (or higher) and your worker reflected in the telemetry.

---

## Detailed Setup

### Hardware Detection & Pricing

SI64.NET automatically detects your hardware and sets your hourly rate:

| Hardware | Specs | Rate | Best For |
|----------|-------|------|----------|
| **M2 Neural** | 8-core CPU, 8GB RAM | 0.001 SOL/hr | Development, small models (7B) |
| **M3 Max** | 12-core CPU, 36GB RAM | 0.004 SOL/hr | Medium inference (13B-30B) |
| **Orin** | 12-core CPU, 12GB VRAM | 0.004 SOL/hr | Computer vision, real-time inference |
| **M3 Ultra** | 12-core CPU, 128GB RAM | 0.025 SOL/hr | Large models (70B unquantized) |
| **Thor** | 12-core CPU, 144GB RAM | 0.035 SOL/hr | Multi-GPU scaling, training |

Your rate is locked in your config. Don't overprice (won't get jobs) or underprice (leaving money on the table).

### Configuration File Reference

```json
{
  "worker_id": "string",              // Unique identifier (auto-generated if missing)
  "genesis_key": "string",            // Security token (set by dispatcher, don't edit)
  "dispatcher_host": "si64.net",      // Network endpoint (Cloudflare tunnel to the dispatcher)
  "dispatcher_port": 443,             // HTTPS port
  "ws_endpoint": "string",            // WebSocket URI
  "solana_wallet": "string",          // Public key for payouts
  "hardware": {
    "cpu_cores": 8,                   // Cores available
    "memory_gb": 64,                  // RAM in GB
    "gpu": "Apple M3 Max",            // GPU model (or "None")
    "gpu_vram_gb": 36                 // VRAM (0 if no GPU)
  },
  "network": {
    "bandwidth_mbps": 1000,           // Your uplink speed
    "latency_ms": 25                  // Typical latency to si64.network
  },
  "pricing": {
    "compute_rate_sol_per_hour": 0.004,
    "minimum_uptime_hours": 24
  }
}
```

---

## Network Registration

When your worker connects, it goes through 3 authentication layers:

### Layer 1: Genesis Key Verification
- Your worker sends its unique genesis key
- Dispatcher validates it's not a duplicate
- ✅ Ensures network integrity

### Layer 2: Hardware Fingerprint
- Worker reports CPU cores, RAM, GPU
- Dispatcher validates specs match config
- ✅ Prevents false advertising

### Layer 3: Rate Agreement
- Worker submits hourly rate
- Dispatcher checks it's reasonable for hardware
- Client jobs can accept or reject your rate
- ✅ Prevents rate manipulation

Once all 3 pass, you're officially **APPROVED** and your worker joins the fleet.

---

## Earning SOL

### How Jobs Work

1. **Client submits inference request** (e.g., "Run Llama 7B on input X")
2. **Dispatcher routes to available workers** matching hardware tier
3. **Your worker receives job** via WebSocket
4. **Your worker spawns isolated Docker container** with Ollama
5. **Model runs, output returned** to dispatcher
6. **Result sent to client**
7. **SOL bounty transferred to your wallet** (mainnet settlement)

### Rewards

- **Per-job payout:** 0.0001 – 0.0005 SOL per inference
- **Uptime bonus:** 2% bonus if 99%+ uptime over 7 days
- **Rating bonus:** 1% bonus per 4.8/5 star rating
- **Speed bonus:** +5% if inference completes <2 standard deviations faster

### Expected Earnings

Assuming 40% utilization on a **Jetson Orin** (0.004 SOL/hr):

| Scenario | Daily | Monthly |
|----------|-------|---------|
| 40% busy | ◎ 0.384 SOL | ◎ 11.52 SOL |
| 60% busy | ◎ 0.576 SOL | ◎ 17.28 SOL |
| 80% busy | ◎ 0.768 SOL | ◎ 23.04 SOL |

*Note: Job frequency depends on network demand. Early adopters may see lower utilization.*

---

## Monitoring & Maintenance

### Check Worker Status

```bash
# View real-time metrics
curl http://localhost:8000/api/stats

# Expected output:
{
  "fleet_size": 47,
  "your_rank": 12,
  "uptime_percent": 99.7,
  "jobs_completed": 1234,
  "total_earnings": "◎ 2.543 SOL",
  "rating": "4.9/5.0"
}
```

### View Job History

```bash
# Last 10 jobs
curl http://localhost:8000/api/jobs?limit=10

# Job details:
{
  "job_id": "abc123...",
  "model": "llama2-7b",
  "input_tokens": 128,
  "output_tokens": 256,
  "duration_ms": 2341,
  "reward_sol": 0.0003,
  "status": "CONFIRMED"
}
```

### Logs

```bash
# Follow worker logs
docker logs -f titan-job-executor

# Check for errors:
# [ERROR] - Something failed
# [WARNING] - Non-critical issue
# [INFO] - Normal operation
```

### Automatic Restarts

If your worker crashes or network drops:
- Worker auto-reconnects every 5 seconds
- Docker restarts container automatically
- Pending jobs are re-queued on network
- **No manual intervention needed**

---

## Troubleshooting

### Worker Won't Connect

**Error:** `Failed to connect to wss://si64.net/connect`

**Causes & Fixes:**
1. Check internet connection: `ping 8.8.8.8`
2. Check firewall allows outbound WSS (port 443): `nc -zv si64.net 443`
3. Restart worker: `Ctrl+C` and re-run Python command
4. Check dispatcher is live: `curl https://si64.net/api/stats`

### Docker Not Available

**Error:** `docker.sock: no such file or directory`

**Fix:**
```bash
# Ensure Docker is running
sudo systemctl start docker

# Ensure your user is in docker group
sudo usermod -aG docker $USER
newgrp docker
```

### GPU Not Detected

**Error:** `GPU: None` in config even though you have one

**Fix:**
- Ensure NVIDIA drivers installed: `nvidia-smi`
- For Apple Silicon: macOS 12+, Docker Desktop 4.0+
- Check Docker has GPU access:
  ```bash
  docker run --rm --gpus all nvidia/cuda:12.0-runtime nvidia-smi
  ```

### Jobs Complete But No Payout

**Error:** Jobs show `CONFIRMED` but wallet empty

**Causes:**
1. **Solana RPC timeout** — Network congestion, retry in 5 min
2. **Insufficient account rent** — Ensure wallet has ≥ 0.02 SOL for account fees
3. **Rate too low** — No clients accepted your jobs yet
4. **Early phase** — Testnet may have limited job volume

**Check logs:**
```bash
docker logs titan-job-executor 2>&1 | grep SETTLEMENT
```

---

## Security Best Practices

### Wallet Security
- ❌ **NEVER** paste your private key into config
- ❌ **NEVER** share your genesis key
- ✅ Use a **dedicated wallet** for SI64 earnings
- ✅ Keep wallet software **updated**

### Docker Security
- Your worker **only accesses** Ollama (localhost:11434)
- **Cannot** access host filesystem outside `/app` and `/tmp/titan-jobs`
- **Cannot** run arbitrary code (only Ollama inference)
- **Kill containers** after each job to prevent state leakage

### Network Security
- All connections are **WSS (encrypted)**
- Genesis key is **cryptographically signed**
- Solana transactions are **immutable on mainnet**
- Your earnings are **non-repudiable** (proven on-chain)

---

## Advanced Configuration

### Set Custom Worker ID

```bash
export WORKER_ID="my-m3-ultra-1"
python3 limb/worker_node.py --worker-id $WORKER_ID --config ~/.si64/config.json
```

### Set Custom Rate (Advanced)

⚠️ **Caution:** Too high = no jobs. Too low = lost revenue.

```json
// In ~/.si64/config.json
"pricing": {
  "compute_rate_sol_per_hour": 0.005  // 25% higher than default
}
```

### Enable GPU Passthrough

For **NVIDIA Jetson only** (requires nvidia-docker):

```bash
apt install nvidia-docker2
python3 limb/worker_node.py --gpu-passthrough --config ~/.si64/config.json
```

### Multiple Workers on One Machine

Run multiple instances on different ports:

```bash
# Terminal 1
WORKER_ID=gpu-1 python3 limb/worker_node.py --port 8001 --config ~/.si64/config.json

# Terminal 2
WORKER_ID=gpu-2 python3 limb/worker_node.py --port 8002 --config ~/.si64/config.json
```

---

## Support & Community

- **Discord:** https://discord.gg/si64
- **GitHub Issues:** https://github.com/si64-net/core/issues
- **Docs:** https://docs.si64.net
- **Status Page:** https://status.si64.net

### Report a Bug

```bash
# Capture logs and system info
docker logs titan-job-executor > worker.log
uname -a > system.log
cat ~/.si64/config.json > config.json

# Create GitHub issue with:
# 1. worker.log
# 2. system.log
# 3. Steps to reproduce
# 4. Expected vs actual behavior
```

---

## FAQ

**Q: Can I run multiple workers?**  
A: Yes! Run separate instances on different ports. Great for max utilization.

**Q: What if my internet drops?**  
A: Worker auto-reconnects. In-progress jobs time out (worker not penalized).

**Q: Do I need a GPU?**  
A: No, but GPU = higher rates and faster completions = more earnings.

**Q: Can I change my rate after starting?**  
A: Edit config and restart worker. New jobs use new rate.

**Q: How often do payouts happen?**  
A: Every Solana slot (~400ms). Settlement is near-instant on mainnet.

**Q: What if I go offline?**  
A: Jobs are re-queued to other workers. Your rating/uptime streak resets.

**Q: Can I see who's using my compute?**  
A: No. SI64 does not track job sources (privacy-first design).

**Q: Is this taxable?**  
A: Likely yes in most jurisdictions. Consult tax professional.

---

## Conclusion

You're now part of the **SI64.NET sovereign compute network**. 

**Next steps:**
1. ✅ Run the worker setup
2. ✅ Monitor your earnings on dashboard
3. ✅ Join the Discord community
4. ✅ Consider running 24/7 for max utilization

**Welcome aboard! 🚀**

---

*Last Updated: 2026-01-17*  
*Maintained by: SI64.NET Foundation*
