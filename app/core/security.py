from firebase_admin import auth
from firebase_admin.auth import ExpiredIdTokenError, InvalidIdTokenError

from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthError(Exception):
    def __init__(self, message: str = "Invalid authentication token") -> None:
        self.message = message
        super().__init__(message)


def verify_firebase_token(id_token: str) -> dict:
    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except ExpiredIdTokenError as exc:
        logger.warning("auth_token_expired")
        raise AuthError("Expired authentication token") from exc
    except InvalidIdTokenError as exc:
        logger.warning("auth_token_invalid")
        raise AuthError("Invalid authentication token") from exc
    except Exception as exc:
        logger.warning("auth_token_failed", error=str(exc))
        raise AuthError("Invalid authentication token") from exc
