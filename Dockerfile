FROM python:3.10-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY core/ ./core/
RUN useradd -m titan
USER titan
ENV PYTHONUNBUFFERED=1
ENV SI64_NODE_ROLE="worker"
CMD ["python3", "core/limb/worker_node.py"]
