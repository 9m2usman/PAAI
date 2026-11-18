import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    auth_secret: str
    auth_database: str
    memory_database: str
    autonomy_database: str
    host: str
    port: int
    log_level: str
    cors_origins: list
    max_request_bytes: int
    requests_per_minute: int
    token_lifetime_seconds: int
    docs_enabled: bool

def get_settings():
    load_dotenv()
    secret = os.getenv("PAAI_AUTH_SECRET", "").strip()
    if len(secret.encode()) < 32 or secret.startswith("replace_with_"):
        raise ValueError("PAAI_AUTH_SECRET must be a strong random secret of at least 32 characters.")
    data_dir = Path(os.getenv("PAAI_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    origins = [item.strip() for item in os.getenv("PAAI_CORS_ORIGINS", "").split(",") if item.strip()]
    return Settings(
        auth_secret=secret,
        auth_database=os.getenv("PAAI_AUTH_DATABASE", str(data_dir / "paai_auth.db")),
        memory_database=os.getenv("PAAI_MEMORY_DATABASE", str(data_dir / "paai_memory.db")),
        autonomy_database=os.getenv("PAAI_AUTONOMY_DATABASE", str(data_dir / "paai_autonomy.db")),
        host=os.getenv("PAAI_HOST", "0.0.0.0"),
        port=int(os.getenv("PAAI_PORT", "8000")),
        log_level=os.getenv("PAAI_LOG_LEVEL", "INFO").upper(),
        cors_origins=origins,
        max_request_bytes=int(os.getenv("PAAI_MAX_REQUEST_BYTES", "1048576")),
        requests_per_minute=int(os.getenv("PAAI_REQUESTS_PER_MINUTE", "120")),
        token_lifetime_seconds=int(os.getenv("PAAI_TOKEN_LIFETIME_SECONDS", "3600")),
        docs_enabled=os.getenv("PAAI_ENABLE_DOCS", "false").lower() == "true",
    )
