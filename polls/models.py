from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from autoslug import AutoSlugField

from .slugs import poll_slugify


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
        always_update=False,
        slugify=poll_slugify
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

    @property
    def has_votes(self):
        return self.votes.exists() or self.ranked_votes.exists()

    @property
    def is_closed(self):
        return self.is_frozen or self.is_expired

    @property
    def embed_height(self):
        """Iframe height in pixels that fits the embed widget without a
        large blank area or a scrollbar.

        The numbers match static/css/embed.css (about 25px per option line,
        plus the title, padding and the closing link) with a small safety
        margin. If you change that stylesheet, adjust the numbers here.
        """

        height = 110 + 25 * len(self.options.all())

        if self.description:
            height += 30 + 22 * ((len(self.description) - 1) // 70)

        if self.is_closed:
            height += 30

        # A long question wraps onto extra lines.
        height += 22 * ((len(self.question) - 1) // 60)

        return height

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

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.option_text
