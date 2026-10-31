from django.conf import settings

from config import throttle


def _key(request, username):
    return throttle.make_key('login', throttle.client_ip(request), username)


def is_locked_out(request, username):
    return throttle.get_count(_key(request, username)) >= settings.LOGIN_MAX_FAILURES


def record_failure(request, username):
    throttle.increment(_key(request, username), settings.LOGIN_LOCKOUT_SECONDS)


def clear_failures(request, username):
    throttle.reset(_key(request, username))
