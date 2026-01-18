#!/usr/bin/env python3
import os
import random
import tweepy

AMMO_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets.txt"),
    "/app/tweets.txt",
]


def load_ammo_line():
    path = None
    for p in AMMO_CANDIDATES:
        if os.path.exists(p):
            path = p
            break
    if not path:
        print("[CLI] ERROR: tweets.txt not found in expected locations.")
        return None

    with open(path, "r") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]

    if not lines:
        print(f"[CLI] ERROR: tweets.txt at {path} is empty.")
        return None

    choice = random.choice(lines)
    print(f"[CLI] Using ammo from {path}")
    return choice


def make_client():
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("[CLI] ERROR: Missing X_API_* credentials in environment.")
        return None

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )
        return client
    except Exception as e:
        print(f"[CLI] ERROR: Failed to create Tweepy client: {e}")
        return None


def main():
    msg = load_ammo_line()
    if not msg:
        return

    client = make_client()
    if not client:
        return

    # Show which account we are about to use
    try:
        me = client.get_me()
        if getattr(me, "data", None):
            print(f"[CLI] ENGAGED PROFILE: @{me.data.username} (id={me.data.id})")
        else:
            print("[CLI] WARNING: get_me() returned no data; profile unknown.")
    except Exception as e:
        print(f"[CLI] WARNING: Failed to query current profile: {e}")

    print("[CLI] FIRING TWEET:")
    print(msg)

    try:
        resp = client.create_tweet(text=msg)
        print("[CLI] RAW RESPONSE:", resp)
        # Tweepy v2 Client returns a Response object with data/errors
        errors = getattr(resp, "errors", None)
        if errors:
            print("[CLI] X API ERRORS:", errors)
        else:
            print("[CLI] SUCCESS: Tweet appears accepted by X API.")
    except Exception as e:
        print(f"[CLI] ERROR: Tweet failed: {e}")


if __name__ == "__main__":
    main()
