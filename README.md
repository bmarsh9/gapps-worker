## Get Started

#### 1. Start the platform
```commandline
# Run everything except for tests
docker compose --profile default up --build -d

# Run tests in container
docker compose --profile default --profile test up --build -d

# Shut down containers
docker compose --profile default down

# Create integration and deployment
curl -X POST http://localhost:8080/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hello_world",
    "title": "Hello World",
    "description": "Hello world integration",
    "schema": {
      "type": "object",
      "properties": {
        "account_id": { "type": "string" },
        "region": { "type": "string" }
      },
      "required": ["account_id", "region"]
    }
  }'

curl -X POST http://localhost:8080/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": 1,
    "config": {
      "token": "123456789012"
    },
    "schedule": "*/1 * * * *",
    "timeout": 120
  }'
```

#### 2. View logs
```commandline
docker-compose --profile default logs -f
```

## README for workers
See `worker/README.md` for more information about the workers and creating integrations.
