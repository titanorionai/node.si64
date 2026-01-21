"""
Minimal dotenv shim for containerized environments where
`python-dotenv` is not installed. This provides a no-op
`load_dotenv` so `titan_config` can safely import in the image.
"""
import os

def load_dotenv(path=None, override=False):
    # no-op: environment variables are expected to be injected
    return False
