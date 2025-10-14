FROM python:3.13.7-slim

LABEL org.opencontainers.image.source=https://github.com/ClashKingInc/ClashKingBot
LABEL org.opencontainers.image.description="Image for the ClashKing Discord Bot"
LABEL org.opencontainers.image.licenses=MIT

# Install uv and system dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsnappy-dev \
    git \
    curl \
    build-essential \
    gcc \
    python3-dev \
    libmagickwand-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy pyproject.toml first for better caching
COPY pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system . \
    && apt-get remove -y build-essential gcc python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip

# Copy the rest of the application code into the container
COPY . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://127.0.0.1:8027/health || exit 1
LABEL org.opencontainers.image.source=https://github.com/ClashKingInc/ClashKingBot
LABEL org.opencontainers.image.description="Image for the ClashKing Discord Bot"
LABEL org.opencontainers.image.licenses=MIT

# Command to run the application
CMD ["uv", "run", "python", "main.py"]