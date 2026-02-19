## Gapps Worker

### Purpose
The Gapps worker is the integration platform that allows you to create automations and flag compliance issues. It will leverage the code stored in `https://github.com/bmarsh9/gapps-integrations` for the integrations.

#### Start the platform
```commandline
# Run everything (no tests)
docker compose --profile default up --build -d

# Run tests in container
docker compose --profile default --profile test up --build -d

# Shut down containers
docker compose --profile default down
```

#### 2. View logs
```commandline
# View logs for API
docker-compose logs api -f 

# View logs for workers
docker-compose logs worker -f 
```