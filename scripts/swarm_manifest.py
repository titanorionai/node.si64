"""TITAN SWARM MANIFEST
=======================
Low-power / high-availability infantry nodes for mission_control.

This module centralizes the known swarm IDs and their self-reported
hardware signatures so other tools (dashboards, planners, simulators)
can import a single source of truth.
"""

from typing import Dict, Any

from mission_control import assign_mission_profile

# --- THE SWARM (INFANTRY) -------------------------------------------------
# Format: NODE_ID -> HARDWARE_SIGNATURE
#
# Includes both earlier low-power swarm entries and the extended infantry
# set you defined.

SWARM_INFANTRY_NODES: Dict[str, str] = {
    # Low Power / High Availability (earlier set)
    "TITAN_NODE_044": "RASPBERRY_PI_5_8GB",
    "TITAN_NODE_045": "RASPBERRY_PI_4_4GB",
    "TITAN_NODE_046": "RASPBERRY_PI_4_4GB",
    "TITAN_NODE_047": "RASPBERRY_PI_ZERO_2W",

    # Extended Infantry / Nano + Pi Units
    "TITAN_NANO_ALPHA": "JETSON_NANO_4GB",
    "TITAN_NANO_BETA": "JETSON_NANO_4GB",
    "TITAN_NANO_GAMMA": "JETSON_NANO_4GB",
    "TITAN_PI_UNIT_01": "RASPBERRY_PI_5_8GB",
    "TITAN_PI_UNIT_02": "RASPBERRY_PI_5_8GB",
    "TITAN_PI_UNIT_03": "RASPBERRY_PI_4_4GB",
    "TITAN_PI_UNIT_04": "RASPBERRY_PI_ZERO_2W",
}


def get_swarm_profiles() -> Dict[str, Any]:
    """Return mission profiles for all registered infantry nodes.

    Uses mission_control.assign_mission_profile under the hood so this
    stays in sync with your economic tiers and safety logic.
    """

    profiles: Dict[str, Any] = {}
    for node_id, hw in SWARM_INFANTRY_NODES.items():
        profiles[node_id] = assign_mission_profile(node_id, hw)
    return profiles
