from collections import Counter, defaultdict
from threading import Lock
from time import perf_counter

_started = perf_counter()
_requests: Counter[tuple[str, str, int]] = Counter()
_duration: defaultdict[tuple[str, str], float] = defaultdict(float)
_lock = Lock()


def observe(method: str, route: str, status_code: int, duration_seconds: float) -> None:
    with _lock:
        _requests[(method, route, status_code)] += 1
        _duration[(method, route)] += duration_seconds


def render_metrics() -> str:
    lines = [
        "# HELP dpp_uptime_seconds Process uptime.",
        "# TYPE dpp_uptime_seconds gauge",
        f"dpp_uptime_seconds {perf_counter() - _started:.3f}",
        "# HELP dpp_http_requests_total HTTP requests by method, route, and status.",
        "# TYPE dpp_http_requests_total counter",
    ]
    with _lock:
        for (method, route, status), count in sorted(_requests.items()):
            lines.append(
                "dpp_http_requests_total"
                f'{{method="{method}",route="{route}",status="{status}"}} {count}'
            )
        lines.extend([
            "# HELP dpp_http_request_duration_seconds_total Total request duration.",
            "# TYPE dpp_http_request_duration_seconds_total counter",
        ])
        for (method, route), duration in sorted(_duration.items()):
            lines.append(
                "dpp_http_request_duration_seconds_total"
                f'{{method="{method}",route="{route}"}} {duration:.6f}'
            )
    return "\n".join(lines) + "\n"
