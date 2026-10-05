from app.core.database_url import migration_sync_url, normalize_async_url

NEON = (
    "postgresql://user:p%40ss@ep-cool-darkness-123456-pooler.ap-southeast-1.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


def test_neon_pooled_url_becomes_asyncpg() -> None:
    url, args = normalize_async_url(NEON)
    assert url.startswith("postgresql+asyncpg://")
    assert "-pooler." in url
    assert "sslmode" not in url
    assert "channel_binding" not in url
    assert args["ssl"] is True
    assert args["statement_cache_size"] == 0
    assert "p%40ss" in url


def test_migration_url_uses_direct_host() -> None:
    url = migration_sync_url(NEON)
    assert url.startswith("postgresql+psycopg2://")
    assert "-pooler" not in url
    assert "ep-cool-darkness-123456.ap-southeast-1.aws.neon.tech" in url
    assert "sslmode=require" in url
    assert "channel_binding" not in url


def test_postgres_scheme_and_quotes() -> None:
    url, args = normalize_async_url('"postgres://user:pass@localhost:5432/repz"')
    assert url == "postgresql+asyncpg://user:pass@localhost:5432/repz"
    assert args == {}


def test_direct_neon_host_keeps_statement_cache() -> None:
    raw = "postgresql://user:pass@ep-cool.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    url, args = normalize_async_url(raw)
    assert "statement_cache_size" not in args
    assert args["ssl"] is True
    migrated = migration_sync_url(raw)
    assert migrated.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in migrated
    assert "ep-cool.ap-southeast-1.aws.neon.tech" in migrated
