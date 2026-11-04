from django.contrib import admin

from .models import RankedVote, Vote


class VoteRecordAdmin(admin.ModelAdmin):
    """Votes can be inspected and removed (moderation) but never created or
    edited by hand."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Vote)
class VoteAdmin(VoteRecordAdmin):
    list_display = ('poll', 'option', 'user', 'created_at')
    list_filter = ('poll',)


@admin.register(RankedVote)
class RankedVoteAdmin(VoteRecordAdmin):
    list_display = ('poll', 'option', 'rank', 'user', 'created_at')
    list_filter = ('poll',)
