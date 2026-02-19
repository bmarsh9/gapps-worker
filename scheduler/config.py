import os


class Config:
    INTEGRATIONS_BASE_URL = os.getenv("INTEGRATIONS_BASE_URL", "http://localhost:8080")
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))  # seconds
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "3600"))  # fallback default
