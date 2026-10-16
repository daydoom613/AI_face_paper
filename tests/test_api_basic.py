"""
Very small smoke tests for the Flask API.
You can run them after installing requirements with:

    pytest tests/test_api_basic.py
"""

import threading
import time
from typing import Iterator

import requests

from backend_python import server  # noqa: F401
from config import SERVER_HOST, SERVER_PORT


def wait_server(timeout: float = 5.0) -> None:
    start = time.time()
    url = f"http://{SERVER_HOST}:{SERVER_PORT}/"
    while time.time() - start < timeout:
        try:
            requests.get(url, timeout=1.0)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("Server did not start in time")


def test_home_endpoint() -> None:
    # Start server in background thread for test (only for local/manual use)
    t = threading.Thread(
        target=server.app.run,
        kwargs={"host": SERVER_HOST, "port": SERVER_PORT, "debug": False},
        daemon=True,
    )
    t.start()
    wait_server()

    resp = requests.get(f"http://{SERVER_HOST}:{SERVER_PORT}/", timeout=2.0)
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "status" in data

