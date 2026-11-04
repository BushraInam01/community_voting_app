"""Small factories shared by the test suites (not part of the running site)."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from polls.models import Poll, PollOption


def make_user(username='alice', password='TestPassword123!'):
    return User.objects.create_user(username=username, password=password)


def make_poll(
    user,
    question='Which database?',
    options=('Postgres', 'SQLite'),
    anonymous=False,
    voting_type='multiple_choice',
    expires_in=timedelta(days=1),
    frozen=False,
):
    poll = Poll.objects.create(
        question=question,
        created_by=user,
        is_anonymous=anonymous,
        voting_type=voting_type,
        expires_at=timezone.now() + expires_in,
        is_frozen=frozen,
    )

    for text in options:
        PollOption.objects.create(poll=poll, option_text=text)

    return poll
