#!/usr/bin/env bash
# Fire a single tweet by pulling a random line from tweets.txt
# and sending it via the X API using your X_API_* creds.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# Load X_API_* credentials from local .env so you don't
# have to export them manually in your shell.
if [[ -f .env ]]; then
	set -o allexport
	# shellcheck disable=SC1091
	. .env
	set +o allexport
fi

./venv/bin/python3 fire_tweet.py
