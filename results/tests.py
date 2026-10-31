from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from config.testing import make_poll, make_user
from voting.models import RankedVote, Vote
from .ranking import instant_runoff


class InstantRunoffTests(TestCase):
    # Option ids: 1 = A, 2 = B, 3 = C

    def test_first_round_majority_wins(self):
        result = instant_runoff(
            [[1, 2, 3], [1, 3, 2], [1, 2, 3], [2, 1, 3], [3, 1, 2]],
            [1, 2, 3],
        )

        self.assertEqual(result['winners'], [1])
        self.assertEqual(len(result['rounds']), 1)
        self.assertFalse(result['is_tie'])

    def test_votes_transfer_after_elimination(self):
        # First choices: A=2, B=2, C=1 -> C is eliminated, its ballot goes to B.
        result = instant_runoff(
            [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 2, 1]],
            [1, 2, 3],
        )

        self.assertEqual(result['winners'], [2])
        self.assertEqual(result['rounds'][0]['eliminated'], 3)
        self.assertEqual(result['rounds'][1]['counts'], {1: 2, 2: 3})

    def test_exact_tie_between_remaining_options(self):
        result = instant_runoff([[1, 2], [2, 1]], [1, 2])

        self.assertTrue(result['is_tie'])
        self.assertEqual(sorted(result['winners']), [1, 2])

    def test_last_place_tie_eliminates_latest_listed_option(self):
        # Round 1: A=2, B=C=D=1. B, C and D tie for last place with the same
        # first-choice votes, so the latest-listed option (D, id 4) goes out.
        result = instant_runoff([[1, 2, 3], [1, 3, 2], [2, 1, 3], [3, 1, 2], [4, 1, 2]], [1, 2, 3, 4])

        self.assertEqual(result['rounds'][0]['eliminated'], 4)

    def test_no_ballots(self):
        result = instant_runoff([], [1, 2])

        self.assertEqual(result['winners'], [])
        self.assertFalse(result['is_tie'])

    def test_single_option(self):
        self.assertEqual(instant_runoff([[1]], [1])['winners'], [1])


class ResultsViewTests(TestCase):

    def setUp(self):
        self.owner = make_user('owner')

    def test_multiple_choice_counts_and_percentages(self):
        poll = make_poll(self.owner, options=('A', 'B'))
        a, b = poll.options.all()
        for i, option in enumerate([a, a, a, b]):
            Vote.objects.create(
                poll=poll, option=option, voter_token=f'token-{i}'
            )

        response = self.client.get(reverse('results:poll_results', args=[poll.slug]))

        self.assertEqual(response.context['total_votes'], 4)
        counts = {
            r['option'].option_text: (r['vote_count'], r['percentage'])
            for r in response.context['results']
        }
        self.assertEqual(counts, {'A': (3, 75.0), 'B': (1, 25.0)})

    def test_results_query_count_does_not_grow_with_options(self):
        poll = make_poll(self.owner, options=tuple('ABCDEFGH'))
        url = reverse('results:poll_results', args=[poll.slug])

        with self.assertNumQueries(2):  # the poll, then all options with counts
            self.client.get(url)

    def test_ranked_results_show_runoff_winner(self):
        poll = make_poll(
            self.owner, voting_type='ranked', options=('A', 'B', 'C')
        )
        a, b, c = poll.options.all()
        ballots = [
            (a, b, c), (a, c, b),      # A first
            (b, a, c), (b, c, a),      # B first
            (c, b, a),                 # C first -> eliminated, goes to B
        ]
        for i, order in enumerate(ballots):
            for rank, option in enumerate(order, start=1):
                RankedVote.objects.create(
                    poll=poll, option=option,
                    voter_token=f'token-{i}', rank=rank
                )

        response = self.client.get(reverse('results:poll_results', args=[poll.slug]))

        self.assertEqual(response.context['total_votes'], 5)
        ranked = response.context['ranked']
        self.assertEqual([o.option_text for o in ranked['winners']], ['B'])
        self.assertContains(response, 'Instant-runoff result')
        self.assertContains(response, 'First-choice votes')

    def test_htmx_polling_continues_while_open_and_stops_when_closed(self):
        open_poll = make_poll(self.owner, question='Open poll')
        closed_poll = make_poll(
            self.owner, question='Closed poll', expires_in=-timedelta(hours=1)
        )

        live = self.client.get(
            reverse('results:poll_results', args=[open_poll.slug]),
            HTTP_HX_REQUEST='true',
        )
        done = self.client.get(
            reverse('results:poll_results', args=[closed_poll.slug]),
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(live.status_code, 200)
        self.assertEqual(done.status_code, 286)

    def test_results_page_loads_htmx_from_own_origin(self):
        poll = make_poll(self.owner)

        response = self.client.get(reverse('results:poll_results', args=[poll.slug]))

        self.assertContains(response, '/static/js/htmx.min.js')
        self.assertNotContains(response, 'unpkg.com')

    def test_results_list_is_paginated(self):
        for i in range(21):
            make_poll(self.owner, question=f'Poll {i}')

        response = self.client.get(reverse('results:results_list') + '?page=2')

        self.assertEqual(len(response.context['polls']), 1)
