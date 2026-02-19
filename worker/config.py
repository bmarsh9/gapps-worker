import os


class Config:
    # API
    INTEGRATIONS_BASE_URL = os.getenv("INTEGRATIONS_BASE_URL", "http://localhost:8080")
    INTEGRATIONS_TOKEN = os.getenv("INTEGRATIONS_TOKEN", "changeme")

    # Worker
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # seconds
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "180"))
    QUEUE = os.getenv("QUEUE", "default")

    # GitHub
    GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL")  # e.g. https://github.com/org/integrations
    GITHUB_RAW_URL = os.getenv("GITHUB_RAW_URL")    # e.g. https://raw.githubusercontent.com/org/repo/main/integrations.json


    # Sync
    SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "300"))  # seconds, default 5 mins

    # Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # /worker
    INTEGRATIONS_DIR = os.path.join(BASE_DIR, "integrations")  # /worker/integrations
    VENVS_DIR = os.path.join(BASE_DIR, "venvs")