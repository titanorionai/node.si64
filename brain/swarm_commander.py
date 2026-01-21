"""
TITAN PROTOCOL | SWARM COMMANDER (V4.0)
=======================================
Authority: Central Command
Classification: RESTRICTED
Description: Advanced logic for hardware segmentation and mission routing.
"""

import logging
import os
import json
import asyncio
from enum import Enum
from typing import Dict, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field

# --- MIL-SPEC LOGGING ---
logger = logging.getLogger("TITAN_SWARM")

class HardwareClass(str, Enum):
    JETSON_ORIN = "UNIT_ORIN_AGX"
    APPLE_SILICON = "UNIT_APPLE_M_SERIES"
    STD_GPU = "UNIT_NVIDIA_CUDA"

class MissionTier(str, Enum):
    ALPHA = "TIER_ALPHA_PRIORITY"
    BETA = "TIER_BETA_STANDARD"
    GAMMA = "TIER_GAMMA_IDLE"

class JobDirective(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    tier: MissionTier
    hardware_req: HardwareClass
    payload: Dict[str, Any]
    timestamp: float = Field(default_factory=lambda: asyncio.get_event_loop().time())

class SwarmCommander:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.active_uplinks: Dict[str, Any] = {}
        self.logger = logging.getLogger("TITAN_SWARM")

    async def commission_unit(self, websocket, node_id: str, hardware_type: HardwareClass):
        """
        Activates a worker node and assigns it to a specific hardware pool.
        Performs atomic registration in the Redis backend.
        """
        try:
            self.active_uplinks[node_id] = websocket
            pool_key = f"pool:{hardware_type.value}:active"

            # If this is the ORIN genesis unit, remove stale ORIN entries from the pool
            if node_id.startswith("ORIN_GENESIS_001"):
                try:
                    existing = await self.redis.smembers(pool_key)
                    ghosts = [n for n in existing if n.startswith("ORIN_GENESIS_001") and n != node_id]
                except Exception:
                    ghosts = []

            # Atomic Registration: remove ghosts (if any) and add this node
            try:
                async with self.redis.pipeline() as pipe:
                    # Remove legacy ORIN genesis ghosts from global active set and pool
                    if node_id.startswith("ORIN_GENESIS_001") and ghosts:
                        for g in ghosts:
                            pipe.srem("active_nodes", g)
                            pipe.srem(pool_key, g)
                            self.logger.info(f"REAPED GHOST ORIN ENTRY: {g}")

                    pipe.sadd("active_nodes", node_id)
                    pipe.sadd(pool_key, node_id)
                    await pipe.execute()
                # Set a last-seen timestamp with TTL so reaper can detect stale nodes
                try:
                    ttl = int(os.getenv("TITAN_NODE_TTL_S", "120"))
                    now = asyncio.get_event_loop().time()
                    await self.redis.set(f"node:last_seen:{node_id}", str(now))
                    await self.redis.expire(f"node:last_seen:{node_id}", ttl)
                except Exception:
                    pass
            except Exception as e:
                self.logger.error(f"COMMISSION FAILURE ({node_id}): {e}")
                return False

            self.logger.info(f"UNIT COMMISSIONED: {node_id} assigned to [ {hardware_type.value} ]")
            return True
        except Exception as e:
            self.logger.error(f"COMMISSION FAILURE ({node_id}): {e}")
            return False

    async def decommission_unit(self, node_id: str, hardware_type: HardwareClass):
        """
        Honorable discharge of a unit from the active grid.
        Cleans up all registry entries to prevent ghost routing.
        """
        if node_id in self.active_uplinks:
            del self.active_uplinks[node_id]
            
        pool_key = f"pool:{hardware_type.value}:active"
        
        try:
            async with self.redis.pipeline() as pipe:
                pipe.srem("active_nodes", node_id)
                pipe.srem(pool_key, node_id)
                await pipe.execute()
            self.logger.info(f"UNIT DECOMMISSIONED: {node_id}")
        except Exception as e:
            self.logger.error(f"DECOMMISSION ERROR {node_id}: {e}")

    async def dispatch_mission(self, directive: JobDirective):
        """
        Routes a job to the correct hardware queue based on classification.
        Broadcasts a Pub/Sub signal to wake up idle workers.
        """
        target_pool = directive.hardware_req.value
        queue_key = f"queue:{target_pool}"
        channel_key = f"signal:{target_pool}"
        
        try:
            # Pydantic v1/v2 compatibility serialization
            try:
                payload_json = directive.model_dump_json()
            except AttributeError:
                payload_json = directive.json()
            
            # Push to the head of the hardware-specific queue
            await self.redis.lpush(queue_key, payload_json)
            self.logger.info(f"MISSION LOGGED: {directive.job_id} >> {queue_key}")
            
            # Notify idle workers via Real-Time Signal
            await self._broadcast_signal(channel_key, "NEW_INTEL_AVAILABLE")
            return directive.job_id
        except Exception as e:
            self.logger.critical(f"DISPATCH FAILURE: {e}")
            return None

    async def _broadcast_signal(self, channel: str, message: str):
        """Internal signaling mechanism"""
        try:
            await self.redis.publish(channel, message)
        except Exception: pass
