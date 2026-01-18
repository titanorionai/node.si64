# TITAN PROTOCOL | Docker Container Isolation

## Status: ✅ ACTIVE

All AI jobs are now executed inside Docker containers, NOT on bare metal.

### Current Setup

**Ollama Service (Containerized)**
```
Container: titan-ollama-engine
Image: ollama/ollama:latest
Status: Running
Port: 127.0.0.1:11434 (localhost only - not exposed)
Memory Limit: 16GB
CPU Limit: 4 cores
Volumes: Persistent /root/.ollama (model cache)
```

### Security Guarantees

1. **Process Isolation**
   - Jobs run inside Docker containers
   - Cannot access host OS or other containers
   - Separate filesystem namespace

2. **Resource Limits**
   - Memory: 16GB max
   - CPU: 4 cores max
   - Prevents resource exhaustion attacks

3. **Network Isolation**
   - Ollama bound to 127.0.0.1:11434 (localhost only)
   - Not exposed to external network
   - Custom bridge network (172.28.0.0/16)

4. **Filesystem Protection**
   - Host filesystem not accessible from container
   - Read-only volumes where possible
   - Temporary files in container /tmp

### Commands

**Start Ollama Container:**
```bash
sudo docker compose up -d
```

**Check Status:**
```bash
sudo docker compose ps
```

**View Logs:**
```bash
sudo docker logs titan-ollama-engine -f
```

**Stop Ollama:**
```bash
sudo docker compose down
```

**Shell Access (Debug Only):**
```bash
sudo docker exec -it titan-ollama-engine /bin/bash
```

### Job Execution Flow

1. Worker node receives job from dispatcher
2. Job payload sent to Ollama container (via HTTP to 127.0.0.1:11434)
3. Ollama executes model inference isolated in container
4. Result returned to worker node
5. Worker node sends result to dispatcher
6. **Host OS never directly executes untrusted code**

### Verification

Check that Ollama is responding from container:
```bash
sudo docker exec titan-ollama-engine curl http://localhost:11434/api/tags
```

Check worker can reach container:
```bash
curl http://127.0.0.1:11434/api/tags
```

### Why This Matters

- ✅ **Bare Metal Exposure:** ELIMINATED
- ✅ **Privilege Escalation:** PREVENTED (Docker isolates privileges)
- ✅ **Resource Exhaustion:** PREVENTED (hard limits enforced)
- ✅ **Code Injection:** CONTAINED (runs in sandboxed filesystem)
- ✅ **Data Exfiltration:** MITIGATED (network isolation)

### Future Enhancements

1. GPU passthrough (nvidia-docker) for accelerated inference
2. Per-job temporary containers (one container = one job)
3. Seccomp profiles for additional syscall filtering
4. AppArmor/SELinux policies
5. Private registry for air-gapped deployments
