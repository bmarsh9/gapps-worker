FROM python:3.11-slim

WORKDIR /scheduler

# Copy requirements.txt from the project root into the container
COPY requirements.txt /scheduler/requirements.txt

# Copy the actual scheduler code from the worker directory
COPY scheduler /scheduler

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start the worker
CMD ["python", "main.py"]
