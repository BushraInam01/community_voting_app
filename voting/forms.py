from django import forms

from polls.models import PollOption


class MultipleChoiceVoteForm(forms.Form):

    option = forms.ModelChoiceField(
        queryset=PollOption.objects.none(),
        widget=forms.RadioSelect,
        label='Select your option'
    )

    def __init__(self, *args, poll=None, **kwargs):
        super().__init__(*args, **kwargs)

        if poll:
            self.fields['option'].queryset = PollOption.objects.filter(
                poll=poll
            )


class RankedVoteForm(forms.Form):

    def __init__(self, *args, poll=None, **kwargs):
        super().__init__(*args, **kwargs)

        if poll:
            options = poll.options.all()
            total_options = options.count()

            rank_choices = [
                (rank, f'{rank}')
                for rank in range(1, total_options + 1)
            ]

            for option in options:
                self.fields[f'option_{option.id}'] = forms.ChoiceField(
                    label=option.option_text,
                    choices=rank_choices,
                    widget=forms.Select()
                )

    def clean(self):
        cleaned_data = super().clean()

        ranks = list(cleaned_data.values())

        if len(ranks) != len(set(ranks)):
            raise forms.ValidationError(
                'Each option must have a unique rank.'
            )

        return cleaned_data