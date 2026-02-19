import os
import subprocess
import logging
import threading
import time
import hashlib
import requests
from config import Config

logger = logging.getLogger(__name__)


class GitHubSync:
    def __init__(self):
        self.repo_url = Config.GITHUB_REPO_URL
        self._req_hashes = {}

        os.makedirs(Config.INTEGRATIONS_DIR, exist_ok=True)
        os.makedirs(Config.VENVS_DIR, exist_ok=True)

    def sync(self):
        """Pull latest code from GitHub and set up venvs for enabled integrations."""
        logger.info("Starting sync with GitHub...")
        try:
            self._pull_repo()
            enabled = self._fetch_enabled_integrations()
            self._setup_integrations(enabled)
            logger.info("Sync complete.")
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise

    def _pull_repo(self):
        """Clone repo if it doesn't exist, otherwise pull latest."""
        git_dir = os.path.join(Config.BASE_DIR, ".git")

        if os.path.isdir(git_dir):
            logger.info("Repo exists, pulling latest...")
            result = subprocess.run(
                ["git", "pull"],
                cwd=Config.BASE_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"git pull failed: {result.stderr}")
            logger.info(result.stdout.strip())
        else:
            logger.info(f"Cloning repo from {self.repo_url}...")
            for cmd in [
                ["git", "init"],
                ["git", "remote", "add", "origin", self.repo_url],
                ["git", "fetch", "origin"],
                ["git", "reset", "--hard", "origin/main"],
            ]:
                result = subprocess.run(
                    cmd,
                    cwd=Config.BASE_DIR,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(f"{' '.join(cmd)} failed: {result.stderr}")
            logger.info("Clone complete.")

    def _fetch_enabled_integrations(self):
        """
        Fetch integrations.json from GitHub and return only enabled integration names.
        """
        try:
            resp = requests.get(Config.GITHUB_RAW_URL, timeout=10)
            resp.raise_for_status()
            integrations = resp.json()
            enabled = [i["name"] for i in integrations if i.get("enabled")]
            logger.info(f"Found {len(enabled)} enabled integrations: {enabled}")
            return enabled
        except Exception as e:
            raise RuntimeError(f"Failed to fetch integrations.json from GitHub: {e}")

    def _setup_integrations(self, enabled: list):
        """For each enabled integration, create venv and install deps if needed."""
        for name in enabled:
            integration_path = os.path.join(Config.INTEGRATIONS_DIR, name)

            if not os.path.isdir(integration_path):
                logger.warning(f"[{name}] Directory not found at {integration_path}, skipping.")
                continue

            if not os.path.isfile(os.path.join(integration_path, "entry.py")):
                logger.warning(f"[{name}] No entry.py found, skipping.")
                continue

            logger.info(f"[{name}] Setting up integration...")
            self._ensure_venv(name, integration_path)

    def _ensure_venv(self, name: str, integration_path: str):
        """Create venv and install base + integration requirements if they've changed."""
        venv_path = os.path.join(Config.VENVS_DIR, name)
        pip_path = os.path.join(venv_path, "bin", "pip")
        base_req = os.path.join(Config.BASE_DIR, "requirements.txt")
        integration_req = os.path.join(integration_path, "requirements.txt")

        # Create venv if it doesn't exist
        if not os.path.isdir(venv_path):
            logger.info(f"[{name}] Creating venv...")
            result = subprocess.run(
                ["python3", "-m", "venv", venv_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"[{name}] venv creation failed: {result.stderr}")

        # Install base requirements (shared utils dependencies)
        if os.path.isfile(base_req):
            current_hash = self._hash_file(base_req)
            if self._req_hashes.get(f"{name}__base") != current_hash:
                logger.info(f"[{name}] Installing base requirements...")
                result = subprocess.run(
                    [pip_path, "install", "-r", base_req],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(f"[{name}] base pip install failed: {result.stderr}")
                self._req_hashes[f"{name}__base"] = current_hash
                logger.info(f"[{name}] Base requirements installed.")
            else:
                logger.info(f"[{name}] Base requirements unchanged, skipping.")
        else:
            logger.warning(f"[{name}] No base requirements.txt found at {base_req}")

        # Install integration-specific requirements
        if os.path.isfile(integration_req):
            current_hash = self._hash_file(integration_req)
            if self._req_hashes.get(name) != current_hash:
                logger.info(f"[{name}] Installing integration requirements...")
                result = subprocess.run(
                    [pip_path, "install", "-r", integration_req],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(f"[{name}] pip install failed: {result.stderr}")
                self._req_hashes[name] = current_hash
                logger.info(f"[{name}] Integration requirements installed.")
            else:
                logger.info(f"[{name}] Integration requirements unchanged, skipping.")
        else:
            logger.info(f"[{name}] No integration requirements.txt found, skipping.")

    def _hash_file(self, path: str) -> str:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def start_background_sync(self):
        """Start a background thread that periodically re-syncs."""
        def loop():
            while True:
                time.sleep(Config.SYNC_INTERVAL)
                try:
                    self.sync()
                except Exception as e:
                    logger.error(f"Background sync error: {e}")

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        logger.info(f"Background sync started. Interval: {Config.SYNC_INTERVAL}s")


# Singleton
syncer = GitHubSync()