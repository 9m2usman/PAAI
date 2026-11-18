import time
import uuid
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RequestControls(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes=1048576, requests_per_minute=120):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(deque)

    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > self.max_body_bytes:
            response = JSONResponse({"detail": "Request body too large."}, status_code=413)
        else:
            client = request.client.host if request.client else "unknown"
            now = time.monotonic()
            bucket = self.requests[client]
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= self.requests_per_minute:
                response = JSONResponse({"detail": "Rate limit exceeded."}, status_code=429)
            else:
                bucket.append(now)
                response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
