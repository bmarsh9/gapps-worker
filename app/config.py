import os


class Config:
    INTEGRATIONS_BASE_URL = os.getenv("INTEGRATIONS_BASE_URL", "http://localhost:8080")
    INTEGRATIONS_TOKEN = os.getenv("INTEGRATIONS_TOKEN", "changeme")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
    GITHUB_RAW_URL = os.getenv(
        "GITHUB_RAW_URL")  # e.g. https://raw.githubusercontent.com/org/repo/main/integrations.json
