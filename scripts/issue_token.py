#!/usr/bin/env python3
"""Call /api/admin/issue_token to create a short-lived bearer token for a node.
Usage: python3 scripts/issue_token.py <node_id> [ttl_seconds] [dispatcher_url]
"""
import sys, requests, os

def main():
    if len(sys.argv) < 2:
        print("Usage: issue_token.py <node_id> [ttl_seconds] [dispatcher_url]")
        sys.exit(1)
    node_id = sys.argv[1]
    ttl = int(sys.argv[2]) if len(sys.argv) > 2 else None
    url = sys.argv[3] if len(sys.argv) > 3 else os.getenv('DISPATCHER_URL','http://127.0.0.1:8000')
    key = os.getenv('GENESIS_KEY') or os.getenv('X_GENESIS_KEY')
    if not key:
        print('Set GENESIS_KEY env or X_GENESIS_KEY to authenticate to admin API')
        sys.exit(2)
    headers = {'x-genesis-key': key}
    params = {'node_id': node_id}
    if ttl:
        params['ttl'] = ttl
    resp = requests.post(f"{url}/api/admin/issue_token", params=params, headers=headers, timeout=10)
    try:
        print(resp.status_code, resp.text)
    except Exception:
        print(resp.status_code)

if __name__ == '__main__':
    main()
