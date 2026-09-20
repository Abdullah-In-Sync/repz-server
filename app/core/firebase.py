from pathlib import Path

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def init_firebase() -> None:
    if firebase_admin._apps:
        return
    cred_path = Path(settings.firebase_credentials_path)
    if not cred_path.exists():
        if settings.is_test:
            logger.warning("firebase_credentials_missing_test_mode", path=str(cred_path))
            return
        raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)
    logger.info("firebase_initialized")
