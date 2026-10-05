"""Turn a pasted Neon (or local) Postgres URL into driver-specific URLs.

Neon console strings look like:

    postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require&channel_binding=require

asyncpg rejects ``sslmode`` and ``channel_binding``. Alembic (psycopg2) needs the
direct host, because the ``-pooler`` endpoint is PgBouncer in transaction mode.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _clean(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def _swap_driver(url: str, driver: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    base = scheme.split("+", 1)[0]
    if base == "postgres":
        base = "postgresql"
    return f"{base}+{driver}://{rest}"


def _query(url: str) -> tuple[object, dict[str, str]]:
    parts = urlsplit(url)
    return parts, dict(parse_qsl(parts.query, keep_blank_values=True))


def _with_query(parts, query: dict[str, str]) -> str:
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _replace_hostname(netloc: str, old: str | None, new: str, port: int | None) -> str:
    if not old:
        return netloc
    userinfo, sep, _hostport = netloc.rpartition("@")
    hostport = f"{new}:{port}" if port else new
    if sep:
        return f"{userinfo}@{hostport}"
    return hostport


def _direct_host(hostname: str) -> str:
    return hostname.replace("-pooler.", ".", 1)


def normalize_async_url(raw: str) -> tuple[str, dict]:
    """Return ``(postgresql+asyncpg URL, asyncpg connect_args)``."""
    url = _swap_driver(_clean(raw), "asyncpg")
    parts, query = _query(url)
    connect_args: dict = {}

    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    ssl_flag = query.pop("ssl", None)
    if ssl_flag is not None and ssl_flag not in {"0", "false", "disable"}:
        connect_args["ssl"] = True
    elif sslmode and sslmode != "disable":
        connect_args["ssl"] = True

    host = parts.hostname or ""
    if "-pooler." in host:
        connect_args["statement_cache_size"] = 0

    return _with_query(parts, query), connect_args


def migration_sync_url(raw: str) -> str:
    """Direct ``postgresql+psycopg2`` URL for Alembic."""
    url = _swap_driver(_clean(raw), "psycopg2")
    parts, query = _query(url)
    host = parts.hostname or ""
    if "-pooler." in host:
        host = _direct_host(host)
        netloc = _replace_hostname(parts.netloc, parts.hostname, host, parts.port)
        parts = parts._replace(netloc=netloc)

    query.pop("channel_binding", None)
    ssl_flag = query.pop("ssl", None)
    if "sslmode" not in query and ssl_flag not in {None, "0", "false", "disable"}:
        query["sslmode"] = "require"
    if "neon.tech" in host and "sslmode" not in query:
        query["sslmode"] = "require"
    return _with_query(parts, query)
