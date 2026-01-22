#!/usr/bin/env python3
"""
Compare localhost API responses with public si64.net to ensure the tunnel serves the same build.
Exit 0 if all endpoints match, non-zero if any mismatch or fetch error.
"""
import json
import sys
import urllib.request
import urllib.error
from typing import Any, Tuple

LOCAL_BASE = "http://127.0.0.1:8000"
PUBLIC_BASE = "https://si64.net"
TIMEOUT = 10

ENDPOINTS = [
    "/api/stats",
    "/api/wallet",
    "/api/devices/M2",
    "/api/devices/ORIN",
    "/api/devices/M3_ULTRA",
    "/api/devices/THOR",
]


def fetch(url: str) -> Tuple[int, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "tunnel-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # nosec - trusted hostnames
        body = resp.read().decode("utf-8")
        status = resp.getcode()
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = body
        return status, data


def canonical(data: Any) -> str:
    if isinstance(data, (dict, list)):
        return json.dumps(data, sort_keys=True, separators=(",", ":"))
    return str(data)


def compare_endpoint(path: str) -> bool:
    local_url = f"{LOCAL_BASE}{path}"
    public_url = f"{PUBLIC_BASE}{path}"
    try:
        l_status, l_data = fetch(local_url)
        p_status, p_data = fetch(public_url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[FAIL] {path}: fetch error {exc}")
        return False

    if l_status != p_status:
        print(f"[FAIL] {path}: status mismatch local={l_status} public={p_status}")
        return False

    if canonical(l_data) != canonical(p_data):
        print(f"[FAIL] {path}: payload mismatch")
        print(f"  local : {l_data}")
        print(f"  public: {p_data}")
        return False

    print(f"[OK] {path}")
    return True


def main() -> int:
    all_good = True
    for ep in ENDPOINTS:
        if not compare_endpoint(ep):
            all_good = False
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
