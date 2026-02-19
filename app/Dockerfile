FROM python:3.11-slim

WORKDIR /app

# Copy shared requirements into container
COPY requirements.txt /app/requirements.txt

# Copy app code
COPY app /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["flask", "--app", "api", "run", "--host=0.0.0.0", "--port=8080"]
