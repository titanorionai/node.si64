# TITAN PROTOCOL | The Sovereign ARM/Silicon Grid

![Titan Protocol](https://img.shields.io/badge/STATUS-MAINNET_BETA-0afff0?style=for-the-badge&logo=solana&logoColor=black)
![Architecture](https://img.shields.io/badge/ARCHITECTURE-ARM64_%2F_SILICON-white?style=for-the-badge&logo=apple&logoColor=black)
![Settlement](https://img.shields.io/badge/SETTLEMENT-SOLANA-9945FF?style=for-the-badge&logo=solana)

> **"The x86 monopoly is over. The future of AI inference is Edge-Native, Energy-Efficient, and Sovereign."**

## 1. Executive Summary

**Titan Protocol** is a decentralized physical infrastructure network (DePIN) designed exclusively for high-efficiency **ARM64** and **Apple Silicon** compute clusters. Unlike legacy cloud providers trapped in x86/CUDA mono-cultures, Titan leverages the massive, untapped latent power of consumer silicon (NVIDIA Jetson, Mac Studio, Raspberry Pi 5) to create a distributed supercomputer optimized for LLM inference.

We are building the **"Airbnb for Compute"**, settled instantly on the **Solana Blockchain**.

---

## 2. The Architecture: Biologically Inspired

The network is organized into three distinct biological components, creating a self-healing, censorship-resistant grid.

### 🧠 The Brain (Cortex Orchestrator)
* **Role:** The central dispatcher and settlement engine.
* **Tech Stack:** Python 3.10, FastAPI, Redis, SQLite (WAL Mode).
* **Security:** "Fortress" Grade.
    * **Rate Limiting:** 60 req/min for public IPs (DDoS mitigation).
    * **Sanitization:** Strict Pydantic validators preventing SQLi/XSS.
    * **Auth:** `x-genesis-key` cryptographic header verification.
* **Capacity:** Tuned for **52,000 concurrent WebSocket connections** on a single Jetson AGX Orin node.

### 💪 The Limb (Worker Node)
* **Role:** The muscle. Executes AI tasks on bare metal.
* **Tech Stack:** Python, Bash, Llama.cpp, CUDA (JetPack 6.0).
* **Behavior:**
    * **Event-Driven:** Maintains a persistent WebSocket uplink to the Brain.
    * **Pull-Based:** Signals `IDLE` state to request work; never polls.
    * **Hardware Aware:** auto-throttles based on GPU thermal sensors (`jtop`).

### ⚡ The Nervous System (Real-Time Bus)
* **Transport:** WebSockets (WSS).
* **Latency:** <15ms average round-trip time.
* **Protocol:** JSON-RPC over persistent TCP connections.

---

## 3. Tokenomics & Settlement

Titan Protocol bypasses traditional SaaS billing (Stripe/Fiat) in favor of **Micro-Settlements on Solana**.

* **Pay-Per-Token:** Compute is billed by the millisecond.
* **Instant Finality:** Workers are paid immediately upon proof-of-work submission.
* **Smart Contracts:**
    * **Rentals:** Users lock SOL in a smart contract to "lease" a specific hardware node (e.g., an H100 or AGX Orin) for a fixed duration.
    * **Jobs:** One-off inference tasks (Text-to-Image, LLM Chat) are settled via direct wallet transfers.

### Current Market Rates (Mainnet Beta)
| Hardware Tier | Architecture | Use Case | Cost (SOL/hr) |
| :--- | :--- | :--- | :--- |
| **Standard** | Apple M1/M2 | Dev / 7B Models | 0.002 |
| **Pro** | NVIDIA Jetson Orin | CV / Robotics / 70B | 0.005 |
| **Enterprise** | Apple M3 Ultra | 128k Context RAG | 0.015 |

---

## 4. Deployment Guide

### Prerequisites
* **Hardware:** NVIDIA Jetson (Orin/Xavier) OR Apple Silicon (M1/M2/M3).
* **OS:** Ubuntu 22.04+ (Jetson) or macOS Sonoma.
* **Network:** Port 8000 open (for Brain nodes only).

### Quick Start (Worker Node)

Join the grid and start earning SOL:

```bash
# 1. Clone the Repository
git clone [https://github.com/oddgodgamer/AGX-ORIN.git](https://github.com/oddgodgamer/AGX-ORIN.git)
cd AGX-ORIN

# 2. Install Dependencies
pip3 install -r requirements.txt

# 3. Connect to the Grid
python3 limb/worker_node.py --connect wss://titan-grid.network
