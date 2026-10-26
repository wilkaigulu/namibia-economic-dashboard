"""Shared paths, logging and HTTP helpers.

Every other module imports from here so that scripts work no matter which
directory they are launched from. Previously every path was relative to the
current working directory, which meant the whole pipeline silently broke if you
ran a script from inside src/.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

# --------------------------------------------------------------------------
# Paths — anchored to the repository root, not the working directory
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

CONFIG = ROOT / "config"
DATA = ROOT / "data"

WB_DIR = DATA / "automated" / "world_bank"
CLIMATE_DIR = DATA / "automated" / "climate"
CLIMATE_REGIONS_DIR = CLIMATE_DIR / "regions"
CURATED_DIR = DATA / "curated"
DIMENSION_DIR = DATA / "dimension"
WAREHOUSE_DIR = DATA / "warehouse"

ALL_DIRS = [
    WB_DIR,
    CLIMATE_DIR,
    CLIMATE_REGIONS_DIR,
    CURATED_DIR,
    DIMENSION_DIR,
    WAREHOUSE_DIR,
]


def ensure_dirs() -> None:
    """Create every data directory. Cheap, idempotent, and stops the pipeline
    failing on a fresh clone or a fresh CI runner."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)-22s  %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


# --------------------------------------------------------------------------
# HTTP with retries
# --------------------------------------------------------------------------

class FetchError(RuntimeError):
    """Raised when a remote source cannot be reached after retries.

    The extractors raise this rather than swallowing the error, so a failed
    quarterly refresh shows up as a red CI run instead of as stale CSVs that
    look fresh because the commit step succeeded.
    """


def fetch_json(
    url: str,
    *,
    attempts: int = 4,
    timeout: int = 90,
    backoff: float = 3.0,
    session: requests.Session | None = None,
):
    """GET a URL and return parsed JSON, retrying transient failures."""
    log = get_logger("http")
    sess = session or requests
    last: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = sess.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - re-raised below as FetchError
            last = exc
            if attempt < attempts:
                wait = backoff * attempt
                log.warning(
                    "attempt %s/%s failed (%s); retrying in %.0fs",
                    attempt, attempts, exc, wait,
                )
                time.sleep(wait)

    raise FetchError(f"giving up on {url}: {last}")
"""Shared paths, logging and HTTP helpers.

Every other module imports from here so that scripts work no matter which
directory they are launched from. Previously every path was relative to the
current working directory, which meant the whole pipeline silently broke if you
ran a script from inside src/.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

# --------------------------------------------------------------------------
# Paths — anchored to the repository root, not the working directory
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

CONFIG = ROOT / "config"
DATA = ROOT / "data"

WB_DIR = DATA / "automated" / "world_bank"
CLIMATE_DIR = DATA / "automated" / "climate"
CLIMATE_REGIONS_DIR = CLIMATE_DIR / "regions"
CURATED_DIR = DATA / "curated"
DIMENSION_DIR = DATA / "dimension"
WAREHOUSE_DIR = DATA / "warehouse"

ALL_DIRS = [
    WB_DIR,
    CLIMATE_DIR,
    CLIMATE_REGIONS_DIR,
    CURATED_DIR,
    DIMENSION_DIR,
    WAREHOUSE_DIR,
]


def ensure_dirs() -> None:
    """Create every data directory. Cheap, idempotent, and stops the pipeline
    failing on a fresh clone or a fresh CI runner."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)-22s  %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


# --------------------------------------------------------------------------
# HTTP with retries
# --------------------------------------------------------------------------

class FetchError(RuntimeError):
    """Raised when a remote source cannot be reached after retries.

    The extractors raise this rather than swallowing the error, so a failed
    quarterly refresh shows up as a red CI run instead of as stale CSVs that
    look fresh because the commit step succeeded.
    """


def fetch_json(
    url: str,
    *,
    attempts: int = 4,
    timeout: int = 90,
    backoff: float = 3.0,
    session: requests.Session | None = None,
):
    """GET a URL and return parsed JSON, retrying transient failures."""
    log = get_logger("http")
    sess = session or requests
    last: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = sess.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - re-raised below as FetchError
            last = exc
            if attempt < attempts:
                wait = backoff * attempt
                log.warning(
                    "attempt %s/%s failed (%s); retrying in %.0fs",
                    attempt, attempts, exc, wait,
                )
                time.sleep(wait)

    raise FetchError(f"giving up on {url}: {last}")
