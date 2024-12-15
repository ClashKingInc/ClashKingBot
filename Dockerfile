# Base Python image
FROM python:3.12-slim-bookworm AS base

# Builder stage
FROM base AS builder
# Install git, gcc, g++, and other necessary tools
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    libsnappy-dev \
    build-essential \
    python3-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy uv binary directly from its prebuilt Docker image
COPY --from=ghcr.io/astral-sh/uv:0.5.9 /uv /bin/uv

# Enable bytecode compilation and use link mode as "copy"
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Create a virtual environment with uv
RUN uv venv

# Copy dependency files into the container
COPY requirements.txt /app/

# Install dependencies using uv in a cached way
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Final runtime stage
FROM base
# Copy the built application from the builder stage
COPY --from=builder /app /app
# Add virtual environment's bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Command to run the application
CMD ["python3", "main.py"]