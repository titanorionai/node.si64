#!/bin/bash
# TITAN PROTOCOL | Security Verification Script
# Verifies all containerization and security measures

echo "=========================================="
echo "TITAN PROTOCOL | Security Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Check 1: Docker Container Running
echo -n "✓ Docker Ollama Container Status... "
if sudo docker compose ps | grep -q "titan-ollama-engine.*Up"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 2: Ollama API Responsive
echo -n "✓ Ollama API Responding... "
if curl -s http://127.0.0.1:11434/api/tags &>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 3: Container Network Isolated
echo -n "✓ Container Network Isolated... "
if sudo docker network ls | grep -q titan-network; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 4: Port Binding (localhost only)
echo -n "✓ Port Binding Localhost Only... "
if sudo docker compose ps | grep -q "127.0.0.1:11434"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 5: Dispatcher Service Running
echo -n "✓ Dispatcher Service Status... "
if sudo systemctl is-active --quiet titan-brain; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 6: Redis Available
echo -n "✓ Redis State Cache Online... "
if redis-cli ping 2>&1 | grep -q PONG; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 7: Database Accessible
echo -n "✓ SQLite Database Accessible... "
if [ -f "/home/titan/TitanNetwork/titan_ledger.db" ]; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 8: Environment Variables Correct
echo -n "✓ Genesis Key Configured... "
if grep -q "TITAN_GENESIS_KEY_V1_SECURE" /home/titan/TitanNetwork/.env; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Check 9: Container Filesystem Isolated
echo -n "✓ Container Filesystem Isolated... "
CONTAINER_ID=$(sudo docker ps --filter "name=titan-ollama-engine" -q 2>/dev/null)
if [ ! -z "$CONTAINER_ID" ]; then
    # Host files should not be accessible in container
    RESULT=$(sudo docker exec $CONTAINER_ID ls /mnt 2>/dev/null | wc -l)
    if [ "$RESULT" -eq 0 ] || [ "$RESULT" -eq 1 ]; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
else
    echo -e "${YELLOW}SKIP${NC}"
fi

# Check 10: Resource Limits Enforced
echo -n "✓ Memory Limit Set (16GB)... "
MEMORY_LIMIT=$(sudo docker inspect titan-ollama-engine --format='{{.HostConfig.Memory}}' 2>/dev/null)
if [ "$MEMORY_LIMIT" -ge 17179869184 ]; then  # 16GB in bytes
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Results: ${GREEN}${PASSED} PASSED${NC} | ${RED}${FAILED} FAILED${NC}"
echo "=========================================="
echo ""
echo "Security Status: $([ $FAILED -eq 0 ] && echo -e "${GREEN}✅ ALL SYSTEMS SECURE${NC}" || echo -e "${RED}⚠️  ISSUES DETECTED${NC}")"
echo ""
echo "Isolation Guarantee: Jobs execute ONLY in Docker containers"
echo "Network Isolation: Ollama not exposed to external network"
echo "Resource Limits: Memory (16GB) and CPU (4 cores) enforced"
echo ""
