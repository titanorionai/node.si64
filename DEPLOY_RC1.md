# ARM64 Release Candidate (v1.0.1-rc1)

This document contains the exact commands used to build, publish, and validate the ARM64 Release Candidate image for Titan worker nodes.

Image (RC1): `titanorionai/worker-node:v1.0.1-rc1`

Build & Push (developer machine with Buildx):

```bash
docker login
docker buildx create --name titan-builder --use || true
docker buildx inspect --bootstrap
docker buildx build --platform linux/arm64 \
  -t titanorionai/worker-node:latest \
  -t titanorionai/worker-node:v1.0.1-rc1 \
  --push .
```

Fire-and-Forget (no mounts, remote operator):

```bash
# Replace YOUR_WALLET and optionally supply your genesis key
docker run -d \
  --name titan-node-rc1 \
  --restart unless-stopped \
  --network host \
  --cpus="2.0" \
  --memory="4g" \
  -e TITAN_WORKER_WALLET="YOUR_WALLET" \
  -e TITAN_GENESIS_KEY="<GENESIS_KEY>" \
  titanorionai/worker-node:v1.0.1-rc1

# Tail logs (verify it stays Up and accepts uplink)
docker logs -f titan-node-rc1
```

Validation Criteria:
- Container must start without any bind mounts.
- Logs should contain: `TITAN LIMB ONLINE.` and `UPLINK SECURE. AWAITING DIRECTIVES.`
- If the container exits immediately, collect `docker logs --tail 200` and retry with `TITAN_GENESIS_KEY` set.

Notes:
- This RC includes `python-dotenv` and `titan_config.py` baked into the image so it runs standalone.
- The image was built and validated on 2026-01-21 by the CI operator.
