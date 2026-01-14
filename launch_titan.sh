#!/bin/bash
# TITAN ORION: IRONCLAD LAUNCHER
# ------------------------------

# 1. HARDCODE THE ORIN GPU PATHS (This fixes the "Compiler Not Found" error forever)
export PATH=/usr/local/cuda/bin:$PATH
export CUDACXX=/usr/local/cuda/bin/nvcc
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
export CMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc

# 2. KILL EVERYTHING (Clear the ports)
echo ">>> CLEARING SYSTEM..."
pkill -9 -f master_control.py
pkill -9 -f predictor.py
pkill -9 -f orin_mev_bot
pkill -9 -f llama-server
pkill -9 -f cargo

# 3. LAUNCH THE GUI
echo ">>> STARTING MAINFRAME..."
cd ~
python3 master_control.py
