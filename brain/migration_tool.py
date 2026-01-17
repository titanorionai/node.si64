import sqlite3
import os
import sys

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "titan_ledger.db")

def migrate_legacy_data():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        return

    print(f"/// TITAN LEDGER MIGRATION ///")
    print(f"TARGET: {DB_PATH}")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 1. Check if 'tx' (Legacy) exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tx'")
            if not cursor.fetchone():
                print("[INFO] No legacy 'tx' table found. System is clean.")
                return

            # 2. Check if 'transactions' (Modern) exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
            if not cursor.fetchone():
                print("[INFO] Creating modern 'transactions' table schema...")
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        job_id TEXT PRIMARY KEY, 
                        worker_wallet TEXT, 
                        amount_sol REAL, 
                        tx_signature TEXT, 
                        timestamp DATETIME, 
                        status TEXT
                    )
                ''')

            # 3. Perform Migration
            print("[ACTION] Migrating data from 'tx' to 'transactions'...")
            
            # Fetch old data: job_id, wallet, amount, tx_hash, timestamp
            cursor.execute("SELECT * FROM tx")
            legacy_rows = cursor.fetchall()
            
            migrated_count = 0
            skipped_count = 0
            
            for row in legacy_rows:
                # Map old schema to new schema
                # Old: (job_id, wallet, amount, tx_hash, timestamp)
                # New: (job_id, worker_wallet, amount_sol, tx_signature, timestamp, status)
                try:
                    conn.execute(
                        "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?)",
                        (row[0], row[1], row[2], row[3], row[4], "MIGRATED")
                    )
                    migrated_count += 1
                except sqlite3.IntegrityError:
                    # ID already exists in new table
                    skipped_count += 1
            
            conn.commit()
            
            print(f"--------------------------------")
            print(f"[SUCCESS] Migration Complete.")
            print(f"Records Moved:   {migrated_count}")
            print(f"Duplicates Skipped: {skipped_count}")
            print(f"--------------------------------")
            
            # Optional: Drop old table
            # cursor.execute("DROP TABLE tx")
            # print("[CLEANUP] Legacy 'tx' table dropped.")

    except Exception as e:
        print(f"[CRITICAL FAILURE] Migration aborted: {e}")

if __name__ == "__main__":
    migrate_legacy_data()
