"""Shared pytest fixtures / env loader."""
import os
from pathlib import Path


def _load_frontend_env():
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_frontend_env()
