from alembic.config import Config

from alembic import command
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("alembic_upgraded")
