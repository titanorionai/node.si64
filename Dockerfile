# BASE LAYER: Official Python Slim (Debian Bookworm) - Minimal Attack Surface
FROM python:3.10-slim-bookworm

# METADATA
LABEL maintainer="TITAN NETWORK <ops@si64.net>"
LABEL classification="RESTRICTED"

# ENVIRONMENT HARDENING
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# TACTICAL DIRECTORY
WORKDIR /app

# DEPENDENCY INJECTION
# UPDATED: Explicitly installing ca-certificates for secure WSS handshake
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# NEURAL DEPENDENCIES
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# INJECT CORE LOGIC
# We copy the 'core' folder (The Limb)
COPY core/ ./core/

# Copy top-level config and dotenv shim so container is standalone
COPY titan_config.py ./
COPY dotenv.py ./

# CREATE NON-ROOT USER (Security Best Practice)
RUN useradd -m titan && chown -R titan:titan /app
USER titan

# COMMAND PROTOCOL
# Default to connecting to the Mothership
ENTRYPOINT ["python3", "core/limb/worker_node.py"]
CMD ["--connect", "wss://si64.net/connect"]
