from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from autoslug import AutoSlugField


class Poll(models.Model):

    VOTING_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('ranked', 'Ranked Voting'),
    ]

    question = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    slug = AutoSlugField(
        populate_from='question',
        unique=True,
        max_length=255,
        always_update=False
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_polls'
    )

    voting_type = models.CharField(
        max_length=20,
        choices=VOTING_TYPE_CHOICES,
        default='multiple_choice'
    )

    is_anonymous = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    is_frozen = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return self.question


class PollOption(models.Model):

    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='options'
    )

    option_text = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.option_text