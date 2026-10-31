from django.conf import settings

from config import throttle


def _key(request, poll):
    return throttle.make_key('anonvote', poll.pk, throttle.client_ip(request))


def is_limited(request, poll):
    """True if this network address has used up its anonymous votes."""
    return throttle.get_count(_key(request, poll)) >= settings.ANONYMOUS_VOTES_PER_IP


def record_vote(request, poll):
    throttle.increment(
        _key(request, poll),
        settings.ANONYMOUS_VOTE_WINDOW_SECONDS
    )
