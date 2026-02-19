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
      "account_id": "123456789012",
      "region": "us-east-1"
    },
    "schedule": "*/1 * * * *",
    "timeout": 120
  }'
