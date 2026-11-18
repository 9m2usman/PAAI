import logging
import re

_SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(access_token|refresh_token|client_secret|password|api_key)(\s*[:=]\s*)[^\s,;]+"),
]

class SecretRedactionFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        for pattern in _SECRET_PATTERNS:
            message = pattern.sub(r"\1[REDACTED]" if pattern.groups == 1 else r"\1\2[REDACTED]", message)
        record.msg = message
        record.args = ()
        return True

def configure_logging(level="INFO"):
    handler = logging.StreamHandler()
    handler.addFilter(SecretRedactionFilter())
    logging.basicConfig(level=getattr(logging, level, logging.INFO), handlers=[handler], force=True)
