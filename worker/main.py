import logging
import time
import traceback
import random
import requests
from config import Config
from sync import syncer
from runner import run_integration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self):
        self.integrations_base_url = Config.INTEGRATIONS_BASE_URL
        self.queue = Config.QUEUE
        self.poll_interval = Config.POLL_INTERVAL

    def run_forever(self):
        # Sync on startup before polling
        logger.info("Running initial sync...")
        syncer.sync()
        syncer.start_background_sync()

        while True:
            job = self.fetch_job()
            if not job:
                logger.info("No job found. Sleeping...")
                self.sleep_with_jitter()
                continue

            logger.info(f"Running job: {job['id']}. Deployment: {job['deployment_id']}")
            try:
                result, status = self.process_job(job)
            except Exception:
                tb = traceback.format_exc()
                logger.error(f"Error running job {job['id']}:\n{tb}")
                result = {"error": tb}
                status = "error"

            self.post_result(job["id"], status, result)
            self.sleep_with_jitter()

    def fetch_job(self):
        try:
            resp = requests.get(
                f"{self.integrations_base_url}/jobs/next",
                params={"queue": self.queue}
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error fetching job: {e}")
            return None

    def process_job(self, job):
        config = job["config"]
        config["job_id"] = job["id"]

        result = run_integration(
            integration_name=job["integration_name"],
            config=config,
            timeout=job.get("timeout", 3600)
        )
        return result, "done"

    def post_result(self, job_id, status, result):
        try:
            requests.post(
                f"{self.integrations_base_url}/jobs/{job_id}/complete",
                json={"status": status, "result": result},
            )
            logger.info(f"Posted result for job {job_id}")
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Failed to post result for job {job_id}:\n{tb}")

    def sleep_with_jitter(self):
        jitter = random.uniform(0, self.poll_interval * 0.5)
        time.sleep(self.poll_interval + jitter)


if __name__ == "__main__":
    JobWorker().run_forever()