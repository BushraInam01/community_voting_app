from datetime import timedelta

from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.auth.models import User
from django.utils import timezone

from polls.models import Poll, PollOption
from .models import Vote, RankedVote


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
