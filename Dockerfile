# Base Python image
FROM python:3.11-slim-bookworm AS base

# Builder stage
FROM base AS builder
# Install build tools and libraries
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    libsnappy-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:0.5.9 /uv /bin/uv

# Enable bytecode compilation and use link mode as "copy"
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Create virtual environment
RUN uv venv

# Copy dependency files
COPY requirements.txt /app/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --verbose -r requirements.txt

# Copy the rest of the application
COPY . /app

# Final runtime stage
FROM base
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python3", "main.py"]