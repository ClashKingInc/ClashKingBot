# Use an updated Python image
FROM python:3.11-bookworm

LABEL org.opencontainers.image.source=https://github.com/ClashKingInc/ClashKingBot
LABEL org.opencontainers.image.description="Image for the ClashKing Discord Bot"
LABEL org.opencontainers.image.licenses=MIT

# Install dependencies
RUN apt-get update && apt-get install -y libsnappy-dev

# Set the working directory in the container
WORKDIR /app

# First, copy only the requirements.txt file
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code into the container
COPY . .

# Command to run the application
CMD ["python3", "main.py"]