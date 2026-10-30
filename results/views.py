
from django.views import View
from django.shortcuts import render, get_object_or_404

from polls.models import Poll
from voting.models import Vote, RankedVote


class ResultsListView(View):

    def get(self, request):

        polls = Poll.objects.all().order_by('-created_at')

        context = {
            'polls': polls,
        }

        return render(
            request,
            'results/results_list.html',
            context
        )


class PollResultsView(View):

    def get(self, request, slug):

        poll = get_object_or_404(
            Poll,
            slug=slug
        )

        if poll.voting_type == 'multiple_choice':

            options = poll.options.all()

            total_votes = Vote.objects.filter(
                poll=poll
            ).count()

            results = []

            for option in options:

                vote_count = Vote.objects.filter(
                    poll=poll,
                    option=option
                ).count()

                percentage = 0

                if total_votes > 0:
                    percentage = (vote_count / total_votes) * 100

                results.append({
                    'option': option,
                    'vote_count': vote_count,
                    'percentage': round(percentage, 2)
                })

        else:

            options = poll.options.all()

            total_votes = RankedVote.objects.filter(
                poll=poll
            ).values(
                'user', 'voter_token'
            ).distinct().count()

            results = []

            for option in options:

                vote_count = RankedVote.objects.filter(
                    poll=poll,
                    option=option,
                    rank=1
                ).count()

                percentage = 0

                if total_votes > 0:
                    percentage = (vote_count / total_votes) * 100

                results.append({
                    'option': option,
                    'vote_count': vote_count,
                    'percentage': round(percentage, 2)
                })

        context = {
            'poll': poll,
            'results': results,
            'total_votes': total_votes,
            'is_live': not poll.is_expired and not poll.is_frozen,
        }

        if request.htmx:

            if not context['is_live']:
                return render(
                    request,
                    'results/partials/live_results.html',
                    context,
                    status=286
                )

            return render(
                request,
                'results/partials/live_results.html',
                context
            )

        return render(
            request,
            'results/results.html',
            context
        )
