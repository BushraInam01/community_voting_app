from datetime import timedelta

from django.test import TestCase, override_settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from config.testing import make_poll, make_user
from polls.models import Poll, PollOption
from .models import Vote, RankedVote
from .views import ANONYMOUS_COOKIE_NAME


class VotingConstraintTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='TestPassword123!'
        )

        self.poll = Poll.objects.create(
            question='Test Poll',
            created_by=self.user,
            expires_at=timezone.now() + timedelta(days=1)
        )

        self.option1 = PollOption.objects.create(
            poll=self.poll,
            option_text='Option 1'
        )

        self.option2 = PollOption.objects.create(
            poll=self.poll,
            option_text='Option 2'
        )

    # Vote model tests

    def test_user_cannot_vote_twice(self):

        Vote.objects.create(
            poll=self.poll,
            option=self.option1,
            user=self.user
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(
                    poll=self.poll,
                    option=self.option2,
                    user=self.user
                )

    def test_anonymous_token_cannot_vote_twice(self):

        Vote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_token='anonymous-test-token'
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(
                    poll=self.poll,
                    option=self.option2,
                    voter_token='anonymous-test-token'
                )

    # RankedVote model tests

    def test_user_cannot_use_same_rank_twice(self):

        RankedVote.objects.create(
            poll=self.poll,
            option=self.option1,
            user=self.user,
            rank=1
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RankedVote.objects.create(
                    poll=self.poll,
                    option=self.option2,
                    user=self.user,
                    rank=1
                )

    def test_user_cannot_rank_same_option_twice(self):

        RankedVote.objects.create(
            poll=self.poll,
            option=self.option1,
            user=self.user,
            rank=1
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RankedVote.objects.create(
                    poll=self.poll,
                    option=self.option1,
                    user=self.user,
                    rank=2
                )

    def test_anonymous_voter_cannot_use_same_rank_twice(self):

        RankedVote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_token='anonymous-test-token',
            rank=1
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RankedVote.objects.create(
                    poll=self.poll,
                    option=self.option2,
                    voter_token='anonymous-test-token',
                    rank=1
                )

    def test_anonymous_voter_cannot_rank_same_option_twice(self):

        RankedVote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_token='anonymous-test-token',
            rank=1
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RankedVote.objects.create(
                    poll=self.poll,
                    option=self.option1,
                    voter_token='anonymous-test-token',
                    rank=2
                )



class VoteViewTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user = make_user('voter')
        self.owner = make_user('owner')

    def vote_url(self, poll):
        return reverse('voting:poll_vote', args=[poll.slug])

    def detail_url(self, poll):
        return reverse('polls:poll_detail', args=[poll.slug])

    # --- named (authenticated) polls

    def test_login_required_for_named_poll(self):
        poll = make_poll(self.owner)

        response = self.client.get(self.vote_url(poll))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])

    def test_user_can_vote_once(self):
        poll = make_poll(self.owner)
        option = poll.options.first()
        self.client.force_login(self.user)

        response = self.client.post(self.vote_url(poll), {'option': option.id})

        self.assertRedirects(response, self.detail_url(poll))
        self.assertEqual(Vote.objects.filter(poll=poll, user=self.user).count(), 1)

        # A second attempt (even for another option) is refused.
        other = poll.options.last()
        self.client.post(self.vote_url(poll), {'option': other.id})
        self.assertEqual(Vote.objects.filter(poll=poll).count(), 1)
        self.assertEqual(Vote.objects.get(poll=poll).option, option)

    def test_cannot_vote_for_option_of_another_poll(self):
        poll = make_poll(self.owner)
        other_poll = make_poll(self.owner, question='Other poll')
        self.client.force_login(self.user)

        response = self.client.post(
            self.vote_url(poll),
            {'option': other_poll.options.first().id}
        )

        self.assertEqual(response.status_code, 200)  # form re-rendered
        self.assertEqual(Vote.objects.count(), 0)

    def test_expired_poll_rejects_votes(self):
        poll = make_poll(self.owner, expires_in=-timedelta(minutes=1))
        self.client.force_login(self.user)

        response = self.client.post(
            self.vote_url(poll), {'option': poll.options.first().id}
        )

        self.assertRedirects(response, self.detail_url(poll))
        self.assertEqual(Vote.objects.count(), 0)

    def test_frozen_poll_rejects_votes(self):
        poll = make_poll(self.owner, frozen=True)
        self.client.force_login(self.user)

        self.client.post(
            self.vote_url(poll), {'option': poll.options.first().id}
        )

        self.assertEqual(Vote.objects.count(), 0)

    # --- anonymous polls

    def test_anonymous_vote_sets_cookie_and_blocks_repeat(self):
        poll = make_poll(self.owner, anonymous=True)
        option = poll.options.first()

        response = self.client.post(self.vote_url(poll), {'option': option.id})

        self.assertIn(ANONYMOUS_COOKIE_NAME, response.cookies)
        self.assertTrue(response.cookies[ANONYMOUS_COOKIE_NAME]['httponly'])
        self.assertEqual(Vote.objects.filter(poll=poll).count(), 1)
        self.assertIsNone(Vote.objects.get(poll=poll).user)

        # Same browser (the test client keeps cookies) cannot vote again.
        self.client.post(self.vote_url(poll), {'option': option.id})
        self.assertEqual(Vote.objects.filter(poll=poll).count(), 1)

    def test_forged_cookie_is_ignored(self):
        poll = make_poll(self.owner, anonymous=True)
        self.client.cookies[ANONYMOUS_COOKIE_NAME] = 'not-a-signed-token'

        response = self.client.post(
            self.vote_url(poll), {'option': poll.options.first().id}
        )

        self.assertEqual(Vote.objects.count(), 1)
        self.assertNotEqual(
            Vote.objects.get().voter_token, 'not-a-signed-token'
        )
        self.assertIn(ANONYMOUS_COOKIE_NAME, response.cookies)

    @override_settings(ANONYMOUS_VOTES_PER_IP=2)
    def test_cookieless_votes_are_limited_per_ip(self):
        from django.test import Client

        poll = make_poll(self.owner, anonymous=True)
        option = poll.options.first()

        for _ in range(5):
            Client().post(self.vote_url(poll), {'option': option.id})

        self.assertEqual(Vote.objects.filter(poll=poll).count(), 2)

    @override_settings(ANONYMOUS_VOTES_PER_IP=1)
    def test_ip_limit_is_per_poll_and_per_address(self):
        from django.test import Client

        poll_a = make_poll(self.owner, anonymous=True, question='Poll A')
        poll_b = make_poll(self.owner, anonymous=True, question='Poll B')

        Client().post(self.vote_url(poll_a), {'option': poll_a.options.first().id})
        Client().post(self.vote_url(poll_a), {'option': poll_a.options.first().id})
        Client().post(self.vote_url(poll_b), {'option': poll_b.options.first().id})
        Client(REMOTE_ADDR='10.0.0.9').post(
            self.vote_url(poll_a), {'option': poll_a.options.first().id}
        )

        self.assertEqual(Vote.objects.filter(poll=poll_a).count(), 2)
        self.assertEqual(Vote.objects.filter(poll=poll_b).count(), 1)

    # --- ranked polls

    def test_ranked_vote_saves_all_ranks(self):
        poll = make_poll(
            self.owner, voting_type='ranked', options=('A', 'B', 'C')
        )
        a, b, c = poll.options.all()
        self.client.force_login(self.user)

        response = self.client.post(self.vote_url(poll), {
            f'option_{a.id}': '2',
            f'option_{b.id}': '3',
            f'option_{c.id}': '1',
        })

        self.assertRedirects(response, self.detail_url(poll))
        ranks = dict(
            RankedVote.objects.filter(poll=poll, user=self.user)
            .values_list('option__option_text', 'rank')
        )
        self.assertEqual(ranks, {'A': 2, 'B': 3, 'C': 1})

    def test_ranked_vote_rejects_duplicate_ranks(self):
        poll = make_poll(self.owner, voting_type='ranked')
        a, b = poll.options.all()
        self.client.force_login(self.user)

        response = self.client.post(self.vote_url(poll), {
            f'option_{a.id}': '1',
            f'option_{b.id}': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'unique rank')
        self.assertEqual(RankedVote.objects.count(), 0)

    def test_ranked_vote_rejects_missing_rank(self):
        poll = make_poll(self.owner, voting_type='ranked')
        a, _ = poll.options.all()
        self.client.force_login(self.user)

        response = self.client.post(self.vote_url(poll), {f'option_{a.id}': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RankedVote.objects.count(), 0)
