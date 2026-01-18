#!/home/titan/TitanNetwork/venv/bin/python3
"""
SI64.NET Twitter Bot
Dedicated social media management and PR for SI64.net
"""

import os
import tweepy
import time
import json
import requests
from datetime import datetime
from pathlib import Path
import threading
from typing import Optional, List

from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load .env from project root so credentials can be managed there
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Twitter API Credentials (from environment variables)
# Primary: SI64_* variables for this dedicated bot
# Fallback: X_* variables used by the Vanguard/Juggernaut bot
TWITTER_API_KEY = os.environ.get("2aALDMA6AZ7Z81PVscM0hA80M") or os.environ.get("X_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("xF6fRl8r0SBXczIvDUkzSV2J2TJGkD9Qf0nGIsFEbMWvrCnjdu") or os.environ.get("X_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("2012611893857271808-WkIhwbPj8mNx2WZzvUjfKpd5kw3tCW") or os.environ.get("X_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("lb4kDmeXBGH0PdYfugmiXlG055FKitr0vQp3SkCwMuhhz") or os.environ.get("X_ACCESS_SECRET", "")

# SI64 API
SI64_API_URL = "http://127.0.0.1:8000"

# Config file
CONFIG_FILE = Path.home() / ".si64_twitter_bot_config.json"

# ============================================================================
# TWITTER CLIENT
# ============================================================================

class SI64TwitterBot:
    """SI64.net Twitter Bot - Social Media Management and PR"""
    
    def __init__(self):
        self.authenticated = False
        self.client = None
        self.api = None
        self.config = self._load_config()
        self._initialize_twitter()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return json.load(f)
        return {
            "last_broadcast": None,
            "posts_count": 0,
            "hashtags": ["#SI64NET", "#Web3", "#DeFi", "#Solana"],
            "promote_interval": 3600,  # 1 hour
            "enable_auto_post": False,
        }
    
    def _save_config(self):
        """Save configuration to file"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _initialize_twitter(self) -> bool:
        """Initialize Twitter API connection"""
        try:
            if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
                print("⚠️  Twitter credentials not configured")
                print("   Set environment variables:")
                print("   - SI64_TWITTER_API_KEY")
                print("   - SI64_TWITTER_API_SECRET")
                print("   - SI64_TWITTER_ACCESS_TOKEN")
                print("   - SI64_TWITTER_ACCESS_SECRET")
                return False
            
            # Initialize v2 client (for posting)
            self.client = tweepy.Client(
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET,
                wait_on_rate_limit=True
            )
            
            # Initialize v1.1 API (for additional features)
            auth = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY,
                TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN,
                TWITTER_ACCESS_SECRET
            )
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Verify credentials
            user = self.client.get_me()
            if user:
                self.authenticated = True
                print(f"✅ Twitter Bot Authenticated as @{user.data.username}")
                return True
        except tweepy.TweepyException as e:
            print(f"❌ Twitter Authentication Failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Error initializing Twitter: {e}")
            return False
    
    # ========================================================================
    # POSTING FUNCTIONS
    # ========================================================================
    
    def post_tweet(self, text: str, reply_to_id: Optional[int] = None) -> Optional[str]:
        """Post a tweet"""
        if not self.authenticated:
            print("❌ Not authenticated with Twitter")
            return None
        
        try:
            response = self.client.create_tweet(
                text=text,
                reply_settings="everyone",
                in_reply_to_tweet_id=reply_to_id
            )
            tweet_id = response.data['id']
            self.config["posts_count"] += 1
            self.config["last_broadcast"] = datetime.now().isoformat()
            self._save_config()
            print(f"✅ Tweet posted: {tweet_id}")
            return tweet_id
        except tweepy.TweepyException as e:
            print(f"❌ Failed to post tweet: {e}")
            return None
    
    def post_si64_status_update(self) -> Optional[str]:
        """Post SI64.net network status update"""
        try:
            response = requests.get(f"{SI64_API_URL}/api/stats", timeout=3)
            if response.status_code != 200:
                print("⚠️  Cannot fetch SI64 stats")
                return None
            
            data = response.json()
            
            status = data.get("status", "unknown")
            fleet = data.get("fleet_size", 0)
            jobs = data.get("jobs_completed", 0)
            
            text = f"""🚀 SI64.NET Network Status Update

Status: {status}
Fleet Size: {fleet} nodes
Completed Jobs: {jobs}

Decentralized compute for Web3 🧠⚡

#SI64NET #Web3 #DeFi #Solana"""
            
            return self.post_tweet(text)
        except Exception as e:
            print(f"❌ Error posting status: {e}")
            return None
    
    def post_promotion(self, message: str) -> Optional[str]:
        """Post SI64.net promotion"""
        hashtags = " ".join(self.config.get("hashtags", ["#SI64NET"]))
        
        text = f"""{message}

🔗 https://si64.net
⚡ Decentralized compute network
🧠 AI + Web3 infrastructure

{hashtags}"""
        
        return self.post_tweet(text)
    
    def post_feature_highlight(self, feature: str, description: str) -> Optional[str]:
        """Highlight a SI64 feature"""
        text = f"""✨ SI64.NET Feature Highlight: {feature}

{description}

Join the decentralized computing revolution 🚀

#SI64NET #Web3 #DeFi"""
        
        return self.post_tweet(text)
    
    def post_community_milestone(self, milestone: str, details: str) -> Optional[str]:
        """Post community milestone"""
        text = f"""🎉 SI64.NET Community Milestone!

{milestone}

{details}

Thank you to our amazing community! 🙏

#SI64NET #Web3Community"""
        
        return self.post_tweet(text)
    
    def post_thread(self, tweets: List[str]) -> Optional[List[str]]:
        """Post a thread of tweets"""
        tweet_ids = []
        reply_to = None
        
        for i, tweet_text in enumerate(tweets):
            try:
                response = self.client.create_tweet(
                    text=tweet_text,
                    reply_settings="everyone",
                    in_reply_to_tweet_id=reply_to
                )
                tweet_id = response.data['id']
                tweet_ids.append(tweet_id)
                reply_to = tweet_id
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"❌ Failed to post thread tweet {i+1}: {e}")
                break
        
        if tweet_ids:
            self.config["posts_count"] += len(tweet_ids)
            self.config["last_broadcast"] = datetime.now().isoformat()
            self._save_config()
            print(f"✅ Posted {len(tweet_ids)} tweets in thread")
        
        return tweet_ids if tweet_ids else None
    
    # ========================================================================
    # ANALYTICS & MONITORING
    # ========================================================================
    
    def get_bot_stats(self) -> dict:
        """Get bot statistics"""
        return {
            "authenticated": self.authenticated,
            "posts_count": self.config.get("posts_count", 0),
            "last_broadcast": self.config.get("last_broadcast"),
            "auto_post_enabled": self.config.get("enable_auto_post", False),
        }
    
    def set_auto_posting(self, enabled: bool, interval: int = 3600):
        """Enable/disable auto posting"""
        self.config["enable_auto_post"] = enabled
        self.config["promote_interval"] = interval
        self._save_config()
        print(f"{'✅' if enabled else '⏸️ '} Auto-posting {'enabled' if enabled else 'disabled'}")
    
    # ========================================================================
    # AUTO POSTING SCHEDULER
    # ========================================================================
    
    def start_auto_scheduler(self):
        """Start background auto-posting scheduler"""
        if not self.authenticated:
            print("❌ Cannot start scheduler: not authenticated")
            return
        
        def scheduler():
            print("🤖 SI64 Twitter Bot scheduler started")
            while self.config.get("enable_auto_post", False):
                try:
                    # Post status update
                    self.post_si64_status_update()
                    
                    # Wait for next interval
                    interval = self.config.get("promote_interval", 3600)
                    for _ in range(interval // 60):
                        if not self.config.get("enable_auto_post"):
                            break
                        time.sleep(60)
                except Exception as e:
                    print(f"❌ Scheduler error: {e}")
                    time.sleep(300)
        
        thread = threading.Thread(target=scheduler, daemon=True)
        thread.start()
        print("✅ Auto-posting scheduler started (background)")

    # ========================================================================
    # BATCH POSTING
    # ========================================================================
    
    def post_daily_digest(self) -> Optional[List[str]]:
        """Post daily digest thread"""
        try:
            response = requests.get(f"{SI64_API_URL}/api/stats", timeout=3)
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            thread_tweets = [
                f"""📊 SI64.NET Daily Digest 📊

Here's what happened in the decentralized compute network today:

(1/4)""",
                
                f"""🔗 Network Status
• Status: {data.get('status', 'Unknown')}
• Active Nodes: {data.get('fleet_size', 0)}
• Jobs Processed: {data.get('jobs_completed', 0)}

(2/4)""",
                
                f"""⚡ Performance Metrics
• Compute Hours: {data.get('total_compute_hours', 0):.1f}h
• Uptime: {data.get('uptime_seconds', 0) // 3600}h
• Network Health: Optimal ✅

(3/4)""",
                
                """🚀 Join the Revolution!

SI64.NET is building the future of decentralized AI compute. 
Participate today! 🧠⚡

#SI64NET #Web3 #DeFi

(4/4)"""
            ]
            
            return self.post_thread(thread_tweets)
        except Exception as e:
            print(f"❌ Error posting digest: {e}")
            return None


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Interactive CLI for the bot"""
    bot = SI64TwitterBot()
    
    if not bot.authenticated:
        print("\n⚠️  Bot not authenticated. Please configure Twitter API credentials.")
        print("See instructions above.\n")
        return
    
    print("\n" + "="*70)
    print(" SI64.NET TWITTER BOT - Social Media Management")
    print("="*70)
    
    while True:
        print("\n📱 Commands:")
        print("  1 - Post status update")
        print("  2 - Post promotion")
        print("  3 - Post feature highlight")
        print("  4 - Post community milestone")
        print("  5 - Post daily digest")
        print("  6 - Toggle auto-posting")
        print("  7 - View bot stats")
        print("  8 - Exit")
        
        choice = input("\n> Select: ").strip()
        
        if choice == "1":
            bot.post_si64_status_update()
        
        elif choice == "2":
            msg = input("📝 Promotion message: ").strip()
            if msg:
                bot.post_promotion(msg)
        
        elif choice == "3":
            feature = input("✨ Feature name: ").strip()
            desc = input("📝 Description: ").strip()
            if feature and desc:
                bot.post_feature_highlight(feature, desc)
        
        elif choice == "4":
            milestone = input("🎉 Milestone: ").strip()
            details = input("📝 Details: ").strip()
            if milestone and details:
                bot.post_community_milestone(milestone, details)
        
        elif choice == "5":
            bot.post_daily_digest()
        
        elif choice == "6":
            enabled = bot.config.get("enable_auto_post", False)
            new_state = not enabled
            bot.set_auto_posting(new_state)
            if new_state:
                bot.start_auto_scheduler()
        
        elif choice == "7":
            stats = bot.get_bot_stats()
            print("\n📊 Bot Statistics:")
            for key, val in stats.items():
                print(f"  {key}: {val}")
        
        elif choice == "8":
            print("👋 Exiting...")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()
