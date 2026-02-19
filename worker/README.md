### How to create an integration

See the `hello_world` integration defined under `integrations/hello_world` as an example for creating an integration. Each integration must have their own folder defined under `integrations` and must follow the same Class schema defined in the hello_world `entry.py` file.

All tasks for an integration should be placed under the `tasks` folder as shown with the `hello_world` integration. Each task must have the `@task` decorator in order to be registered.

```commandline
@task(
    name="name_of_the_task",
    title="Title of the task",
    description="Description of the task",
    order=1 # specify which order the task is executed in. 100 by default
    type="insight" # collector or insight, by default it is collector
    enabled=False # disable the task
)
```

When you execute an integration, you can also pass in a `config` dictionary (JSON) that specifies how the integration should run.
```commandline
config = {
    "access_key": "AKIAEXAMPLE123",
    "secret_key": "superSecretKeyExample",
    "region": "us-east-1",
    "task_timeout": 10,  # timeout for each task
    "tasks": ["list_buckets", "list_buckets_v2"]  # specify specific tasks (by name) to ONLY run. If you remove this key or leave a empty array, ALL enabled tasks will run
}
```

### How it works
There are a few containers that make up the integrations platform.
- API -> API server that allows you to configure integrations and returns jobs
- Scheduler -> polls the API for deployments that are ready to execute and then creates jobs
- Worker -> polls the API for jobs that are ready to execute
- Database -> Postgres that is used as a relational and queue

You can have as many workers as you'd like. The replica count is defined within the `docker-compose.yml` file. Each worker is blocking. In other words, when a worker container is executing a job, it will execute each task within the job and then after it has finished it will continue polling the API for new jobs.

### Start the integration platform

```commandline
docker compose --profile default up --build -d
```

### Run tests

To create tests, take a look at the `tests/hello_world/test_runner.py` file. Each integration should also have their own folder under `tests`.
```commandline
# With docker-compose
docker-compose run --rm test-worker
```

```commandline
# Run all tests
pytest -s -v -p no:warnings -o log_cli=true tests

# Run all tests for integration "hello_world"
pytest -v -p no:warnings -o log_cli=true tests/hello_world

# Run specific tests for integration "hello_world"
pytest -v -p no:warnings -o log_cli=true tests/hello_world/test_runner.py::test_success_of_tasks

```