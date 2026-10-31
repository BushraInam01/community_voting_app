import uuid

from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core import signing
from django.db import transaction, IntegrityError

from polls.models import Poll
from . import throttle
from .models import Vote, RankedVote
from .forms import MultipleChoiceVoteForm, RankedVoteForm


ANONYMOUS_COOKIE_NAME = 'anonymous_voter_token'
ANONYMOUS_TOKEN_SALT = 'voting.anonymous.voter'


def get_anonymous_token(request):
    """Return (token, is_new) for the anonymous voter cookie.

    The token is signed so it can't be forged, but it only identifies a
    browser, not a person: clearing cookies yields a new token. The per-IP
    limit in voting/throttle.py is the mitigation for that.
    """

    token = request.COOKIES.get(ANONYMOUS_COOKIE_NAME)

    if token:
        try:
            signing.loads(token, salt=ANONYMOUS_TOKEN_SALT)
            return token, False

        except signing.BadSignature:
            pass

    token = signing.dumps(uuid.uuid4().hex, salt=ANONYMOUS_TOKEN_SALT)

    return token, True


def has_voted(poll, user=None, token=None):
    """True if this voter (user for named polls, token for anonymous ones)
    already has a vote or ranked ballot on the poll."""

    if poll.is_anonymous:
        voter = {'voter_token': token}
    else:
        voter = {'user': user}

    return (
        Vote.objects.filter(poll=poll, **voter).exists()
        or RankedVote.objects.filter(poll=poll, **voter).exists()
    )


def get_form(poll, data=None):
    form_class = (
        RankedVoteForm if poll.voting_type == 'ranked'
        else MultipleChoiceVoteForm
    )

    return form_class(data, poll=poll)


class PollVoteView(View):

    def _gate(self, request, poll):
        """Return a redirect response if the voter must not continue."""

        if poll.is_closed:
            messages.error(request, 'This poll is closed.')
            return redirect('polls:poll_detail', slug=poll.slug)

        if not poll.is_anonymous and not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        return None

    def _identify(self, request, poll):
        """Return (user, token, is_new_token) for this voter."""

        if poll.is_anonymous:
            token, is_new = get_anonymous_token(request)
            return None, token, is_new

        return request.user, None, False

    def _already_voted(self, request, poll, user, token):
        if has_voted(poll, user, token):
            messages.info(request, 'You have already voted.')
            return redirect('polls:poll_detail', slug=poll.slug)

        return None

    def get(self, request, slug):

        poll = get_object_or_404(Poll, slug=slug)

        response = self._gate(request, poll)

        if response:
            return response

        user, token, _ = self._identify(request, poll)

        response = self._already_voted(request, poll, user, token)

        if response:
            return response

        context = {
            'poll': poll,
            'form': get_form(poll),
        }

        return render(request, 'voting/vote.html', context)

    def post(self, request, slug):

        poll = get_object_or_404(Poll, slug=slug)

        response = self._gate(request, poll)

        if response:
            return response

        user, token, set_cookie = self._identify(request, poll)

        response = self._already_voted(request, poll, user, token)

        if response:
            return response

        if poll.is_anonymous and throttle.is_limited(request, poll):
            messages.error(
                request,
                'Too many votes have been submitted from your network '
                'for this poll. Please try again later.'
            )
            return redirect('polls:poll_detail', slug=poll.slug)

        form = get_form(poll, request.POST)

        if not form.is_valid():
            context = {
                'poll': poll,
                'form': form,
            }

            return render(request, 'voting/vote.html', context)

        try:
            with transaction.atomic():

                # On databases with row locking (e.g. PostgreSQL) this
                # serialises concurrent votes on the same poll. On SQLite it
                # is a no-op and the unique constraints are the safeguard.
                locked_poll = Poll.objects.select_for_update().get(
                    pk=poll.pk
                )

                if locked_poll.is_closed:
                    messages.error(request, 'This poll is closed.')
                    return redirect('polls:poll_detail', slug=poll.slug)

                response = self._already_voted(
                    request, locked_poll, user, token
                )

                if response:
                    return response

                if locked_poll.voting_type == 'multiple_choice':

                    Vote.objects.create(
                        poll=locked_poll,
                        option=form.cleaned_data['option'],
                        user=user,
                        voter_token=token
                    )

                else:

                    RankedVote.objects.bulk_create([
                        RankedVote(
                            poll=locked_poll,
                            option=option,
                            user=user,
                            voter_token=token,
                            rank=int(form.cleaned_data[f'option_{option.id}'])
                        )
                        for option in locked_poll.options.all()
                    ])

        except IntegrityError:
            messages.info(request, 'You have already voted.')
            return redirect('polls:poll_detail', slug=poll.slug)

        if locked_poll.is_anonymous:
            throttle.record_vote(request, locked_poll)

        messages.success(request, 'Your vote has been submitted.')

        response = redirect('polls:poll_detail', slug=poll.slug)

        if poll.is_anonymous and set_cookie:
            response.set_cookie(
                ANONYMOUS_COOKIE_NAME,
                token,
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                secure=request.is_secure(),
                samesite='Lax'
            )

        return response
