# SI64.NET Twitter Bot - Setup Complete ✅

## Quick Start

```bash
# Launch the bot (interactive menu)
cd /home/titan/TitanNetwork
./run_twitter_bot.sh

# Or run directly with credentials loaded
cd /home/titan/TitanNetwork
export $(cat .env.twitter | grep -v '^#' | xargs)
./si64_twitter_bot.py
```

## Authentication Status ✅
- **Account**: @SI64net
- **API Key**: Authenticated
- **Access Level**: Full read/write access

## Bot Features

### 1. **Manual Posting**
- **Post Status Update**: Real-time SI64 network metrics
- **Post Promotion**: Custom SI64.net promotional tweets
- **Feature Highlights**: Showcase specific SI64 capabilities
- **Community Milestones**: Announce achievements
- **Tweet Threads**: Multi-tweet stories with threading

### 2. **Auto-Posting Scheduler**
- Post status updates automatically on interval
- Configurable refresh rate (default: 1 hour)
- Toggle on/off from CLI menu
- Daemon process (runs in background)

### 3. **Analytics & Monitoring**
- Track total posts sent
- Record last broadcast time
- Store statistics locally
- View bot configuration

### 4. **Daily Digest**
Automated thread posting with:
- Network status metrics
- Fleet performance data
- Completion statistics
- Call-to-action

## Commands Menu

```
1 - Post status update
   Posts current SI64 network metrics to Twitter

2 - Post promotion  
   Custom promotional message about SI64.net

3 - Post feature highlight
   Showcase a specific SI64 feature

4 - Post community milestone
   Announce important achievements

5 - Post daily digest
   Auto-generated thread with metrics

6 - Toggle auto-posting
   Enable/disable scheduled tweets

7 - View bot stats
   Show posting history and status

8 - Exit
```

## Configuration Files

### `.env.twitter` (Credentials)
- **Location**: `/home/titan/TitanNetwork/.env.twitter`
- **Permissions**: 600 (read-only by owner)
- **Contains**:
  - API Key
  - API Secret
  - Access Token
  - Access Secret

### Bot Config
- **Location**: `~/.si64_twitter_bot_config.json`
- **Auto-created** on first run
- **Stores**:
  - Posts count
  - Last broadcast time
  - Hashtags
  - Auto-post settings

## Twitter API Requirements

⚠️ **Current Issue**: Account needs Twitter API credits/billing

**To Fix**:
1. Go to https://developer.twitter.com/en/dashboard
2. Upgrade account to paid tier (required for posting)
3. Set up billing in your developer dashboard
4. Bot will work immediately after upgrade

## File Structure

```
/home/titan/TitanNetwork/
├── si64_twitter_bot.py          # Main bot
├── run_twitter_bot.sh           # Launcher
├── setup_twitter_credentials.py # Setup wizard
├── .env.twitter                 # API credentials (secure)
└── .si64_twitter_bot_config.json # Bot config (auto-created)
```

## Example Posts

### Status Update
```
🚀 SI64.NET Network Status Update

Status: operational
Fleet Size: 42 nodes
Completed Jobs: 1,247

Decentralized compute for Web3 🧠⚡

#SI64NET #Web3 #DeFi #Solana
```

### Daily Digest Thread
```
(1/4) 📊 SI64.NET Daily Digest 📊
Here's what happened in the network today...

(2/4) 🔗 Network Status
• Status: operational
• Active Nodes: 42
• Jobs Processed: 1,247

(3/4) ⚡ Performance Metrics
• Compute Hours: 485.3h
• Uptime: 288h
• Network Health: Optimal ✅

(4/4) 🚀 Join the Revolution!
SI64.NET is building the future of decentralized AI compute.
Participate today! 🧠⚡
```

## Integration with Master Control

The Twitter bot can be integrated into the Master Control UI:
1. Add "Social Media" button to sidebar
2. Display bot status in SI64 dashboard
3. Direct posting from Master Control menus

## Troubleshooting

### "Not Authenticated" Error
```bash
# Verify credentials
cat /home/titan/TitanNetwork/.env.twitter

# Test connection
cd /home/titan/TitanNetwork
export $(cat .env.twitter | grep -v '^#' | xargs)
python3 si64_twitter_bot.py
```

### Rate Limiting
- Tweepy automatically handles rate limits
- `wait_on_rate_limit=True` enabled
- Bot will pause and retry

### Payment Required Error
- Twitter API requires paid tier for posting
- Upgrade account in developer dashboard
- Free tier for testing/read-only

## Automation Options

### Option 1: Systemd Service
Create `/etc/systemd/user/si64-twitter-bot.service`
```ini
[Unit]
Description=SI64 Twitter Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/titan/TitanNetwork
ExecStart=/home/titan/TitanNetwork/run_twitter_bot.sh
Restart=on-failure

[Install]
WantedBy=default.target
```

### Option 2: Cron Job
```bash
# Post daily digest at 9 AM
0 9 * * * cd /home/titan/TitanNetwork && \
           export $(cat .env.twitter | grep -v '^#' | xargs) && \
           python3 -c "from si64_twitter_bot import SI64TwitterBot; \
                       SI64TwitterBot().post_daily_digest()"
```

### Option 3: Master Control Integration
Add button to Master Control sidebar for direct access to bot CLI.

## Next Steps

1. ✅ Upgrade Twitter account to paid API tier
2. ✅ Run bot and test posting
3. ✅ Configure auto-posting schedule
4. ✅ Integrate with Master Control (optional)
5. ✅ Set up daily digest automation
