from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.views import View

from polls.models import Poll
from voting.models import RankedVote

from .ranking import instant_runoff

POLLS_PER_PAGE = 20


def percent(part, whole):
    return round(part / whole * 100, 2) if whole else 0


class ResultsListView(View):

    def get(self, request):

        polls = Poll.objects.order_by('-created_at')

        page_obj = Paginator(polls, POLLS_PER_PAGE).get_page(
            request.GET.get('page')
        )

        context = {
            'polls': page_obj,
            'page_obj': page_obj,
        }

        return render(
            request,
            'results/results_list.html',
            context
        )


def multiple_choice_results(poll):
    """One query: each option annotated with its vote count."""

    options = poll.options.annotate(vote_count=Count('votes'))

    total_votes = sum(option.vote_count for option in options)

    results = [
        {
            'option': option,
            'vote_count': option.vote_count,
            'percentage': percent(option.vote_count, total_votes),
        }
        for option in options
    ]

    return results, total_votes, None


def ranked_results(poll):
    """First-choice counts plus an instant-runoff tally."""

    options = list(
        poll.options.annotate(
            first_choice_count=Count(
                'ranked_votes',
                filter=Q(ranked_votes__rank=1)
            )
        )
    )

    by_id = {option.id: option for option in options}

    # One query: group each voter's rows into an ordered ballot.
    ballots = {}

    rows = RankedVote.objects.filter(poll=poll).order_by('rank').values_list(
        'user_id', 'voter_token', 'option_id'
    )

    for user_id, voter_token, option_id in rows:
        ballots.setdefault((user_id, voter_token), []).append(option_id)

    total_votes = len(ballots)

    results = [
        {
            'option': option,
            'vote_count': option.first_choice_count,
            'percentage': percent(option.first_choice_count, total_votes),
        }
        for option in options
    ]

    runoff = instant_runoff(ballots.values(), [o.id for o in options])

    rounds = []

    for number, rnd in enumerate(runoff['rounds'], start=1):
        rounds.append({
            'number': number,
            'rows': [
                {
                    'option': by_id[option_id],
                    'votes': votes,
                    'percentage': percent(votes, rnd['active']),
                    'eliminated': option_id == rnd['eliminated'],
                }
                for option_id, votes in rnd['counts'].items()
            ],
        })

    ranked = {
        'rounds': rounds,
        'winners': [by_id[option_id] for option_id in runoff['winners']],
        'is_tie': runoff['is_tie'],
    }

    return results, total_votes, ranked


class PollResultsView(View):

    def get(self, request, slug):

        poll = get_object_or_404(
            Poll,
            slug=slug
        )

        if poll.voting_type == 'multiple_choice':
            results, total_votes, ranked = multiple_choice_results(poll)
        else:
            results, total_votes, ranked = ranked_results(poll)

        context = {
            'poll': poll,
            'results': results,
            'total_votes': total_votes,
            'ranked': ranked,
            'is_live': not poll.is_closed,
        }

        if request.htmx:

            # htmx treats HTTP 286 as "stop polling".
            status = 200 if context['is_live'] else 286

            return render(
                request,
                'results/partials/live_results.html',
                context,
                status=status
            )

        return render(
            request,
            'results/results.html',
            context
        )
