# SI64 // WORKER NODE [v1.0.2]

![Status](https://img.shields.io/badge/STATUS-OPERATIONAL-brightgreen)
![Arch](https://img.shields.io/badge/ARCH-ARM64-blueviolet)
![Network](https://img.shields.io/badge/NETWORK-SOLANA-000000)

> **"Compute is the currency of the future. This is your printing press."**

The **si64 Worker Node** is a lightweight, autonomous compute unit designed for the **si64 Decentralized Grid**. It transforms idle ARM64 hardware (NVIDIA Jetson, AWS Graviton, Raspberry Pi) into revenue-generating endpoints for AI inference and data processing tasks.

---

🏗️ ARCHITECTURE
This repository contains the Public Execution Environment for the si64 Network.

Zero-Config: No complex config files. State is handled via environment variables.

Outbound-Only: No inbound ports required. Uses secure WSS tunneling to punch through NATs.

Hardware Aware: Automatically detects NVIDIA Jetson (Orin/Thor/AGX) capabilities for accelerated workloads.

SUPPORTED HARDWARE
Primary: NVIDIA Jetson Orin / AGX / Nano

Secondary: Raspberry Pi 5 (64-bit)

Cloud: AWS Graviton / Ampere Altra

🛡️ SECURITY
Isolation: The worker node runs in a strictly unprivileged container.

Codebase: This repository contains only the public-facing worker logic. The core dispatcher and settlement engines are proprietary and hosted on the Controller Network.

Audit: All outgoing traffic is encrypted via TLS 1.3.
v1.0.2 // STABLE

--

## ⚡ QUICK START
Run the single command to install the node service on your device OR follow the steps below.

```bash
curl -sL [https://si64.net/install](https://si64.net/install) | bash
#The installer will prompt you for your Solana Wallet Address during setup.

OR

🐳 DOCKER DEPLOYMENT (MANUAL)
If you prefer to manage the container yourself, you can pull the official image.

#Pull the Image
docker pull titanorionai/worker-node:v1.0.2

#Run the Node Replace YOUR_WALLET_ADDRESS with your actual Solana public key.
docker run -d \
  --name si64-node \
  --restart unless-stopped \
  --network host \
  --runtime nvidia \
  -e SI64_WALLET_ADDRESS="YOUR_WALLET_ADDRESS" \
  titanorionai/worker-node:v1.0.2

#Note: Remove --runtime nvidia if running on non-Jetson hardware like a Raspberry Pi.

#VERIFICATION
#Verify your node is connected and transmitting telemetry:

#1. Check Local Logs. If installed via script:
journalctl -u si64-node -f

# If running via Docker:
docker logs -f si64-node

#Look for: [>>] SENT HANDSHAKE: {'type': 'handshake', 'model': 'NVIDIA Jetson Orin NX'}

#2. Check the Dashboard Visit app.si64.net and connect your wallet to view your active fleet.
#Welcome to si64.net!
