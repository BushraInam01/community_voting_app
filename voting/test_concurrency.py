"""Concurrency tests for voting. These need PostgreSQL: SQLite has no
row-level locking, so select_for_update() is a no-op there and parallel
writers just hit "database is locked".

Run with:
    POSTGRES_DB=voting POSTGRES_USER=voting POSTGRES_PASSWORD=voting \\
        python manage.py test voting.test_concurrency
(the database user needs CREATEDB so Django can create the test database)
"""

import threading
import time
from unittest import mock, skipUnless

from django.core import signing
from django.db import DatabaseError, connection, transaction
from django.test import Client, TransactionTestCase
from django.urls import reverse

from common.factories import make_poll, make_user
from polls.models import Poll

from . import views
from .models import RankedVote, Vote
from .views import ANONYMOUS_COOKIE_NAME, ANONYMOUS_TOKEN_SALT

WORKERS = 8


def run_in_parallel(fn, count=WORKERS):
    """Run fn(i) in `count` threads released at the same instant."""

    barrier = threading.Barrier(count)
    results = [None] * count
    errors = []

    def worker(i):
        try:
            barrier.wait()
            results[i] = fn(i)
        except Exception as exc:  # surfaced in the main thread below
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    [t.start() for t in threads]
    [t.join(timeout=30) for t in threads]

    if errors:
        raise errors[0]

    return results


@skipUnless(connection.vendor == 'postgresql', 'Needs PostgreSQL row locking')
class ConcurrentVotingTests(TransactionTestCase):

    def setUp(self):
        self.owner = make_user('owner')

    def vote_url(self, poll):
        return reverse('voting:poll_vote', args=[poll.slug])

    def test_same_user_voting_in_parallel_counts_once(self):
        poll = make_poll(self.owner)
        voter = make_user('voter')
        option = poll.options.first()
        clients = []
        for _ in range(WORKERS):
            client = Client()
            client.force_login(voter)
            clients.append(client)

        responses = run_in_parallel(
            lambda i: clients[i].post(self.vote_url(poll), {'option': option.id})
        )

        self.assertEqual(Vote.objects.filter(poll=poll).count(), 1)
        self.assertTrue(all(r.status_code == 302 for r in responses))

    def test_same_anonymous_token_in_parallel_counts_once(self):
        poll = make_poll(self.owner, anonymous=True)
        option = poll.options.first()
        token = signing.dumps('shared-browser', salt=ANONYMOUS_TOKEN_SALT)
        clients = []
        for _ in range(WORKERS):
            client = Client()
            client.cookies[ANONYMOUS_COOKIE_NAME] = token
            clients.append(client)

        run_in_parallel(
            lambda i: clients[i].post(self.vote_url(poll), {'option': option.id})
        )

        self.assertEqual(Vote.objects.filter(poll=poll).count(), 1)

    def test_parallel_ranked_ballots_are_never_partial_or_duplicated(self):
        poll = make_poll(self.owner, voting_type='ranked', options=('A', 'B', 'C'))
        a, b, c = poll.options.all()
        voter = make_user('voter')
        clients = []
        for _ in range(WORKERS):
            client = Client()
            client.force_login(voter)
            clients.append(client)

        run_in_parallel(
            lambda i: clients[i].post(self.vote_url(poll), {
                f'option_{a.id}': '1', f'option_{b.id}': '2', f'option_{c.id}': '3',
            })
        )

        self.assertEqual(RankedVote.objects.filter(poll=poll).count(), 3)

    def test_many_different_voters_in_parallel_are_all_counted(self):
        poll = make_poll(self.owner, anonymous=True)
        option = poll.options.first()

        run_in_parallel(
            lambda i: Client().post(self.vote_url(poll), {'option': option.id})
        )

        self.assertEqual(Vote.objects.filter(poll=poll).count(), WORKERS)

    def test_select_for_update_really_locks_the_poll_row(self):
        poll = make_poll(self.owner)
        outcome = {}

        def second_transaction():
            try:
                with transaction.atomic():
                    Poll.objects.select_for_update(nowait=True).get(pk=poll.pk)
                outcome['result'] = 'acquired'
            except DatabaseError:
                outcome['result'] = 'blocked'
            finally:
                connection.close()

        with transaction.atomic():
            Poll.objects.select_for_update().get(pk=poll.pk)
            thread = threading.Thread(target=second_transaction)
            thread.start()
            thread.join(timeout=10)

        self.assertEqual(outcome['result'], 'blocked')

    def test_closing_a_poll_waits_for_votes_already_in_flight(self):
        """The real job of the lock: a vote that has already checked the poll
        is open must finish before the poll can be frozen, so no vote can
        slip in after the freeze.

        The real view is paused part-way through its transaction (just after
        it has taken the lock and re-checked that the poll is open). Without
        select_for_update() in the view, the freeze would complete
        immediately and this test fails.
        """

        poll = make_poll(self.owner)
        option = poll.options.first()
        voter = make_user('voter')
        client = Client()
        client.force_login(voter)

        holding_lock = threading.Event()
        release_vote = threading.Event()
        close_finished = threading.Event()
        calls = {'n': 0}
        real_has_voted = views.has_voted

        def pausing_has_voted(*args, **kwargs):
            calls['n'] += 1
            # 1st call: pre-check outside the transaction.
            # 2nd call: inside the transaction, after the poll row is locked.
            if calls['n'] == 2:
                holding_lock.set()
                release_vote.wait(timeout=10)
            return real_has_voted(*args, **kwargs)

        def voter_request():
            try:
                client.post(self.vote_url(poll), {'option': option.id})
            finally:
                connection.close()

        def closer():
            try:
                # What the "close poll" view does.
                Poll.objects.filter(pk=poll.pk).update(is_frozen=True)
                close_finished.set()
            finally:
                connection.close()

        with mock.patch.object(views, 'has_voted', pausing_has_voted):
            vote_thread = threading.Thread(target=voter_request)
            vote_thread.start()
            self.assertTrue(holding_lock.wait(timeout=10))

            close_thread = threading.Thread(target=closer)
            close_thread.start()
            time.sleep(0.5)

            # The freeze is queued behind the in-flight vote...
            self.assertFalse(close_finished.is_set())

            release_vote.set()
            vote_thread.join(timeout=10)
            close_thread.join(timeout=10)

        # ...then both complete: the vote counted, and the poll is frozen.
        self.assertTrue(close_finished.is_set())
        self.assertEqual(Vote.objects.filter(poll=poll).count(), 1)
        self.assertTrue(Poll.objects.get(pk=poll.pk).is_frozen)

    def test_vote_arriving_after_freeze_is_rejected(self):
        poll = make_poll(self.owner)
        voter = make_user('voter')
        client = Client()
        client.force_login(voter)

        Poll.objects.filter(pk=poll.pk).update(is_frozen=True)
        client.post(self.vote_url(poll), {'option': poll.options.first().id})

        self.assertEqual(Vote.objects.filter(poll=poll).count(), 0)
