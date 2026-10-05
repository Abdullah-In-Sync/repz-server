import base64
import json
from pathlib import Path

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _credentials_from_env():
    raw = settings.firebase_credentials_json.strip()
    if not raw:
        return None
    if raw.startswith("{"):
        info = json.loads(raw)
    else:
        info = json.loads(base64.b64decode(raw))
    return credentials.Certificate(info)


def init_firebase() -> None:
    if firebase_admin._apps:
        return
    cred = _credentials_from_env()
    if cred is None:
        cred_path = Path(settings.firebase_credentials_path)
        if not cred_path.exists():
            if settings.is_test:
                logger.warning("firebase_credentials_missing_test_mode", path=str(cred_path))
                return
            raise FileNotFoundError(
                "Firebase credentials not found. Set FIREBASE_CREDENTIALS_JSON "
                f"or place the service-account file at {cred_path}"
            )
        cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)
    logger.info("firebase_initialized")
