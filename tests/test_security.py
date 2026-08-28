from types import SimpleNamespace

from app.security import InMemoryRateLimiter, request_origin_is_allowed


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter()

    assert limiter.allow("127.0.0.1", max_requests=1, window_seconds=60) is True
    assert limiter.allow("127.0.0.1", max_requests=1, window_seconds=60) is False


def test_request_origin_is_allowed_for_same_host_or_missing_origin():
    same_origin_request = SimpleNamespace(
        headers={"Origin": "http://localhost:5000"},
        host="localhost:5000",
    )
    no_origin_request = SimpleNamespace(headers={}, host="localhost:5000")

    assert request_origin_is_allowed(same_origin_request) is True
    assert request_origin_is_allowed(no_origin_request) is True
