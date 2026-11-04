from django.contrib import admin

from .models import Poll, PollOption


class PollOptionInline(admin.TabularInline):
    """Options cannot be added, edited or removed once people have voted:
    that would silently change what existing votes mean."""

    model = PollOption
    extra = 2

    def _locked(self, poll):
        return poll is not None and poll.has_votes

    def has_add_permission(self, request, obj=None):
        return not self._locked(obj)

    def has_change_permission(self, request, obj=None):
        return not self._locked(obj)

    def has_delete_permission(self, request, obj=None):
        return not self._locked(obj)


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = (
        'question',
        'created_by',
        'voting_type',
        'is_anonymous',
        'expires_at',
        'is_frozen',
    )

    list_filter = (
        'voting_type',
        'is_anonymous',
        'is_frozen',
    )

    search_fields = (
        'question',
        'description',
        'slug',
    )

    inlines = [PollOptionInline]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))

        # Changing these after voting would make existing votes meaningless.
        if obj is not None and obj.has_votes:
            readonly += ['voting_type', 'is_anonymous']

        return readonly


@admin.register(PollOption)
class PollOptionAdmin(admin.ModelAdmin):
    list_display = ('option_text', 'poll', 'created_at')
    search_fields = ('option_text', 'poll__question')

    def has_add_permission(self, request):
        # Add options from the poll's own page, where the vote check applies.
        return False

    def has_change_permission(self, request, obj=None):
        return obj is None or not obj.poll.has_votes
