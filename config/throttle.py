"""Tiny cache-backed counters used for rate limiting.

Counters are stored in Django's default cache. The default LocMemCache is
per-process, so use a shared cache (Redis, Memcached, database cache) in
production if you run more than one worker.

Only REMOTE_ADDR is used to identify clients. X-Forwarded-For is
client-controlled unless a trusted proxy overwrites it, so trusting it blindly
would let anyone dodge the limits. If you deploy behind a reverse proxy,
configure the proxy / WSGI server so REMOTE_ADDR is the real client address.
"""

import hashlib

from django.core.cache import cache


def client_ip(request):
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def make_key(prefix, *parts):
    """Build a cache key; parts are hashed so no raw IPs/usernames are stored."""
    digest = hashlib.sha256(
        '|'.join(str(part).lower() for part in parts).encode()
    ).hexdigest()
    return f'throttle:{prefix}:{digest}'


def get_count(key):
    return cache.get(key, 0)


def increment(key, window_seconds):
    """Increment a counter, starting a new window if it did not exist."""
    if cache.add(key, 1, window_seconds):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        # Key expired between add() and incr(); start a fresh window.
        cache.set(key, 1, window_seconds)
        return 1


def reset(key):
    cache.delete(key)
