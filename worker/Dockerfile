FROM python:3.11-slim

WORKDIR /worker

# Install git and venv dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from the project root into the container
COPY requirements.txt /worker/requirements.txt

# Copy the actual worker code from the worker directory
COPY worker /worker

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for synced code and venvs
RUN mkdir -p /worker/integrations /worker/venvs

# Start the worker
CMD ["python", "main.py"]