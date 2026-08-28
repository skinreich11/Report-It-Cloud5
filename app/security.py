from dataclasses import dataclass, field
from time import time
from urllib.parse import urlparse


@dataclass
class InMemoryRateLimiter:
    attempts_by_key: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, key, *, max_requests, window_seconds):
        now = time()
        window_start = now - window_seconds
        recent_attempts = [
            timestamp
            for timestamp in self.attempts_by_key.get(key, [])
            if timestamp >= window_start
        ]

        if len(recent_attempts) >= max_requests:
            self.attempts_by_key = {**self.attempts_by_key, key: recent_attempts}
            return False

        self.attempts_by_key = {**self.attempts_by_key, key: [*recent_attempts, now]}
        return True


def request_origin_is_allowed(request):
    origin = request.headers.get("Origin")
    if not origin:
        return True

    parsed_origin = urlparse(origin)
    return parsed_origin.netloc == request.host
