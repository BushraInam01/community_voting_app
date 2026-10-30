from django import forms
from django.forms import inlineformset_factory
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


PollOptionFormSet = inlineformset_factory(
    Poll,
    PollOption,
    form=PollOptionForm,
    extra=4,
    min_num=2,
    validate_min=True,
    can_delete=False,
)