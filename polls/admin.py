
from django.contrib import admin
from .models import Poll, PollOption


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2


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

    prepopulated_fields = {}

    inlines = [PollOptionInline]


@admin.register(PollOption)
class PollOptionAdmin(admin.ModelAdmin):
    list_display = ('option_text', 'poll', 'created_at')
    search_fields = ('option_text', 'poll__question')
