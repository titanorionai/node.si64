import logging
from typing import Dict, Any

# --- [ CONFIGURATION ] ---
# Centralized bounty rates for easy economic adjustments
RATES = {
    "MICRO": 0.00005,   # Raspberry Pi / Nano
    "EDGE": 0.002,      # Standard Orin / M1/M2
    "PRO": 0.005,       # AGX Orin / Ultra / Thor
    "HPC": 0.085,       # H100 / GH200
    "VECTOR": 0.025     # A64FX
}

# Setup professional logging (avoid reconfiguring root if already set)
logger = logging.getLogger("TITAN_MISSION_CONTROL")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')


def assign_mission_profile(worker_id: str, hardware_type: str) -> Dict[str, Any]:
    """MISSION CONTROL DISPATCHER v2.0

    Analyzes worker hardware telemetry to assign thermally safe and
    economically viable compute tasks.

    Args:
        worker_id (str): The unique wallet/ID of the worker.
        hardware_type (str): The self-reported hardware string (e.g., "NVIDIA_AGX_ORIN").

    Returns:
        dict: A mission profile containing job type, model, bounty, and complexity.
    """

    # 1. Normalize Input for Robust Matching
    hw_sig = hardware_type.upper().replace("-", "_").strip()

    mission_profile: Dict[str, Any] = {}

    # --- TIER 0: SCIENTIFIC SPECIALIST (A64FX) ---
    # Target: Fujitsu A64FX (Fugaku Class)
    # Capability: Massive Memory Bandwidth, Vector Math
    if "A64FX" in hw_sig or "FUGAKU" in hw_sig:
        logger.info(f"⚡ VECTOR DETECTED [{worker_id}]: Assigning Fluid Dynamics.")
        mission_profile = {
            "tier": "VECTOR_SVE",
            "type": "COMPUTATIONAL_FLUID_DYNAMICS",
            "model": "OpenFOAM_HPC_v9",
            "bounty": RATES["VECTOR"],
            "complexity": "SPECIALIZED",
            "thermal_limit": "CRITICAL",
        }

    # --- TIER 1: THE GODS (H100 / GH200 / THOR) ---
    # Target: Datacenter & Next-Gen Edge
    # Capability: FP8 Training, Trillion-Param Inference
    elif any(x in hw_sig for x in ["H100", "GH200", "THOR", "A100", "HOPPER"]):
        logger.info(f"🔱 GOD-TIER DETECTED [{worker_id}]: releasing full payload.")
        mission_profile = {
            "tier": "DATACENTER_HPC",
            "type": "LLM_TRAINING_FP8",
            "model": "Llama-3-405B-Instruct",
            "bounty": RATES["HPC"],
            "complexity": "EXTREME",
            "sharding": True,
        }

    # --- TIER 2: HEAVY EDGE (AGX ORIN / M2 ULTRA) ---
    # Target: High-end ARM64 Workstations
    # Capability: 70B Quantized Inference, RAG Pipelines
    elif any(x in hw_sig for x in ["AGX", "ULTRA", "MAX", "STUDIO"]):
        logger.info(f"🚀 HEAVY EDGE DETECTED [{worker_id}]: Assigning 70B Model.")
        mission_profile = {
            "tier": "PRO_WORKSTATION",
            "type": "LLM_INFERENCE_4BIT",
            "model": "Llama-3-70B-Quantized",
            "bounty": RATES["PRO"],
            "complexity": "HIGH",
            "context_window": "32k",
        }

    # --- TIER 3: STANDARD SILICON (ORIN / M1 / M2 / M3) ---
    # Target: Standard Apple Silicon & Jetson Orin NX/Nano
    # Capability: 7B/8B Models, Image Gen
    elif any(x in hw_sig for x in ["ORIN", "APPLE", "M1", "M2", "M3", "MAC"]):
        logger.info(f"💻 SILICON DETECTED [{worker_id}]: Assigning Standard Inference.")
        mission_profile = {
            "tier": "STANDARD_EDGE",
            "type": "LLM_INFERENCE_INT8",
            "model": "Llama-3-8B-Instruct",
            "bounty": RATES["EDGE"],
            "complexity": "MEDIUM",
        }

    # --- TIER 4: THE INFANTRY (PI / NANO / IOT) ---
    # Target: Low power devices
    # Capability: Ping, Relay, Consensus voting
    # PROTECTION: Prevents thermal throttling on passive cooling
    elif any(x in hw_sig for x in ["PI", "RASPBERRY", "NANO", "ZERO", "CORTEX"]):
        logger.warning(f"🛡️ THERMAL PROTECTION [{worker_id}]: Throttle engaged.")
        mission_profile = {
            "tier": "IOT_INFANTRY",
            "type": "NETWORK_HEARTBEAT",
            "model": "Ping_Verification_v2",
            "bounty": RATES["MICRO"],
            "complexity": "LOW",
            "sleep_cycles": 5,  # Force rest periods
        }

    # --- FALLBACK: UNKNOWN HARDWARE ---
    else:
        logger.warning(f"⚠️ UNIDENTIFIED SIGNAL [{worker_id}]: {hw_sig}. Probing capabilities.")
        mission_profile = {
            "tier": "UNKNOWN_ARTIFACT",
            "type": "HARDWARE_PROBE",
            "model": "System_Diagnostics",
            "bounty": 0.00001,
            "complexity": "MINIMAL",
        }

    return mission_profile
