import os
import tempfile

# Must be set before `app` is imported: use a throwaway database and no scheduler.
os.environ["FLIGHTS_DATA_DIR"] = tempfile.mkdtemp(prefix="flights-test-")
os.environ["FLIGHTS_SCHEDULER"] = "0"
os.environ["FLIGHTS_MIN_BASELINE_SAMPLES"] = "3"

import pytest  # noqa: E402

from app import config, db, deals  # noqa: E402


@pytest.fixture()
def conn():
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    deals._baseline_cache = None
    with db.connect() as c:
        db.init_db(c)
        yield c
