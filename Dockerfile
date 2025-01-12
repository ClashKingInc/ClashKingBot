# Use an updated Python slim image
FROM python:3.12.8-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

LABEL org.opencontainers.image.source=https://github.com/ClashKingInc/ClashKingBot
LABEL org.opencontainers.image.description="Image for the ClashKing Discord Bot"
LABEL org.opencontainers.image.licenses=MIT

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsnappy-dev \
    git \
    curl \
    build-essential \
    gcc \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements.txt file first
COPY requirements.txt .

# Install dependencies using uv with the --system flag
RUN uv pip install -r requirements.txt --system

# Copy the rest of the application code into the container
COPY . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://127.0.0.1:8027/health || exit 1

# Command to run the application
CMD ["python3", "main.py"]