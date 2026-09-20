import os

os.environ["ENVIRONMENT"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ.setdefault("FIREBASE_CREDENTIALS_PATH", "./missing.json")

from app.core.config import get_settings

get_settings.cache_clear()
