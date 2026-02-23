import os
import glob
import logging
import importlib.util
import sys
import concurrent.futures
from config import Config

logger = logging.getLogger(__name__)


def run_integration(integration_name: str, config: dict, timeout: int = 3600) -> dict:
    """
    Execute an integration by loading its venv site-packages into sys.path
    and importing the entry module directly.

    Args:
        integration_name: The name of the integration (must match folder in integrations/)
        config: The job config dict to pass to the Runner
        timeout: Max seconds to wait for the integration to complete

    Returns:
        dict: The result from the runner

    Raises:
        RuntimeError: If the integration or venv is not found or times out
    """
    integration_path = os.path.join(Config.INTEGRATIONS_DIR, integration_name)
    venv_path = os.path.join(Config.VENVS_DIR, integration_name)

    if not os.path.isdir(integration_path):
        raise RuntimeError(f"Integration '{integration_name}' not found at {integration_path}")

    if not os.path.isdir(venv_path):
        raise RuntimeError(f"Venv for '{integration_name}' not found at {venv_path}. Has sync run?")

    # Find the venv's site-packages
    site_packages = glob.glob(os.path.join(venv_path, "lib", "python*", "site-packages"))
    if not site_packages:
        raise RuntimeError(f"No site-packages found in venv for '{integration_name}'")

    injected_paths = [site_packages[0], integration_path]

    # Inject venv and integration paths at the front of sys.path
    for path in reversed(injected_paths):
        sys.path.insert(0, path)

    logger.info(f"[{integration_name}] Loading integration from {integration_path}")

    try:
        spec = importlib.util.spec_from_file_location(
            f"{integration_name}.entry",
            os.path.join(integration_path, "entry.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Set name from folder so entry.py doesn't need to define it
        module.Runner.name = integration_name
        module.Runner.api_server = Config.INTEGRATIONS_BASE_URL

        runner = module.Runner(config)

        # Run with timeout enforcement
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(runner.run)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise RuntimeError(
                    f"Integration '{integration_name}' timed out after {timeout}s"
                )

    finally:
        # Clean up injected paths from sys.path
        for path in injected_paths:
            if path in sys.path:
                sys.path.remove(path)