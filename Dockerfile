# Use an updated Python image
FROM python:3.12-bookworm

# Set environment variables to prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies in one layer for faster builds
RUN apt-get update && \
    apt-get install -y libsnappy-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Set the working directory in the container
WORKDIR /app

# Copy only requirements.txt first to leverage caching
COPY requirements.txt ./

# Install Python dependencies using uv
RUN uv --install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Add .dockerignore to reduce build context
# (Ensure .dockerignore is properly configured to exclude unnecessary files)

# Command to run the application
CMD ["python3", "main.py"]