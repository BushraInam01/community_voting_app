from django.conf import settings

from config import throttle


def _pair_key(request, username):
    return throttle.make_key('login', throttle.client_ip(request), username)


def _ip_key(request):
    return throttle.make_key('login-ip', throttle.client_ip(request))


def _username_key(username):
    return throttle.make_key('login-user', username.strip())


def is_locked_out(request, username):
    """True if this IP + username, this IP, or this username has failed too often."""

    return (
        throttle.get_count(_pair_key(request, username))
        >= settings.LOGIN_MAX_FAILURES
        or throttle.get_count(_ip_key(request))
        >= settings.LOGIN_MAX_FAILURES_PER_IP
        or throttle.get_count(_username_key(username))
        >= settings.LOGIN_MAX_FAILURES_PER_USERNAME
    )


def record_failure(request, username):
    throttle.increment(
        _pair_key(request, username), settings.LOGIN_LOCKOUT_SECONDS
    )
    throttle.increment(
        _ip_key(request), settings.LOGIN_FAILURE_WINDOW_SECONDS
    )
    throttle.increment(
        _username_key(username), settings.LOGIN_FAILURE_WINDOW_SECONDS
    )


def clear_failures(request, username):
    # Only the IP + username counter is reset. The per-IP and per-username
    # counters keep counting so that one successful login cannot be used to
    # wipe an attacker's history.
    throttle.reset(_pair_key(request, username))
