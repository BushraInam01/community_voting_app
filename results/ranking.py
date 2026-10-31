"""Instant-runoff (ranked-choice) tallying, kept free of Django so it is easy
to test.

Rules:
  * Each ballot counts for its highest-ranked option that is still in the race.
  * If an option has more than half of the active ballots, it wins.
  * Otherwise the option with the fewest votes is eliminated and ballots are
    recounted. Ties for last place are broken by fewest first-choice votes,
    then by option order (the earlier-listed option survives).
  * If every remaining option is tied, the result is a tie between them.
"""


def instant_runoff(ballots, option_ids):
    """Run an instant-runoff count.

    ballots: iterable of lists of option ids, most preferred first.
    option_ids: all option ids in the poll, in display order.

    Returns {'rounds': [...], 'winners': [option_id, ...], 'is_tie': bool}
    where each round is {'counts': {option_id: votes}, 'active': int,
    'eliminated': option_id or None}.
    """

    ballots = [list(ballot) for ballot in ballots]
    order = {option_id: index for index, option_id in enumerate(option_ids)}
    remaining = list(option_ids)

    rounds = []
    first_choice = None

    while remaining:
        counts = {option_id: 0 for option_id in remaining}
        active = 0

        for ballot in ballots:
            for option_id in ballot:
                if option_id in counts:
                    counts[option_id] += 1
                    active += 1
                    break

        if first_choice is None:
            first_choice = dict(counts)

        current = {'counts': counts, 'active': active, 'eliminated': None}
        rounds.append(current)

        if active == 0:
            return {'rounds': rounds, 'winners': [], 'is_tie': False}

        top = max(counts.values())

        if len(remaining) == 1 or top * 2 > active:
            winners = [o for o in remaining if counts[o] == top]
            return {'rounds': rounds, 'winners': winners, 'is_tie': False}

        if len(set(counts.values())) == 1:
            return {'rounds': rounds, 'winners': list(remaining), 'is_tie': True}

        eliminated = min(
            remaining,
            key=lambda o: (counts[o], first_choice.get(o, 0), -order[o])
        )

        current['eliminated'] = eliminated
        remaining.remove(eliminated)

    return {'rounds': rounds, 'winners': [], 'is_tie': False}
