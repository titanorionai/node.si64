#!/bin/bash
# SI64.NET Twitter Bot Launcher
# Loads credentials and runs the bot

cd "$(dirname "$0")"

# Load Twitter credentials
if [ -f .env.twitter ]; then
    export $(cat .env.twitter | grep -v '^#' | xargs)
    echo "✅ Twitter credentials loaded"
else
    echo "❌ .env.twitter file not found"
    exit 1
fi

# Run the bot with the correct Python interpreter
/home/titan/TitanNetwork/venv/bin/python3 ./si64_twitter_bot.py
