#!/usr/bin/env python3
"""
VANGUARD ENTRYPOINT - SI64 Twitter Bot Container Initialization
Handles startup, credential loading, and operational directives
"""

import os
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/vanguard.log')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONTAINER CONFIGURATION
# ============================================================================

# Bot operational directives
BOT_MODE = os.environ.get("BOT_MODE", "STANDARD_GROWTH")
BOT_DIRECTIVE = os.environ.get("BOT_DIRECTIVE", "COMMUNITY_ENGAGEMENT")
POST_INTERVAL_SEC = int(os.environ.get("POST_INTERVAL_SEC", "1800"))  # 30 min default
REPLY_PROBABILITY = float(os.environ.get("REPLY_PROBABILITY", "0.85"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# External service URLs
TITAN_BRAIN_URL = os.environ.get("TITAN_BRAIN_URL", "http://titan-brain:8000")
TITAN_OLLAMA_URL = os.environ.get("TITAN_OLLAMA_URL", "http://titan-ollama-engine:11434")

# Twitter/X API Credentials (loaded from .env)
TWITTER_API_KEY = os.environ.get("X_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("X_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")

# System telemetry
MAX_NET_RETRIES = int(os.environ.get("MAX_NET_RETRIES", "5"))


def validate_environment():
    """Validate required environment variables and credentials"""
    logger.info("=" * 70)
    logger.info(" VANGUARD UNIT | SI64 Twitter Bot Container")
    logger.info(" [TACTICAL] Psychological Warfare & Community Growth Division")
    logger.info("=" * 70)
    logger.info("")
    
    # Credentials check (optional): proceed even if missing for blind firing
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        logger.warning("⚠️ Credentials not fully set (X_API_*). Proceeding in blind-fire mode.")
    else:
        logger.info("✅ Twitter credentials loaded (X_API_*).")
    
    # Log operational parameters
    logger.info(f"📋 OPERATIONAL DIRECTIVES:")
    logger.info(f"   Mode: {BOT_MODE}")
    logger.info(f"   Directive: {BOT_DIRECTIVE}")
    logger.info(f"   Post Interval: {POST_INTERVAL_SEC}s ({POST_INTERVAL_SEC//60}m)")
    logger.info(f"   Reply Probability: {REPLY_PROBABILITY*100:.0f}%")
    logger.info(f"   Log Level: {LOG_LEVEL}")
    logger.info(f"   Max Retries: {MAX_NET_RETRIES}")
    logger.info(f"   Brain URL: {TITAN_BRAIN_URL}")
    logger.info(f"   Ollama URL: {TITAN_OLLAMA_URL}")
    logger.info("")
    
    return True


def wait_for_services(max_retries=30):
    """Wait for dependent services to be healthy"""
    import requests
    
    logger.info("🔗 Checking service connectivity...")
    
    services = {
        "BRAIN": TITAN_BRAIN_URL,
        "OLLAMA": TITAN_OLLAMA_URL,
    }
    
    for attempt in range(max_retries):
        all_ready = True
        
        for service_name, url in services.items():
            try:
                response = requests.get(f"{url}/health" if service_name == "BRAIN" else url, 
                                       timeout=2)
                logger.info(f"   ✅ {service_name} ready")
            except Exception as e:
                all_ready = False
                logger.warning(f"   ⏳ {service_name} not ready ({attempt+1}/{max_retries})")
        
        if all_ready:
            logger.info("✅ All services healthy - starting bot...")
            return True
        
        time.sleep(1)
    
    logger.warning("⚠️  Services not fully healthy, proceeding anyway...")
    return False


def launch_bot():
    """Launch the Twitter bot"""
    try:
        import subprocess
        
        logger.info("⚡ Initializing TITAN VANGUARD | JUGGERNAUT V5.0...")
        logger.info("🎯 Mission: Network Dominance via Twitter/X")
        logger.info("")
        
        # Start bot in subprocess
        bot_process = subprocess.Popen(
            [sys.executable, "/app/vanguard_bot.py"],
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )
        
        logger.info("✅ JUGGERNAUT CLASS V5.0 INITIALIZED")
        logger.info(f"   Bot Process ID: {bot_process.pid}")
        logger.info("🚀 VANGUARD UNIT OPERATIONAL - NEURAL NETWORK ACTIVE")
        logger.info("")
        
        # Wait for process to complete
        bot_process.wait()
        return bot_process.returncode == 0
        
    except Exception as e:
        logger.error(f"❌ Bot launch failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main container entrypoint"""
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Wait for services
    wait_for_services()
    
    # Launch bot
    if launch_bot():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
