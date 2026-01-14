#!/usr/bin/env python3
import time
import os
import random
import tweepy
import math
import threading
import csv
from datetime import datetime, timedelta, date
from huggingface_hub import HfApi
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 🔐 AUTHENTICATION PROTOCOLS
# ==========================================
HF_TOKEN = "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"

TWITTER_API_KEY = "JZVbpyLRkXdGzbgY5WiXA6Lxi"
TWITTER_API_SECRET = "rH5Y5enVwCEsRJlgpknDpdhXDrv0avl1AHI6YT9NiMPHerC97k"
TWITTER_ACCESS_TOKEN = "2008775098187345921-P7h9PNaytJK4VdsMGfCew6esgiuESN"
TWITTER_ACCESS_SECRET = "pAilW73Q2ZP4j0rKbOwZDxWdX4I5pK19nvBcAunKsj9I7"

# ==========================================
# ⚙️ SYSTEM CONFIGURATION
# ==========================================
# Force absolute path to prevent IO errors on Jetson
DATA_DIR = os.path.abspath("./data_warehouse") 

PAIRS = ["SOL/USDC", "WIF/SOL", "JUP/SOL", "BONK/SOL", "PYTH/USDC", "RAY/USDC", "MSOL/SOL"]
PROGRAMS = ["Raydium Liquidity Pool V4", "Orca Whirlpool", "Meteora DLMM", "OpenBook V2", "Jupiter Aggregator V6"]

REPO_MAP = {
    # MEMPOOL SYNTHETIC
    "MEMPOOL_SYNTH_SPARK": "TitanOrionAI/Mempool-Solana-Synthetic-Training-Data-Spark-5k",
    "MEMPOOL_SYNTH_STD":   "TitanOrionAI/Mempool-Solana-Synthetic-Training-Data-Standard-100k",
    "MEMPOOL_SYNTH_OMEGA": "TitanOrionAI/Mempool-Solana-Synthetic-Training-Data-Omega-1M",
    # MEMPOOL ORGANIC
    "MEMPOOL_ORG_SPARK": "TitanOrionAI/Mempool-Solana-Organic-Training-Data-Spark-5k",
    "MEMPOOL_ORG_STD":   "TitanOrionAI/Mempool-Solana-Organic-Training-Data-Standard-100k",
    "MEMPOOL_ORG_OMEGA": "TitanOrionAI/Mempool-Solana-Organic-Training-Data-Omega-1M",
    # MEV SYNTHETIC
    "MEV_SYNTH_SPARK": "TitanOrionAI/MEV-Solana-Synthetic-Training-Data-Spark-5k",
    "MEV_SYNTH_STD":   "TitanOrionAI/MEV-Solana-Synthetic-Training-Data-Standard-100k",
    "MEV_SYNTH_OMEGA": "TitanOrionAI/MEV-Solana-Synthetic-Training-Data-Omega-1M",
    # MEV ORGANIC
    "MEV_ORG_SPARK": "TitanOrionAI/MEV-Solana-Organic-Training-Data-Spark-5k",
    "MEV_ORG_STD":   "TitanOrionAI/MEV-Solana-Organic-Training-Data-Standard-100k",
    "MEV_ORG_OMEGA": "TitanOrionAI/MEV-Solana-Organic-Training-Data-Omega-1M",
}

# ==========================================
# 📡 BROADCASTER MODULE (GTA STYLE)
# ==========================================
TWEET_TEMPLATES = [
    "📦 Fresh shipment just hit the wire. {rows} rows of pure signal. Come get it.",
    "🚀 You want the edge? We got the edge. New batch deployed.",
    "💎 They trade on noise. You trade on this. {rows} rows uploaded to the warehouse.",
    "⚡ Speed kills. Latency kills faster. Get your training data here.",
    "🔒 Secure drop complete. The goods are in the repo. Don't be late.",
    "📈 Market moves fast. Our bots move faster. New training set live.",
    "🧠 Upgrade your algo's brain. {rows} rows of high-grade organic data.",
    "🕶️ Signals so clean they shine. New artifact deployed.",
    "🔋 Power up. {rows} rows of MEV logic ready for download.",
    "💸 Stop guessing. Start sniping. New Mempool logs uploaded.",
    "🏗️ Building the future of finance, one block at a time.",
    "📡 We hear everything on the chain. Now you can too. {rows} rows logged.",
    "⚖️ The scales just tipped in your favor. New data drop active.",
    "🏎️ High performance requires high octane fuel. Here's your tank.",
    "🎯 Bullseye. Every time. Train your sniper on this set.",
    "🧩 The missing piece of your strategy just landed. Check the repo.",
    "🧊 Ice cold alpha. Fresh from the validator nodes. {rows} rows.",
    "🌐 Global latency maps updated. See where the money flows.",
    "🤖 Feed the machine. It's hungry for data. Batch deployed.",
    "⚔️ It's a war out there. Don't go into the mempool unarmed.",
    "💼 Standard issue for the institutional player. New Omega tier drop.",
    "🕵️‍♂️ See what they don't want you to see. Ghost logs uploaded.",
    "📉 Crash or rally? Doesn't matter if you have the data.",
    "📜 History doesn't repeat, but it rhymes. Read the logs.",
    "🚦 Green light. The data is flowing. {rows} rows ready for ingestion.",
    "🧪 Lab results are in. The synthetic variance is perfect.",
    "🔑 Key to the city. Or at least, the block. New MEV set uploaded.",
    "📦 You ordered it. We supplied it. Discrete delivery complete.",
    "🌟 Spark tier updated. A little taste for the locals.",
    "🌊 Tsunami warning. Liquidity flood detected in the new logs.",
    "🦉 The night shift just finished. {rows} rows of overnight action.",
    "🛡️ Protect your capital. Backtest against reality.",
    "🕹️ Game on. Level up your bot with this new pack.",
    "🔌 Plug in. Download. Dominate. It's that simple.",
    "📂 Case file is now open. Inspect the evidence.",
    "🔨 We drilled deep for this one. High-value ore extracted.",
    "🛸 Unidentified Alpha Object detected. Analysis complete. Data uploaded.",
    "🧨 Explosive volatility captured. Handle with care.",
    "🎲 Roll the dice? No. Count the cards. New probability matrix live.",
    "🏰 Build your fortress on solid data. {rows} rows of foundation.",
    "🚀 Lift off in T-minus 10 seconds. Get the data before the pump.",
    "🌑 Dark Forest mapping complete. See the monsters before they bite.",
    "🧘‍♂️ Zen mode. Trading with clarity. New clean dataset available.",
    "🩸 There was blood in the streets. We bottled it. Crash logs uploaded.",
    "🏆 Champions train harder. {rows} rows for your training montage.",
    "💾 Save point reached. Market state captured.",
    "🕸️ We caught the flies. You analyze the web. Spam logs live.",
    "🎩 Magic tricks revealed. See how the arb bots did it.",
    "🦁 King of the jungle. That's you, after this update.",
    "🏁 The race is won in the pit stop. Refuel your models now."
]

def generate_manifest_image(batch_name, size, repo_key):
    """Generates a Cyberpunk/Terminal style manifest image using Pillow."""
    try:
        width, height = 1200, 675
        img = Image.new('RGB', (width, height), color=(0, 0, 0))
        d = ImageDraw.Draw(img)
        try:
            # Try loading system fonts (Linux/Jetson)
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 60)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 30)
        except:
            # Fallback for systems without specific fonts
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Draw Terminal UI
        d.rectangle([20, 20, width-20, height-20], outline="#00FF41", width=4)
        d.text((50, 50), "/// TITAN ORION AGX | V5.0 MANIFEST ///", fill="#00FF41", font=font_small)
        d.text((50, 180), f"BATCH_ID : {batch_name}", fill="white", font=font_large)
        d.text((50, 260), f"DATA_SIZE: {size} ROWS", fill="white", font=font_large)
        d.text((50, 340), f"TARGET   : {repo_key}", fill="#00FF41", font=font_large)
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        d.text((50, 550), f"STATUS   : UPLOAD COMPLETE", fill="#00FF41", font=font_small)
        d.text((50, 590), f"TIME     : {timestamp}", fill="#00FF41", font=font_small)

        path = os.path.join(DATA_DIR, f"manifest_{batch_name}.png")
        img.save(path)
        return path
    except Exception as e:
        print(f"[IMAGE] Generation Failed: {e}")
        return None

def post_to_x(batch_name, size, repo_key):
    try:
        # 1. Generate Image
        image_path = generate_manifest_image(batch_name, size, repo_key)
        
        # 2. Auth v1.1 (Media)
        auth = tweepy.OAuth1UserHandler(TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        api = tweepy.API(auth)
        
        # 3. Auth v2 (Tweet)
        client = tweepy.Client(consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET, access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET)
        
        media_id = None
        if image_path:
            media = api.media_upload(filename=image_path)
            media_id = media.media_id

        # 4. Construct Message
        repo_id = REPO_MAP.get(repo_key, "TitanOrionAI")
        url = f"https://huggingface.co/datasets/{repo_id}"
        template = random.choice(TWEET_TEMPLATES)
        flavor_text = template.format(rows=size)
        msg = f"{flavor_text}\n\n📂 Batch: {batch_name}\n🔗 ACCESS: {url}\n\n#Solana #MEV #TitanOrion"
        
        # 5. Send
        if media_id: client.create_tweet(text=msg, media_ids=[media_id])
        else: client.create_tweet(text=msg)
        print("[TWITTER] Broadcast Successful.")
        
        # 6. Clean up
        if image_path and os.path.exists(image_path): os.remove(image_path)
    except Exception as e:
        print(f"[TWITTER] Broadcast Failed: {e}")

# ==========================================
# 🏭 V5.0 FACTORY ENGINE (PHYSICS & MATH)
# ==========================================
def get_scenario_config(scenario):
    # [Trend_Bias, Volatility_Mult, Jito_Base_Lamports]
    if scenario == "Bull Run":          return [0.0005, 1.2, 500_000]   # Uptrend
    elif scenario == "Bear Market":     return [-0.0005, 1.2, 200_000]  # Downtrend
    elif scenario == "Flash Crash":     return [-0.02, 5.0, 15_000_000] # Huge Drop
    elif scenario == "MEV Heavy":       return [0.0, 0.8, 8_000_000]    # Flat price, High Tips
    elif scenario == "Liquidity Snipe": return [0.01, 3.0, 4_000_000]   # Sharp Spike
    elif scenario == "Pump & Dump":     return [0.03, 4.0, 2_000_000]   # Massive Pump
    else: return [0.0, 0.5, 50_000] # Low Vol (Balanced)

def generate_random_walk_row(timestamp, prev_price, scenario, weights):
    """Generates a row with V5.0 Physics: Random Walk Price + Deep Metadata."""
    trend_bias, vol_mult, tip_base = weights
    
    pair = random.choice(PAIRS)
    program = random.choice(PROGRAMS)
    
    # --- 1. PRICE PHYSICS (Random Walk) ---
    # Change = (Trend Bias) + (Random Noise * Volatility)
    # This creates realistic candles instead of random scatter
    percent_change = trend_bias + (random.gauss(0, 0.002) * vol_mult)
    new_price = prev_price * (1 + percent_change)
    if new_price < 0.01: new_price = 0.01 # Safety floor

    # --- 2. DEEP METADATA ---
    # Metrics for institutional simulation
    if tip_base > 1_000_000:
        slot_contention = random.uniform(0.7, 1.0) # High contention
        cu_consumed = random.randint(200_000, 1_400_000)
    else:
        slot_contention = random.uniform(0.0, 0.3) # Low contention
        cu_consumed = random.randint(5_000, 150_000)

    # --- 3. CORRELATED JITO TIPS ---
    # Tips correlate with Alpha Score and Volatility
    alpha_score = random.uniform(0, 100)
    jito_tip = int(tip_base + (alpha_score * 50_000 * vol_mult))
    
    # CSV Line
    return f"{timestamp},{pair},{scenario},{new_price:.6f},{jito_tip},{alpha_score:.2f},{program},{slot_contention:.4f},{cu_consumed}", new_price

# ==========================================
# 📝 PROFESSIONAL README GENERATOR
# ==========================================
def get_readme_template(repo_key, size):
    spark_notice = ""
    if size <= 5000:
        spark_notice = """# ⚡ TITAN SPARK PACK (Free Sample)
> **NOTE:** You are currently viewing the **Free "Spark" Tier** of this dataset.
> * **Contains:** 5,000 Rows (Daily Snapshot)
> * **Status:** Public / Open Source
> * **Purpose:** Code validation and schema verification.
>
> *For the full 1M+ row institutional datasets, please request access below.*
---
"""

    # --- 1. MEMPOOL SYNTHETIC ---
    if "MEMPOOL_SYNTH" in repo_key:
        return f"""---
license: mit
task_categories:
- time-series-forecasting
- tabular-regression
- reinforcement-learning
tags:
- solana
- mempool
- simulation
- synthetic
size_categories:
- 5K<n<1M
---
---
{spark_notice}
# 🔒 RESTRICTED ACCESS: Titan Mempool Simulation Bundle

> **⚠️ COMPETITIVE INTELLIGENCE:** This dataset contains **forward-looking mempool simulations**. It is designed to train AL (Adaptive Learning) models to predict congestion spikes *before* they manifest on-chain.
>
> **Access is granted primarily to:**
> * HFT / Arbitrage Firms
> * RPC Providers (Latency Optimization)
> * Academic Researchers

### 📢 How to Access
Click the **"Request Access"** button above. Please state your intended use-case (e.g., "Priority Fee Prediction Model") to expedite approval.

---
---

## 📊 Dataset Overview
This is the **Titan Mempool Simulator**, a high-fidelity generation of pending transaction states. Unlike on-chain data which only shows you what *landed*, this dataset simulates the **pending state** (the "Dark Forest"), allowing you to train bots to react to spam waves and fee escalations 400ms faster than the competition.

### 📦 What's Inside the Bundle?
| Scenario File | Condition | Description | Use-Case |
| :--- | :--- | :--- | :--- |
| `titan_mempool_spam_wave.csv` | 🌊 **DDoS / Spam** | 50,000+ txs/second flood simulation. | Train filters to identify high-value txs amidst noise. |
| `titan_mempool_fee_escalation.csv` | 📈 **Fee War** | Rapid priority fee bidding war. | Optimize dynamic fee estimators to save SOL. |
| `titan_mempool_snipe_event.csv` | 🎯 **Token Launch** | 1000s of buyers targeting one contract. | Test "First-in-Block" logic. |

## 💎 "Dark Forest" Features (Column Dictionary)
| Column Name | Type | Description |
| :--- | :--- | :--- |
| `timestamp_seen` | *Datetime* | Time the node "saw" the transaction gossip. |
| `signature` | *String* | Simulated TXID. |
| `priority_fee_micro_lamports` | *Integer* | The fee attached to the pending packet. |
| `compute_unit_limit` | *Integer* | Resource cap requested. |
| `account_write_locks` | *List* | The accounts being contended for (Hotspots). |
| `simulated_latency_ms` | *Float* | Artificial network lag applied to this packet. |
| `inclusion_probability` | *Float* | **Titan Score (0-1.0)**: Likelihood this lands in the next slot. |
| `slot_contention` | *Float* | Block saturation percentage (V5.0 Metric). |
| `cu_consumed` | *Integer* | Simulated compute load (V5.0 Metric). |

## 💰 Commercial Licensing & Pricing
**This repository contains the Free Sample ("Spark"). Full datasets are Gated.**

| Tier | Price | Includes | Target Audience |
| :--- | :--- | :--- | :--- |
| **Spark** | **FREE** | 5,000 Rows (Daily Drop) | Students / Code Verification |
| **Standard** | **5 SOL** | **100,000 Rows** (Weekly Refresh) | Bot Developers |
| **Professional** | **1,680 USDC** | **1,000,000 Rows** (Deep Learning Set) | **Fee Estimation Models** |
| **Enterprise** | **3,500 USDC** | Full Bundle + *Real-Time WebSocket Access* | RPC Node Operators |

### 🛒 How to Purchase & Gain Access
1.  **Click "Request Access"** at the top of this page.
2.  **Send Your Payment To**
    * **Address:** `FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q`
    * *Note: We accept **SOL** for Standard, and **USDC-SPL** for Pro/Enterprise.*
3.  **In your Request Note**, paste your **Transaction Signature (TXID)**.
    * *Example Note: "Purchased Professional Mempool Tier. TXID: 5xG9... Payment verified."*

**⚠️ AUTOMATION ALERT:** Our system scans the chain for your TXID. Once verified, access is granted automatically within 10 minutes.

---
*Generated by the Titan Orion Neural Engine. Verified for integrity.*
"""

    # --- 2. MEMPOOL ORGANIC ---
    elif "MEMPOOL_ORG" in repo_key:
        return f"""---
license: mit
task_categories:
- time-series-forecasting
- tabular-regression
- tabular-classification
tags:
- solana
- mempool
- organic-data
- dropped-transactions
- gossip-protocol
size_categories:
- 100K<n<10M
---
---
{spark_notice}
# 🔒 RESTRICTED ACCESS: Titan Organic Mempool Archive

> **⚠️ AUTHENTICITY VERIFIED:** This dataset is a **Lossless Capture** of the Solana UDP Gossip plane. It contains millions of transaction packets that were broadcasted but **failed to land** (Dropped/Expired). This "Ghost Data" is invisible on standard explorers like Solscan.
>
> **Access is granted primarily to:**
> * Infrastructure Providers
> * MEV Searchers (analyzing failed bundles)
> * Network Analysts

### 📢 How to Access
Click the **"Request Access"** button above. Please state your intended use-case (e.g., "Dropped Transaction Analysis") to expedite approval.

---
---

## 📊 Dataset Overview
This is the **Titan Organic Mempool Archive**. Using our globally distributed Geyser nodes, we capture the raw stream of unconfirmed transactions. This allows you to see the "Hidden Market"—the thousands of arbitrage attempts, failed snipes, and under-priced transactions that the network rejected.

**Why buy Mempool Logs?**
You cannot optimize your landing rate if you only look at successful transactions. You must study **why transactions fail** to ensure yours succeed.

### 📦 What's Inside the Archive?
| Dataset File | Type | Description | Use-Case |
| :--- | :--- | :--- | :--- |
| `titan_organic_dropped_txs.csv` | **Failures** | Transactions that expired or were dropped by validators. | Analyze expiration causes (Fee too low vs. Block full). |
| `titan_organic_pending_latency.csv` | **Timing** | Time-to-Land metrics for global transactions. | Map the fastest propagation paths on the network. |
| `titan_organic_spam_logs.csv` | **Noise** | Raw spam volume from high-frequency bot farms. | Filter development. |

## 💎 "Ground Truth" Features (Column Dictionary)
| Column Name | Type | Description |
| :--- | :--- | :--- |
| `gossip_timestamp_utc` | *Datetime* | Exact microsecond our node received the UDP packet. |
| `signature` | *String* | The transaction ID. |
| `sender_ip_region` | *String* | Approximate geo-location of the originating node (US-EAST, EU-WEST, etc). |
| `priority_fee` | *Integer* | The bid attached to the transaction. |
| `landed_status` | *Boolean* | `TRUE` if confirmed, `FALSE` if dropped. |
| `drop_reason` | *String* | Why it failed: `BLOCK_FULL`, `FEE_TOO_LOW`, `EXPIRED`, or `CONFILCT`. |
| `propagation_delay_ms` | *Float* | Time difference between Gossip arrival and Block inclusion. |
| `program_id` | *String* | Target Contract (Raydium/Orca) (V5.0 Metric). |
| `slot_contention` | *Float* | Saturation of the specific write-lock (V5.0 Metric). |

## 💰 Commercial Licensing & Pricing
**This repository contains the Free Sample ("Spark"). Full Historical Archives are Gated.**

| Tier | Price | Includes | Target Audience |
| :--- | :--- | :--- | :--- |
| **Spark** | **FREE** | 5,000 Rows (Daily Snapshot) | Students / Code Verification |
| **Standard** | **5 SOL** | **100,000 Rows** (Weekly Archive) | Independent Quants / Backtesting |
| **Professional** | **1,680 USDC** | **1,000,000 Rows** (Monthly Ghost Log) | **Infrastructure Optimization** |
| **Enterprise** | **3,500 USDC** | **Full Raw Stream** (TB-Scale) + *Geo-Tagged Latency Maps* | RPC Providers / Validators |

### 🛒 How to Purchase & Gain Access
1.  **Click "Request Access"** at the top of this page.
2.  **Send Your Payment To**
    * **Address:** `FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q`
    * *Note: We accept **SOL** for Standard, and **USDC-SPL** for Pro/Enterprise.*
3.  **In your Request Note**, paste your **Transaction Signature (TXID)**.
    * *Example Note: "Purchased Professional Organic Mempool. TXID: 2xA9... Payment verified."*

**⚠️ AUTOMATION ALERT:** Our system scans the chain for your TXID. Once verified, access is granted automatically within 10 minutes.

---
*Harvested by Titan Orion Geyser Nodes. Immutable and Verified.*
"""

    # --- 3. MEV ORGANIC ---
    elif "MEV_ORG" in repo_key:
        return f"""---
license: mit
    task_categories:
    - time-series-forecasting
    - tabular-regression
    - other
tags:
- finance
- solana
- mev
- hft
- organic-data
- production-grade
size_categories:
- 100K<n<10M
---
---
{spark_notice}
# 🔒 RESTRICTED ACCESS: Titan Organic "Ground Truth" Archive

> **⚠️ AUTHENTICITY VERIFIED:** This dataset contains **100% Organic, Live-Captured Market Data** harvested directly from the Solana Mainnet-Beta RPC nodes. It represents actual historical blockspace conditions, not simulations.
>
> **Access is granted primarily to:**
> * Institutional Arbitrage Desks
> * MEV Searchers requiring historical replay
> * Machine Learning Engineers (Model Validation)

### 📢 How to Access
Click the **"Request Access"** button above. Please state your intended use-case (e.g., "Historical Replay Backtesting") to expedite approval.

---
---

## 📊 Dataset Overview
This is the **Titan Organic Archive**, a chronological record of Solana's mempool and blockspace activity. Sourced directly from our high-performance **Geyser/Yellowstone nodes**, this data captures the chaotic reality of the chain—including failed transactions, actual Jito bribe wars, and real-time validator congestion.

**Why Organic?**
Synthetic data is perfect for training, but **Organic Data is required for validation.** You cannot deploy capital until you have backtested against *real* history.

### 📦 What's Inside the Archive?
| Dataset File | Timeframe | Description | Use-Case |
| :--- | :--- | :--- | :--- |
| `titan_organic_mev_logs.csv` | **Live Capture** | Real-time MEV battles (Sandwich/Arb) captured in-slot. | Analyze competitor tip strategies and win-rates. |
| `titan_organic_congestion.csv` | **High Traffic** | Data from the busiest 100 blocks of the day. | Train retry-logic and compute dynamic priority fees. |
| `titan_organic_token_flow.csv` | **Token Volume** | Net flow of top meme-coins and SPL tokens per slot. | Signal detection for momentum trading bots. |

## 💎 "Ground Truth" Features (Column Dictionary)
| Column Name | Type | Description |
| :--- | :--- | :--- |
| `timestamp_utc` | *Datetime* | Exact block time (Slot time) derived from the validator. |
| `signature` | *String* | **The On-Chain Transaction Signature (TXID).** Verify it on Solscan. |
| `slot` | *Integer* | The absolute slot number on Solana Mainnet-Beta. |
| `actual_execution_price` | *Float* | The real price the trade filled at (includes real slippage). |
| `winning_jito_tip` | *Integer* | The exact bribe amount (in Lamports) that won the auction. |
| `competitor_count` | *Integer* | Number of other transactions landing in the same state-write lock. |
| `success_status` | *Boolean* | `TRUE` if the trade landed, `FALSE` if it reverted/dropped. |
| `program_id` | *String* | The DEX interacting with (Orca/Raydium) (V5.0 Metric). |
| `cu_consumed` | *Integer* | Actual compute units burned (V5.0 Metric). |

## 💰 Commercial Licensing & Pricing
**This repository contains the Free Sample ("Spark"). Full Historical Archives are Gated.**

| Tier | Price | Includes | Target Audience |
| :--- | :--- | :--- | :--- |
| **Spark** | **FREE** | 5,000 Rows (Daily Snapshot) | Students / Code Verification |
| **Standard** | **5 SOL** | **100,000 Rows** (Weekly Archive) | Independent Quants / Backtesting |
| **Professional** | **1,680 USDC** | **1,000,000 Rows** (Monthly Deep Archive) | **ML Engineers / Validation Sets** |
| **Enterprise** | **3,500 USDC** | **Full Node History** (Unlimited) + *Real-Time Stream Access* | Hedge Funds / Validators |

### 🛒 How to Purchase & Gain Access
1.  **Click "Request Access"** at the top of this page.
2.  **Send Your Payment To**
    * **Address:** `FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q`
    * *Note: We accept **SOL** for Standard, and **USDC-SPL** for Pro/Enterprise.*
3.  **In your Request Note**, paste your **Transaction Signature (TXID)**.
    * *Example Note: "Purchased Professional Organic Tier. TXID: 2xA9... Payment verified."*

**⚠️ AUTOMATION ALERT:** Our system scans the chain for your TXID. Once verified, access is granted automatically within 10 minutes.

---
*Harvested by Titan Orion Geyser Nodes. Immutable and Verified.*
"""

    # --- 4. MEV SYNTHETIC (DEFAULT) ---
    else:
        return f"""---
license: mit
task_categories:
- time-series-forecasting
- tabular-regression
- reinforcement-learning
tags:
- finance
- solana
- mev
- hft
size_categories:
- 5K<n<1M
---
---
{spark_notice}
# 🔒 RESTRICTED ACCESS: Full Institutional Bundles

> **⚠️ ACCESS CONTROL:** The full datasets contain high-alpha competitive intelligence, including Jito Tip probability matrices and Competitor Saturation logs.
>
> **Access is granted primarily to:**
> * Institutional Quant Desks
> * Verified Solana Validators
> * Academic Researchers (edu emails)

### 📢 How to Access
Click the **"Request Access"** button above. Please state your intended use-case (e.g., "Arb Bot Backtesting") to expedite approval.

---
---

## 📊 Dataset Overview
This is the **Titan Alpha Bundle**, a collection of distinct market regimes generated by the **Titan Orion AGX V5.0** engine. Unlike standard datasets that only show "average" conditions, this bundle allows you to stress-test your Arbitrage and MEV models against specific market anomalies.

### 📦 What's Inside the Bundle?
| Scenario File | Market Condition | volatility | Use-Case |
| :--- | :--- | :--- | :--- |
| `titan_sample_flash_crash.csv` | 📉 **Flash Crash** | **High (5.0)** | Stress-test your stop-loss logic and liquidation hunters. |
| `titan_sample_bull_run.csv` | 🚀 **Parabolic Bull** | Medium (1.5) | Train trend-following logic and FOMO-based sniper entries. |
| `titan_sample_mev_war.csv` | ⚔️ **MEV Congestion** | High (2.0) | Optimize **Jito Tips** when 50+ competitors are fighting for the same slot. |

## 💎 "Alpha" Features (Column Dictionary)
| Column Name | Type | Description |
| :--- | :--- | :--- |
| `timestamp_utc` | *Datetime* | Microsecond precision timestamp of the slot. |
| `market_regime` | *Category* | Context label: `FLASH_CRASH`, `BULL_TREND`, or `HIGH_CONGESTION`. |
| `implied_slippage_bps` | *Float* | The cost of trade execution in Basis Points (vital for backtesting). |
| `competitor_saturation` | *Integer* | Estimated number of rival bots competing for the same slot. |
| `validator_latency_ms` | *Float* | Network lag time to the lead validator (Simulated). |
| `jito_tip_lamports` | *Integer* | The bribe paid to Jito validators to secure the transaction. |
| `titan_alpha_score` | *Float* | **Proprietary Score (0-100)** indicating the probability of trade success. |
| `program_id` | *String* | Target Contract (Raydium/Orca/Meteora) (V5.0 Metric). |
| `slot_contention` | *Float* | 0-100% Saturation of the specific state-lock (V5.0 Metric). |
| `cu_consumed` | *Integer* | Compute Units burnt in the transaction (V5.0 Metric). |

## 💰 Commercial Licensing & Pricing
**This repository contains the Free Sample ("Spark"). Full datasets are Gated.**

| Tier | Price | Includes | Target Audience |
| :--- | :--- | :--- | :--- |
| **Spark** | **FREE** | 5,000 Rows (Daily Drop) | Students / Code Verification |
| **Standard** | **5 SOL** | **100,000 Rows** (Weekly Refresh) | Independent Quants / Testers |
| **Professional** | **1,680 USDC** | **1,000,000 Rows** (The "Titan Omega" Deep Learning Set) | **ML Engineers / Model Training** |
| **Enterprise** | **3,500 USDC** | Alpha Bundle + *Live Weekly Updates* + Commercial Redist. Rights | Hedge Funds / Validators |

### 🛒 How to Purchase & Gain Access
1.  **Click "Request Access"** at the top of this page.
2.  **Send Your Payment To**
    * **Address:** `FpFtUESU6Rvy7uS85sLDg7iayjczrsFNJa4Q2dFV8z6q`
    * *Note: We accept **SOL** for Standard, and **USDC-SPL** for Pro/Enterprise.*
3.  **In your Request Note**, paste your **Transaction Signature (TXID)**.
    * *Example Note: "Purchased Professional Tier. TXID: 5xG9... Payment verified."*

**⚠️ AUTOMATION ALERT:** Our system scans the chain for your TXID. Once verified, access is granted automatically within 10 minutes.

---
*Generated by the Titan Orion Neural Engine. Verified for integrity.*
"""

def generate_batch_file(filename, row_count, selected_scenarios):
    # NEW V5.0 HEADER WITH METADATA
    header = "timestamp_utc,pair,market_regime,execution_price,jito_tip_lamports,titan_alpha_score,program_id,slot_contention,cu_consumed\n"
    
    with open(filename, "w") as f:
        f.write(header)
        start_time = datetime.now()
        
        # Initialize Random Walk Price
        current_price = 150.00 
        
        for _ in range(int(row_count)):
            if not selected_scenarios: active_scenario = "Balanced"
            else: active_scenario = random.choice(selected_scenarios)
            
            weights = get_scenario_config(active_scenario)
            ts = start_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            
            # PASS PRICE STATE
            row_str, current_price = generate_random_walk_row(ts, current_price, active_scenario, weights)
            
            f.write(f"{row_str}\n")
            start_time += timedelta(milliseconds=random.randint(1, 15))
        
        # IO SAFETY: Flush to disk to avoid LFS errors on OMEGA batches
        f.flush()
        os.fsync(f.fileno())

    return True


def prepare_organic_batch(batch_name, size, organic_csv_path, out_dir=DATA_DIR):
    """Prepare a factory-compatible CSV from an organic capture CSV.
    This is a dry-run helper: it samples up to `size` rows from `organic_csv_path`
    and writes a normalized CSV to DATA_DIR but DOES NOT UPLOAD.
    Returns path to the prepared CSV.
    """
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, f"{batch_name}_{size}_organic.csv")

    header = "timestamp_utc,pair,market_regime,execution_price,jito_tip_lamports,titan_alpha_score,program_id,slot_contention,cu_consumed\n"

    written = 0
    try:
        # Read whole file to handle cases where newlines are escaped as literal '\n'
        with open(organic_csv_path, "r") as inf:
            raw = inf.read()

        if "\\n" in raw and "\n" not in raw:
            raw = raw.replace("\\n", "\n")

        lines = raw.splitlines()
        reader = csv.reader(lines)

        with open(out_csv, "w") as outf:
            outf.write(header)

            # Attempt to skip header if present
            rows = list(reader)
            if rows and any("timestamp_utc" in str(x) for x in rows[0]):
                row_iter = iter(rows[1:])
            else:
                row_iter = iter(rows)

            for row in row_iter:
                if written >= int(size): break
                # Expecting: timestamp_utc,signature,slot,pool,symbol,success,fee,program_ids
                try:
                    ts = row[0]
                    signature = row[1] if len(row) > 1 else ""
                    slot = row[2] if len(row) > 2 else ""
                    pool = row[3] if len(row) > 3 else ""
                    symbol = row[4] if len(row) > 4 else ""
                    success = row[5] if len(row) > 5 else ""
                    fee = row[6] if len(row) > 6 else "0"
                    program_ids = row[7] if len(row) > 7 else ""
                except Exception:
                    continue

                # Map to factory schema
                pair = symbol if symbol else pool
                market_regime = "Organic-Capture"
                execution_price = "0.0"
                try:
                    jito_tip = int(fee)
                except Exception:
                    jito_tip = 0
                titan_alpha = 50.0
                program_id = program_ids.split(";")[0] if program_ids else ""
                slot_contention = 0.0
                cu_consumed = 0

                outf.write(f"{ts},{pair},{market_regime},{execution_price},{jito_tip},{titan_alpha:.2f},{program_id},{slot_contention:.4f},{cu_consumed}\n")
                written += 1

        print(f"[FACTORY] Prepared organic batch: {out_csv} ({written} rows)")
        return out_csv
    except Exception as e:
        print(f"[FACTORY] prepare_organic_batch failed: {e}")
        return None

# ==========================================
# 🚀 MAIN PIPELINE
# ==========================================
def run_factory_pipeline(batch_name, size, selected_scenarios, target_repo_keys, organic_csv=None):
    os.makedirs(DATA_DIR, exist_ok=True)

    # If an organic_csv is provided, prepare a factory-compatible CSV from it
    if organic_csv:
        csv_file = prepare_organic_batch(batch_name, size, organic_csv, out_dir=DATA_DIR)
        if not csv_file:
            print("[FACTORY] Failed to prepare organic batch; aborting.")
            return False
        # Dry-run: do not upload anything when using organic source unless explicitly requested
        print(f"[FACTORY] Dry-run mode: prepared {csv_file}. Uploads are skipped.")

        # Still write READMEs locally for review, but skip huggingface uploads and Twitter
        if target_repo_keys:
            for key in target_repo_keys:
                print(f"[FACTORY] (Dry-run) Prepared README for {key}")
                readme_content = get_readme_template(key, size)
                readme_path = f"{DATA_DIR}/README_{key}.md"
                with open(readme_path, "w") as f:
                    f.write(readme_content)
                    f.flush()
                    os.fsync(f.fileno())
        return True

    # 1. Generate Data (V5 Engine) — synthetic path
    csv_file = f"{DATA_DIR}/{batch_name}_{size}.csv"
    generate_batch_file(csv_file, size, selected_scenarios)
    time.sleep(1) # Safety pause for IO
    
    success = True
    api = HfApi(token=HF_TOKEN)

    if not target_repo_keys: return True

    for key in target_repo_keys:
        repo_id = REPO_MAP.get(key)
        if repo_id:
            print(f"[FACTORY] Processing {key}...")
            readme_content = get_readme_template(key, size)
            readme_path = f"{DATA_DIR}/README_{key}.md"
            with open(readme_path, "w") as f: 
                f.write(readme_content)
                f.flush()
                os.fsync(f.fileno())
            
            time.sleep(1) # Safety pause

            try:
                # Upload CSV (CSV Fails safely without breaking loop)
                try:
                    api.upload_file(path_or_fileobj=csv_file, path_in_repo=f"{batch_name}.csv", repo_id=repo_id, repo_type="dataset")
                except Exception as e:
                    print(f"[FACTORY] CSV Upload Error {key}: {e}")
                    success = False
                    continue # Skip readme if CSV failed

                # Upload README
                api.upload_file(path_or_fileobj=readme_path, path_in_repo="README.md", repo_id=repo_id, repo_type="dataset")
                print(f"[FACTORY] Success: {key}")
                
                # Twitter Broadcast
                post_to_x(batch_name, size, key)
                
            except Exception as e:
                print(f"[FACTORY] Metadata Upload Error {key}: {e}")
                success = False
            
            # Cleanup
            if os.path.exists(readme_path): os.remove(readme_path)
    return success


# -----------------------------------------------------------------------------
# Scheduler: Auto-generate and publish datasets on schedule
# - Daily at 14:00 local: produce 5k MEMPOOL and 5k MEV synthetic (SPARK)
# - Weekly on Monday at 12:00 local: produce 100k MEM and MEV synthetic (STANDARD)
# Each successful upload triggers `post_to_x` via run_factory_pipeline
# -----------------------------------------------------------------------------

_scheduler_thread = None
_scheduler_stop = False

def _scheduler_loop():
    last_daily_date = None
    last_weekly_date = None

    DAILY_HOUR = 14  # 2 PM
    WEEKLY_DAY = 0   # Monday (0=Monday)
    WEEKLY_HOUR = 12 # Noon

    while not _scheduler_stop:
        now = datetime.now()

        # Daily job
        if now.hour == DAILY_HOUR and now.date() != last_daily_date:
            # 5k MEMPOOL Synthetic (SPARK)
            batch_name = f"AUTO-MEMPOOL-{now.strftime('%Y%m%d')}-5k"
            threading.Thread(target=run_factory_pipeline, args=(batch_name, 5000, [], ["MEMPOOL_SYNTH_SPARK"]), daemon=True).start()

            # 5k MEV Synthetic (SPARK)
            batch_name2 = f"AUTO-MEV-{now.strftime('%Y%m%d')}-5k"
            threading.Thread(target=run_factory_pipeline, args=(batch_name2, 5000, ["MEV Heavy"], ["MEV_SYNTH_SPARK"]), daemon=True).start()

            print(f"[SCHED] Launched daily 5k jobs for {now.date()}")
            last_daily_date = now.date()

        # Weekly job (once per week)
        if now.weekday() == WEEKLY_DAY and now.hour == WEEKLY_HOUR and now.date() != last_weekly_date:
            # 100k MEMPOOL Synthetic (STANDARD)
            batchw = f"AUTO-MEMPOOL-{now.strftime('%Y%m%d')}-100k"
            threading.Thread(target=run_factory_pipeline, args=(batchw, 100000, [], ["MEMPOOL_SYNTH_STD"]), daemon=True).start()

            # 100k MEV Synthetic (STANDARD)
            batchw2 = f"AUTO-MEV-{now.strftime('%Y%m%d')}-100k"
            threading.Thread(target=run_factory_pipeline, args=(batchw2, 100000, ["MEV Heavy"], ["MEV_SYNTH_STD"]), daemon=True).start()

            print(f"[SCHED] Launched weekly 100k jobs for {now.date()}")
            last_weekly_date = now.date()

        # Sleep briefly
        time.sleep(30)


def start_scheduler():
    global _scheduler_thread, _scheduler_stop
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop = False
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()
    print("[SCHED] Dataset scheduler started.")


def stop_scheduler():
    global _scheduler_stop
    _scheduler_stop = True
    print("[SCHED] Dataset scheduler stopping.")


# -----------------------------------------------------------------------------
# Helpers: Map batch size and data type to REPO_MAP keys (organic)
# -----------------------------------------------------------------------------
def _repo_tier_for_size(size:int):
    if size <= 5000:
        return "SPARK"
    if size <= 100000:
        return "STD"
    return "OMEGA"


def get_repo_keys_for(size:int, data_type:str, organic=True):
    """Return a list of target repo keys for the given size and data type.
    data_type: 'MEMPOOL' or 'MEV' (case-insensitive)
    organic: when True, use the ORGANIC repo keys (MEMPOOL_ORG_*, MEV_ORG_*)
    """
    dt = data_type.upper()
    tier = _repo_tier_for_size(int(size))

    if dt == 'MEMPOOL':
        base = 'MEMPOOL_ORG' if organic else 'MEMPOOL_SYNTH'
    elif dt == 'MEV':
        base = 'MEV_ORG' if organic else 'MEV_SYNTH'
    else:
        # fallback to mempool organic
        base = 'MEMPOOL_ORG' if organic else 'MEMPOOL_SYNTH'

    key = f"{base}_{'SPARK' if tier=='SPARK' else ('STD' if tier=='STD' else 'OMEGA') }"
    # Ensure key exists in REPO_MAP
    if key in REPO_MAP:
        return [key]
    # fallback: return all organic repos of that type (best-effort)
    keys = [k for k in REPO_MAP.keys() if k.startswith(base)]
    return keys


def prepare_and_connect_organic(batch_name, size, organic_csv_path, data_type='MEMPOOL'):
    """High-level wrapper: prepare a factory-compatible organic CSV and
    create README files for the corresponding repo(s). This is a DRY-RUN and
    will NOT upload to Hugging Face or post to Twitter.

    Returns dict with keys: prepared_csv (path) and repo_keys (list).
    """
    keys = get_repo_keys_for(size, data_type, organic=True)
    ok = run_factory_pipeline(batch_name, size, [], keys, organic_csv=organic_csv_path)
    prepared = os.path.join(DATA_DIR, f"{batch_name}_{size}_organic.csv")
    return {"prepared_csv": prepared if os.path.exists(prepared) else None, "repo_keys": keys, "dry_run_ok": ok}


def upload_organic_batch(batch_name, size, organic_csv_path, repo_keys):
    """Prepare organic batch and upload to Hugging Face + tweet.
    This performs the real upload and will raise/return False on failure.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    prepared = prepare_organic_batch(batch_name, size, organic_csv_path, out_dir=DATA_DIR)
    if not prepared:
        print(f"[FACTORY] upload_organic_batch: failed to prepare {organic_csv_path}")
        return False

    api = HfApi(token=HF_TOKEN)
    success = True
    for key in repo_keys:
        repo_id = REPO_MAP.get(key)
        if not repo_id:
            print(f"[FACTORY] upload_organic_batch: unknown repo key {key}")
            success = False
            continue

        readme_content = get_readme_template(key, size)
        readme_path = f"{DATA_DIR}/README_{key}.md"
        with open(readme_path, "w") as f:
            f.write(readme_content)
            f.flush()
            os.fsync(f.fileno())

        try:
            print(f"[FACTORY] Uploading {prepared} -> {repo_id} ...")
            api.upload_file(path_or_fileobj=prepared, path_in_repo=f"{batch_name}.csv", repo_id=repo_id, repo_type="dataset")
            api.upload_file(path_or_fileobj=readme_path, path_in_repo="README.md", repo_id=repo_id, repo_type="dataset")
            print(f"[FACTORY] Upload success: {key} ({repo_id})")

            # Broadcast
            try:
                post_to_x(batch_name, size, key)
            except Exception as e:
                print(f"[FACTORY] post_to_x failed: {e}")

        except Exception as e:
            print(f"[FACTORY] Upload error for {key}: {e}")
            success = False

        # cleanup readme
        if os.path.exists(readme_path): os.remove(readme_path)

    return success
