import sys, time, json, logging, signal, zmq, requests, os, threading
from datetime import datetime, timedelta

# --- CONFIG ---
ZMQ_PORT = 5555
SCAN_INTERVAL = 10 # Scan for new targets every 10 seconds (very aggressive)

# --- FILTERS ---
MIN_LIQ = 0         # no liquidity floor to maximize discovery
MIN_AGE_HOURS = 0   # include very new pools
MAX_AGE_HOURS = 168 # up to 7 days
MIN_TREND = -100.0  # accept any movement (capture everything)
MAX_TREND = 100.0   # wide upper bound

# RPC configuration (can be overridden by env vars)
# Chainstack / Geyser defaults (can be overridden by env vars)
GEYSER_URL = os.environ.get('GEYSER_URL', 'https://yellowstone-solana-mainnet.core.chainstack.com:443')
GEYSER_TOKEN = os.environ.get('GEYSER_TOKEN', 'b8dc50df2c1abbbae3faab2bcf308faa')
RPC_HTTP_URL = os.environ.get('RPC_HTTP_URL', 'https://solana-mainnet.core.chainstack.com/b8dc50df2c1abbbae3faab2bcf308faa')

# Primary RPC to use for JSON-RPC calls
RPC_URL = os.environ.get('RPC_URL', RPC_HTTP_URL)
# Token to place in headers if provided (env overrides default)
RPC_TOKEN = os.environ.get('RPC_TOKEN', GEYSER_TOKEN)
RPC_AUTH_HEADER = None

def detect_rpc_auth_header(rpc_url, token):
    """Try common header names and return the one that yields a JSON RPC response."""
    if not token:
        return None
    candidates = [
        ('x-token', token),
        ('x-chainstack-token', token),
        ('Authorization', f'Bearer {token}'),
        ('x-api-key', token),
        ('x-access-token', token),
        ('api-key', token),
    ]
    test_payload = {"jsonrpc":"2.0","id":1,"method":"getEpochInfo","params":[]}
    for name, val in candidates:
        try:
            headers = {'Content-Type': 'application/json', name: val}
            r = requests.post(rpc_url, headers=headers, data=json.dumps(test_payload), timeout=6)
            try:
                j = r.json()
                if isinstance(j, dict) and ('result' in j or 'error' in j):
                    logger.info(f"[SCOUT] Detected auth header: {name}")
                    return name
            except Exception:
                continue
        except Exception:
            continue
    return None

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S', stream=sys.stdout)
logger = logging.getLogger("TitanBrain")

class TitanBrain:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.bind(f"tcp://*:{ZMQ_PORT}")
        
        self.current_target = {"mint": "", "pool": "", "symbol": ""}
        self.last_scan = 0
        self.running = True
        
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, signum, frame):
        self.running = False
        sys.exit(0)

    def capture_onchain_for_pool(self, pool_address, meta, limit=5):
        """Fetch recent on-chain transactions for a pool and append to data_warehouse/organic_capture.csv

        Uses retries and exponential backoff to handle transient RPC failures.
        """
        try:
            DATA_DIR = os.path.abspath("./data_warehouse")
            os.makedirs(DATA_DIR, exist_ok=True)
            out_path = os.path.join(DATA_DIR, "organic_capture.csv")

            rpc_url = RPC_URL
            headers = {"Content-Type": "application/json"}
            if RPC_TOKEN:
                headers['x-token'] = RPC_TOKEN
            logger.info(f"[SCOUT] Using RPC: {rpc_url} (token={'yes' if RPC_TOKEN else 'no'})")

            def post_rpc(payload, retries=5, base_delay=1.0):
                """Post JSON-RPC with exponential backoff + jitter and 429 handling."""
                delay = base_delay
                for attempt in range(1, retries + 1):
                    try:
                        # prepare headers and detect auth header once
                        nonlocal_headers = dict(headers)
                        global RPC_AUTH_HEADER
                        if RPC_TOKEN and RPC_AUTH_HEADER is None:
                            RPC_AUTH_HEADER = detect_rpc_auth_header(rpc_url, RPC_TOKEN)
                        if RPC_TOKEN and RPC_AUTH_HEADER:
                            if RPC_AUTH_HEADER == 'Authorization':
                                nonlocal_headers[RPC_AUTH_HEADER] = f"Bearer {RPC_TOKEN}"
                            else:
                                nonlocal_headers[RPC_AUTH_HEADER] = RPC_TOKEN

                        r = requests.post(rpc_url, headers=nonlocal_headers, data=json.dumps(payload), timeout=10)
                        r_text = r.text
                        if r.status_code == 200:
                            try:
                                return r.json()
                            except Exception as je:
                                logger.warning(f"[SCOUT] RPC JSON parse error (attempt {attempt}): {je} body={r_text[:800]}")
                                return None
                        elif r.status_code == 429:
                            # rate limited: backoff with jitter
                            jitter = min(60, delay * 2)
                            sleep_for = delay + (random.random() * jitter)
                            logger.warning(f"[SCOUT] RPC 429 rate limited (attempt {attempt}). Sleeping {sleep_for:.1f}s")
                            time.sleep(sleep_for)
                            delay = min(60, delay * 2)
                            continue
                        else:
                            body = r_text[:800]
                            logger.warning(f"[SCOUT] RPC status {r.status_code} (attempt {attempt}) body={body}")
                    except Exception as e:
                        logger.warning(f"[SCOUT] RPC exception (attempt {attempt}): {e}")

                    # generic backoff before next attempt
                    sleep_for = delay + (random.random() * delay)
                    time.sleep(sleep_for)
                    delay = min(60, delay * 2)
                return None

            payload = {"jsonrpc": "2.0", "id":1, "method":"getSignaturesForAddress", "params":[pool_address, {"limit": limit}]}
            resp_json = post_rpc(payload, retries=4)
            if not resp_json:
                logger.debug(f"[SCOUT] No RPC response for signatures for {pool_address}")
                return
            sigs = resp_json.get('result', [])

            rows = []
            for s in sigs:
                sig = s.get('signature')
                if not sig:
                    continue
                p2 = {"jsonrpc":"2.0","id":1,"method":"getTransaction","params":[sig, {"encoding":"jsonParsed"}]}
                tx_json = post_rpc(p2, retries=4)
                if not tx_json:
                    continue
                tx = tx_json.get('result')
                if not tx:
                    continue

                block_time = tx.get('blockTime')
                slot = tx.get('slot')
                meta_info = tx.get('meta', {}) or {}
                err = meta_info.get('err')
                success = (err is None)
                fee = meta_info.get('fee', 0)
                program_ids = set()
                for instr in tx.get('transaction', {}).get('message', {}).get('instructions', []):
                    pid = instr.get('programId') or instr.get('programIdIndex')
                    if isinstance(pid, dict):
                        pid = pid.get('pubkey')
                    if pid:
                        program_ids.add(str(pid))

                row = {
                    'timestamp_utc': datetime.utcfromtimestamp(block_time).isoformat() if block_time else datetime.utcnow().isoformat(),
                    'signature': sig,
                    'slot': slot,
                    'pool': pool_address,
                    'symbol': meta.get('symbol',''),
                    'success': success,
                    'fee': fee,
                    'program_ids': ';'.join(list(program_ids))
                }
                rows.append(row)

            if rows:
                write_header = not os.path.exists(out_path)
                with open(out_path, 'a') as f:
                    if write_header:
                        f.write('timestamp_utc,signature,slot,pool,symbol,success,fee,program_ids\\n')
                    for r in rows:
                        # escape program_ids field
                        f.write(f"{r['timestamp_utc']},{r['signature']},{r['slot']},{r['pool']},{r['symbol']},{int(r['success'])},{r['fee']},\"{r['program_ids']}\"\\n")
                logger.info(f"[SCOUT] Captured {len(rows)} on-chain txs for pool {pool_address}")

        except Exception as e:
            logger.error(f"[SCOUT] capture error: {e}")

    def seed_initial_capture(self, limit=30, per_pool=200):
        """Grab top pairs from DexScreener and capture recent txs to seed organic dataset."""
        try:
            logger.info(f"[SCOUT] Seeding initial capture for top {limit} pairs (per_pool={per_pool})")
            resp = requests.get("https://api.dexscreener.com/latest/dex/search/?q=solana", timeout=10)
            data = resp.json()
            count = 0
            for pair in data.get('pairs', []):
                if count >= limit: break
                if pair.get('chainId') != 'solana': continue
                pool = pair.get('pairAddress')
                meta = {'symbol': pair.get('baseToken', {}).get('symbol','')}
                try:
                    # run captures sequentially to avoid hitting RPC limits
                    self.capture_onchain_for_pool(pool, meta, per_pool)
                    count += 1
                    time.sleep(5.0)
                except Exception:
                    logger.exception("[SCOUT] seed capture error")
            logger.info(f"[SCOUT] Seed capture dispatched: {count} pools")
        except Exception as e:
            logger.error(f"[SCOUT] seed init error: {e}")

    def scan_dexscreener(self):
        """ The Scout: Finds tokens matching the profile """
        try:
            # Fetch latest boosted or trending tokens (Solana)
            # We use a broad search and filter manually for precision
            url = "https://api.dexscreener.com/latest/dex/tokens/solana" 
            # Note: For a true scanner we usually hit the 'latest' endpoint, 
            # but DexScreener API requires specific token addresses for that endpoint.
            # WORKAROUND: We will use a known list of 'trending' or just search common terms 
            # for this demo, OR use the 'search' endpoint.
            
            # BETTER STRATEGY FOR API LIMITS: 
            # We search for a specific pattern or just grab the trending list
            # Since we can't scrape 'trending' easily without a paid key sometimes,
            # We will assume we are pasting a list or using a very specific search.
            # However, to automate fully:
            
            logger.info("[SCOUT] 🔭 Scanning DexScreener...")
            # Using a search query for 'Solana' to get a list of active pairs
            resp = requests.get("https://api.dexscreener.com/latest/dex/search/?q=solana")
            data = resp.json()
            
            if 'pairs' not in data:
                return None

            best_candidate = None

            for pair in data['pairs']:
                if pair.get('chainId') != 'solana': continue

                # 1. LIQUIDITY CHECK
                liq = float(pair.get('liquidity', {}).get('usd', 0))
                if liq < MIN_LIQ: continue

                # 2. TREND CHECK (1H)
                change_1h = float(pair.get('priceChange', {}).get('h1', 0))
                if not (MIN_TREND <= change_1h <= MAX_TREND): continue

                # 3. AGE CHECK (Approximate via pairCreatedAt)
                created_ts = pair.get('pairCreatedAt', 0) / 1000
                age_hours = (time.time() - created_ts) / 3600
                if not (MIN_AGE_HOURS <= age_hours <= MAX_AGE_HOURS): continue

                # FOUND ONE
                best_candidate = {
                    "mint": pair['baseToken']['address'],
                    "pool": pair['pairAddress'],
                    "symbol": pair['baseToken']['symbol'],
                    "age": round(age_hours, 1),
                    "trend": change_1h
                }
                # attempt to capture recent on-chain txs for organic dataset
                try:
                    logger.info(f"[SCOUT] Capturing sample for pool {best_candidate['pool']} ({best_candidate['symbol']})")
                    self.capture_onchain_for_pool(best_candidate['pool'], best_candidate, limit=50)
                except Exception:
                    logger.exception("[SCOUT] Failed to capture on-chain sample")

                break # Take the first match (highest relevance usually)

            return best_candidate

        except Exception as e:
            logger.error(f"[SCOUT] Error: {e}")
            return None

    def run(self):
        logger.info(f"[BRAIN] 🧠 ONLINE. FILTERS: Age {MIN_AGE_HOURS}-{MAX_AGE_HOURS}h | Trend +{MIN_TREND}-{MAX_TREND}% | Liq >${MIN_LIQ}")

        # Seed initial captures from DexScreener top results to prime organic dataset
        try:
            # Seed a moderate number to avoid public RPC rate limits
            self.seed_initial_capture(limit=20, per_pool=50)
        except Exception:
            logger.exception("[SCOUT] Seed capture failed")

        while self.running:
            try:
                # 1. HANDLE REQUEST
                msg = self.socket.recv_string()
                req = json.loads(msg)
                
                response = {}

                # 2. RUN SCOUT (If interval passed)
                if time.time() - self.last_scan > SCAN_INTERVAL:
                    target = self.scan_dexscreener()
                    if target:
                        if target['mint'] != self.current_target['mint']:
                            logger.info(f"[SCOUT] 🚨 TARGET FOUND: {target['symbol']} | +{target['trend']}% | {target['age']}h Old")
                            self.current_target = target
                        else:
                            logger.info(f"[SCOUT] Keeping Target: {target['symbol']}")
                    else:
                        logger.info("[SCOUT] No new targets found. Scanning...")
                    
                    self.last_scan = time.time()

                # 3. BUILD RESPONSE FOR RUST
                response["target_mint"] = self.current_target.get("mint", "")
                response["target_pool"] = self.current_target.get("pool", "")

                # 4. DECISION LOGIC (If trade request)
                if req.get("type") == "TX":
                    impact = float(req.get("price_impact", 100))
                    if impact < 5.0:
                        response["action"] = "BUY"
                        logger.info(f"[BRAIN] 🟢 APPROVING BUY on {self.current_target['symbol']}")
                    else:
                        response["action"] = "HOLD"
                        logger.info(f"[BRAIN] 🔴 DENY: High Impact ({impact}%)")
                
                self.socket.send_json(response)

            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(0.1)

if __name__ == "__main__":
    TitanBrain().run()
