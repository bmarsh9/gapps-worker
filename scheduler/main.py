from config import Config
import requests
from datetime import datetime, timedelta
from time import sleep
from croniter import croniter
import logging
import sys

logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


def should_schedule(dep, now):
    last = dep.get(" ")
    if not last:
        return True

    last = datetime.fromisoformat(last)

    try:
        next_run = croniter(dep["schedule"], last).get_next(datetime)
        return now >= next_run
    except Exception:
        return False


def scheduler_loop():
    while True:
        try:
            now = datetime.utcnow()
            r = requests.get(f"{Config.INTEGRATIONS_BASE_URL}/api/deployments/scheduled")
            r.raise_for_status()
            deployments = r.json()
            logger.info(f"Received {len(deployments)} deployments from API server")
            for dep in deployments:
                if should_schedule(dep, now):
                    job_payload = {"deployment_id": dep["id"]}
                    resp = requests.post(
                        f"{Config.INTEGRATIONS_BASE_URL}/jobs", json=job_payload
                    )
                    resp.raise_for_status()

        except Exception as e:
            logger.error(f"[Scheduler error] {e}")

        sleep(Config.POLL_INTERVAL)


if __name__ == "__main__":
    scheduler_loop()
