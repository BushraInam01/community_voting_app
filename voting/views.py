import uuid

from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core import signing
from django.db import transaction, IntegrityError
from django.utils import timezone

from polls.models import Poll
from .models import Vote, RankedVote
from .forms import MultipleChoiceVoteForm, RankedVoteForm


ANONYMOUS_COOKIE_NAME = 'anonymous_voter_token'


def get_anonymous_token(request):

    token = request.COOKIES.get(ANONYMOUS_COOKIE_NAME)

    if token:
        try:
            signing.loads(
                token,
                salt='voting.anonymous.voter'
            )
            return token, False

        except signing.BadSignature:
            token = None

    token = signing.dumps(
        uuid.uuid4().hex,
        salt='voting.anonymous.voter'
    )

    return token, True


class PollVoteView(View):

    def get(self, request, slug):

        poll = get_object_or_404(Poll, slug=slug)

        if poll.is_expired or poll.is_frozen:
            messages.error(request, 'This poll is closed.')
            return redirect('polls:poll_detail', slug=poll.slug)

        if not poll.is_anonymous and not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if poll.is_anonymous:
            token, _ = get_anonymous_token(request)

            if (
                Vote.objects.filter(
                    poll=poll,
                    voter_token=token
                ).exists()
                or RankedVote.objects.filter(
                    poll=poll,
                    voter_token=token
                ).exists()
            ):
                messages.info(request, 'You have already voted.')
                return redirect('polls:poll_detail', slug=poll.slug)

        else:
            if (
                Vote.objects.filter(
                    poll=poll,
                    user=request.user
                ).exists()
                or RankedVote.objects.filter(
                    poll=poll,
                    user=request.user
                ).exists()
            ):
                messages.info(request, 'You have already voted.')
                return redirect('polls:poll_detail', slug=poll.slug)

        if poll.voting_type == 'ranked':
            form = RankedVoteForm(poll=poll)
        else:
            form = MultipleChoiceVoteForm(poll=poll)

        context = {
            'poll': poll,
            'form': form,
        }

        return render(request, 'voting/vote.html', context)

    def post(self, request, slug):

        poll = get_object_or_404(Poll, slug=slug)

        if poll.is_expired or poll.is_frozen:
            messages.error(request, 'This poll is closed.')
            return redirect('polls:poll_detail', slug=poll.slug)

        if not poll.is_anonymous and not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        token = None
        set_cookie = False

        if poll.is_anonymous:
            token, set_cookie = get_anonymous_token(request)

            if (
                Vote.objects.filter(
                    poll=poll,
                    voter_token=token
                ).exists()
                or RankedVote.objects.filter(
                    poll=poll,
                    voter_token=token
                ).exists()
            ):
                messages.info(request, 'You have already voted.')
                return redirect('polls:poll_detail', slug=poll.slug)

        else:
            if (
                Vote.objects.filter(
                    poll=poll,
                    user=request.user
                ).exists()
                or RankedVote.objects.filter(
                    poll=poll,
                    user=request.user
                ).exists()
            ):
                messages.info(request, 'You have already voted.')
                return redirect('polls:poll_detail', slug=poll.slug)

        if poll.voting_type == 'ranked':
            form = RankedVoteForm(request.POST, poll=poll)
        else:
            form = MultipleChoiceVoteForm(request.POST, poll=poll)

        if form.is_valid():

            try:
                with transaction.atomic():

                    locked_poll = Poll.objects.select_for_update().get(
                        pk=poll.pk
                    )

                    if locked_poll.is_frozen or timezone.now() >= locked_poll.expires_at:
                        messages.error(request, 'This poll is closed.')
                        return redirect(
                            'polls:poll_detail',
                            slug=poll.slug
                        )

                    if poll.is_anonymous:
                        already_voted = (
                            Vote.objects.filter(
                                poll=locked_poll,
                                voter_token=token
                            ).exists()
                            or RankedVote.objects.filter(
                                poll=locked_poll,
                                voter_token=token
                            ).exists()
                        )

                        voter_user = None

                    else:
                        already_voted = (
                            Vote.objects.filter(
                                poll=locked_poll,
                                user=request.user
                            ).exists()
                            or RankedVote.objects.filter(
                                poll=locked_poll,
                                user=request.user
                            ).exists()
                        )

                        voter_user = request.user

                    if already_voted:
                        messages.info(request, 'You have already voted.')
                        return redirect(
                            'polls:poll_detail',
                            slug=poll.slug
                        )

                    if locked_poll.voting_type == 'multiple_choice':

                        Vote.objects.create(
                            poll=locked_poll,
                            option=form.cleaned_data['option'],
                            user=voter_user,
                            voter_token=token
                        )

                    else:

                        options = locked_poll.options.all()

                        for option in options:
                            rank = int(
                                form.cleaned_data[f'option_{option.id}']
                            )

                            RankedVote.objects.create(
                                poll=locked_poll,
                                option=option,
                                user=voter_user,
                                voter_token=token,
                                rank=rank
                            )

            except IntegrityError:
                messages.info(request, 'You have already voted.')
                return redirect('polls:poll_detail', slug=poll.slug)

            messages.success(request, 'Your vote has been submitted.')

            response = redirect(
                'polls:poll_detail',
                slug=poll.slug
            )

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

        context = {
            'poll': poll,
            'form': form,
        }

        return render(request, 'voting/vote.html', context)
