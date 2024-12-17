# Stage 1: Base Image with Python and System Dependencies
FROM python:3.11-bookworm AS base

LABEL org.opencontainers.image.source=https://github.com/ClashKingInc/ClashKingBot
LABEL org.opencontainers.image.description="Image for the ClashKing Discord Bot"
LABEL org.opencontainers.image.licenses=MIT

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libsnappy-dev && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Stage 2: Install Python Dependencies
FROM base AS dependencies

# Copy only requirements to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Copy Application Code
FROM dependencies AS final

# Copy the rest of the application code
COPY . .

# Set the default command
CMD ["python3", "main.py"]