#!/home/titan/TitanNetwork/venv/bin/python3
"""
SI64 Twitter Bot - Credentials Setup Wizard
"""

import os
from pathlib import Path

def setup_credentials():
    """Interactive setup for Twitter credentials"""
    
    print("\n" + "="*70)
    print(" SI64.NET Twitter Bot - Credentials Setup")
    print("="*70)
    print("\nPlease enter your Twitter API credentials:")
    print("(Get these from https://developer.twitter.com/)\n")
    
    api_key = input("API Key: ").strip()
    api_secret = input("API Secret: ").strip()
    access_token = input("Access Token: ").strip()
    access_secret = input("Access Secret: ").strip()
    
    # Verify
    print("\n" + "-"*70)
    print("Credentials Summary:")
    print(f"  API Key: {api_key[:10]}...{api_key[-5:]}")
    print(f"  API Secret: {api_secret[:10]}...{api_secret[-5:]}")
    print(f"  Access Token: {access_token[:10]}...{access_token[-5:]}")
    print(f"  Access Secret: {access_secret[:10]}...{access_secret[-5:]}")
    print("-"*70)
    
    confirm = input("\nSave these credentials? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Setup cancelled")
        return False
    
    # Save to .env.twitter
    env_file = Path("/home/titan/TitanNetwork/.env.twitter")
    content = f"""# SI64.NET Twitter Bot Credentials
# Generated: {__import__('datetime').datetime.now().isoformat()}
SI64_TWITTER_API_KEY={api_key}
SI64_TWITTER_API_SECRET={api_secret}
SI64_TWITTER_ACCESS_TOKEN={access_token}
SI64_TWITTER_ACCESS_SECRET={access_secret}
"""
    
    env_file.write_text(content)
    os.chmod(env_file, 0o600)
    
    print(f"\n✅ Credentials saved to .env.twitter")
    print(f"   File permissions: 600 (read-only by owner)")
    
    return True

if __name__ == "__main__":
    setup_credentials()
