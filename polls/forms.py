from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.conf import settings
from django.utils import timezone

from .models import Poll, PollOption


class PollForm(forms.ModelForm):

    class Meta:
        model = Poll

        fields = [
            'question',
            'description',
            'voting_type',
            'is_anonymous',
            'expires_at',
        ]

        widgets = {
            'question': forms.TextInput(
                attrs={
                    'placeholder': 'Enter your poll question',
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Describe your poll',
                }
            ),

            'expires_at': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['expires_at'].help_text = (
            f'Time zone: {settings.TIME_ZONE}'
        )

    def clean_expires_at(self):

        expires_at = self.cleaned_data.get('expires_at')

        if expires_at and expires_at <= timezone.now():
            raise forms.ValidationError(
                'Expiry date and time must be in the future.'
            )

        return expires_at


class PollOptionForm(forms.ModelForm):

    class Meta:
        model = PollOption

        fields = [
            'option_text',
        ]

        widgets = {
            'option_text': forms.TextInput(
                attrs={
                    'placeholder': 'Enter poll option',
                }
            ),
        }


MAX_OPTIONS = 10


class BasePollOptionFormSet(BaseInlineFormSet):
    """Rejects repeated options ("Yes", "yes", " YES ") across the formset."""

    def clean(self):
        super().clean()

        # Let each form show its own errors first.
        if any(self.errors):
            return

        seen = set()

        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                continue

            text = (form.cleaned_data.get('option_text') or '').strip()

            if not text:
                continue

            key = text.casefold()

            if key in seen:
                raise forms.ValidationError(
                    f'Each option must be different. "{text}" is repeated.'
                )

            seen.add(key)


PollOptionFormSet = inlineformset_factory(
    Poll,
    PollOption,
    form=PollOptionForm,
    formset=BasePollOptionFormSet,
    extra=4,
    min_num=2,
    max_num=MAX_OPTIONS,
    validate_min=True,
    validate_max=True,
    # Refuse absurd TOTAL_FORMS values early instead of validating them all.
    absolute_max=MAX_OPTIONS + 10,
    can_delete=False,
)
