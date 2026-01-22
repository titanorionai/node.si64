#!/bin/bash
# TITAN PROTOCOL | RESTART SEQUENCE
# =================================

TITAN_ROOT=~/TitanNetwork
LOG_DIR=$TITAN_ROOT/logs
mkdir -p $LOG_DIR

echo -e "\033[1;36m[TITAN] INITIATING NETWORK RESET...\033[0m"

# 1. TERMINATE EXISTING PROCESSES
echo -e "\033[0;33m[1/4] Terminating Active Nodes...\033[0m"
pkill -f "titan_cortex" 2>/dev/null
pkill -f "dispatcher.py" 2>/dev/null
pkill -f "worker_node.py" 2>/dev/null

# Wait for ports to clear
sleep 2

# 2. FLUSH REDIS (OPTIONAL - KEEPS QUEUE CLEAN)
# echo -e "\033[0;33m[2/4] Flushing Event Queue...\033[0m"
# redis-cli flushall > /dev/null 2>&1

# 3. LAUNCH THE CORTEX (BRAIN)
echo -e "\033[0;32m[2/4] Booting Titan Cortex (Dispatcher)...\033[0m"
if [ -f "$TITAN_ROOT/brain/dispatcher.py" ]; then
    nohup python3 $TITAN_ROOT/brain/dispatcher.py > $LOG_DIR/cortex.log 2>&1 &
    CORTEX_PID=$!
    echo "      >> Cortex Active (PID: $CORTEX_PID)"
else
    echo -e "\033[0;31m[ERROR] Dispatcher not found at $TITAN_ROOT/brain/dispatcher.py\033[0m"
    exit 1
fi

# Wait for Cortex to spin up
sleep 3

# 4. LAUNCH THE LIMB (WORKER)
echo -e "\033[0;32m[3/4] Engaging Worker Node...\033[0m"
# Attempt to find worker in two common locations based on previous chats
if [ -f "$TITAN_ROOT/core/limb/worker_node.py" ]; then
    WORKER_PATH="$TITAN_ROOT/core/limb/worker_node.py"
elif [ -f "$TITAN_ROOT/limb/worker_node.py" ]; then
    WORKER_PATH="$TITAN_ROOT/limb/worker_node.py"
else
    echo -e "\033[0;31m[WARNING] Worker Node script not found. Cortex is running alone.\033[0m"
    WORKER_PATH=""
fi

if [ ! -z "$WORKER_PATH" ]; then
    nohup python3 $WORKER_PATH --connect ws://127.0.0.1:8000/connect > $LOG_DIR/worker.log 2>&1 &
    WORKER_PID=$!
    echo "      >> Worker Active (PID: $WORKER_PID)"
fi

echo -e "\033[1;36m[4/4] NETWORK STATUS: NOMINAL\033[0m"
echo "      Logs available in: $LOG_DIR"
#!/bin/bash
# TITAN PROTOCOL | RESTART SEQUENCE
# =================================

TITAN_ROOT=~/TitanNetwork
LOG_DIR=$TITAN_ROOT/logs
mkdir -p $LOG_DIR

echo -e "\033[1;36m[TITAN] INITIATING NETWORK RESET...\033[0m"

# 1. TERMINATE EXISTING PROCESSES
echo -e "\033[0;33m[1/4] Terminating Active Nodes...\033[0m"
pkill -f "titan_cortex" 2>/dev/null
pkill -f "dispatcher.py" 2>/dev/null
pkill -f "worker_node.py" 2>/dev/null

# Wait for ports to clear
sleep 2

# 2. FLUSH REDIS (OPTIONAL - KEEPS QUEUE CLEAN)
# echo -e "\033[0;33m[2/4] Flushing Event Queue...\033[0m"
# redis-cli flushall > /dev/null 2>&1

# 3. LAUNCH THE CORTEX (BRAIN)
echo -e "\033[0;32m[2/4] Booting Titan Cortex (Dispatcher)...\033[0m"
if [ -f "$TITAN_ROOT/brain/dispatcher.py" ]; then
    nohup python3 $TITAN_ROOT/brain/dispatcher.py > $LOG_DIR/cortex.log 2>&1 &
    CORTEX_PID=$!
    echo "      >> Cortex Active (PID: $CORTEX_PID)"
else
    echo -e "\033[0;31m[ERROR] Dispatcher not found at $TITAN_ROOT/brain/dispatcher.py\033[0m"
    exit 1
fi

# Wait for Cortex to spin up
sleep 3

# 4. LAUNCH THE LIMB (WORKER)
echo -e "\033[0;32m[3/4] Engaging Worker Node...\033[0m"
# Attempt to find worker in two common locations based on previous chats
if [ -f "$TITAN_ROOT/core/limb/worker_node.py" ]; then
    WORKER_PATH="$TITAN_ROOT/core/limb/worker_node.py"
elif [ -f "$TITAN_ROOT/limb/worker_node.py" ]; then
    WORKER_PATH="$TITAN_ROOT/limb/worker_node.py"
else
    echo -e "\033[0;31m[WARNING] Worker Node script not found. Cortex is running alone.\033[0m"
    WORKER_PATH=""
fi

if [ ! -z "$WORKER_PATH" ]; then
    nohup python3 $WORKER_PATH --connect ws://127.0.0.1:8000/connect > $LOG_DIR/worker.log 2>&1 &
    WORKER_PID=$!
    echo "      >> Worker Active (PID: $WORKER_PID)"
fi

echo -e "\033[1;36m[4/4] NETWORK STATUS: NOMINAL\033[0m"
echo "      Logs available in: $LOG_DIR"
