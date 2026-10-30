from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q

from polls.models import Poll, PollOption


class Vote(models.Model):

    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='votes'
    )

    option = models.ForeignKey(
        PollOption,
        on_delete=models.CASCADE,
        related_name='votes'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='votes'
    )

    voter_token = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['poll', 'user'],
                condition=Q(user__isnull=False),
                name='uniq_vote_user_poll'
            ),
            models.UniqueConstraint(
                fields=['poll', 'voter_token'],
                condition=Q(voter_token__isnull=False),
                name='uniq_vote_token_poll'
            ),
        ]

    def __str__(self):
        return f'{self.poll.question} - {self.option.option_text}'


class RankedVote(models.Model):

    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='ranked_votes'
    )

    option = models.ForeignKey(
        PollOption,
        on_delete=models.CASCADE,
        related_name='ranked_votes'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ranked_votes'
    )

    voter_token = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    rank = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['poll', 'user', 'rank'],
                condition=Q(user__isnull=False),
                name='uniq_rank_user_position'
            ),
            models.UniqueConstraint(
                fields=['poll', 'user', 'option'],
                condition=Q(user__isnull=False),
                name='uniq_rank_user_option'
            ),
            models.UniqueConstraint(
                fields=['poll', 'voter_token', 'rank'],
                condition=Q(voter_token__isnull=False),
                name='uniq_rank_token_position'
            ),
            models.UniqueConstraint(
                fields=['poll', 'voter_token', 'option'],
                condition=Q(voter_token__isnull=False),
                name='uniq_rank_token_option'
            ),
        ]

    def __str__(self):
        return f'{self.poll.question} - Rank {self.rank}'
