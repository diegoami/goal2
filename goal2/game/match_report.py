"""[designed: T97; accepted vision #266 screen 08] The completed match as one report.

[confirmed: watched_schema RESULT_KEYS and board (accepted E033 Match._finish/_board)] A watched or
competitive result keeps the original's full-time board: ten statistics, the two raw bars, the
man of the match, the half-time score and the substitutions. A quick result keeps the score and
the goals only, so the rest is reported as not recorded, never invented. Names come from the
game's name table (`goaldat`), so renames (T92) and localized pools (T93) carry into the result.
"""
NOT_RECORDED = 'Not recorded'
# [confirmed: watched_schema board statistics; E033] The original's statistics, in its order.
STATISTICS = (('corners', 'Corners'), ('free_kicks', 'Free kicks'), ('penalties', 'Penalties'),
              ('shots', 'Shots'), ('on_target', 'On target'), ('saves', 'Saves'), ('fouls', 'Fouls'),
              ('bookings', 'Yellow cards'), ('red_cards', 'Red cards'), ('injuries', 'Injuries'))


def report(last_match, goaldat):
    """The report of `last_match` (a validated state.last_match), or None when no match was played."""
    if last_match is None:
        return None
    from goal2.game.watched_schema import watched, COMPETITIVE_SCHEMA, resolution
    names, countries = goaldat.player_names, goaldat.country_names
    teams = last_match['teams'];score = list(last_match['score'])
    original = last_match.get('original') if watched(last_match) else None
    competitive = original is not None and last_match.get('schema') == COMPETITIVE_SCHEMA
    scorers = ([], [])
    for goal in last_match['goals']:
        scorers[goal['team']].append((names[goal['player']], goal['minute']))
    value = {'teams': [countries[t] for t in teams], 'score': score, 'scorers': scorers,
             'kind': 'Competitive' if competitive else 'Friendly',
             'engine': 'Original engine' if original is not None else 'Quick simulation (rebuild setup)',
             'half_time': None, 'statistics': None, 'bars': None, 'man_of_the_match': None,
             'substitutions': [], 'stages': None}
    if original is not None:
        board = original['board']
        value['half_time'] = list(original['half_time_score'])
        value['statistics'] = [(label, list(board['statistics'][key])) for key, label in STATISTICS]
        # [designed: accepted screen 08] Possession/territory bars: raw values, meaning unverified.
        value['bars'] = [list(bar) for bar in board['bars']]
        word = original['man_of_the_match']
        value['man_of_the_match'] = names[word] if 0 < word < len(names) else original['man_of_the_match_name']
        value['substitutions'] = [(row['team'], names[row['off']], names[row['on']], row['minute'])
                                  for row in original['substitutions']]
        if competitive:
            value['stages'] = resolution(original)
    return value


def lines(value):
    """Plain text of a report, for the Country desk's last-match panel and assistive names."""
    if value is None:
        return ['No match played']
    a, b = value['teams']
    out = [f"{a} {value['score'][0]} - {value['score'][1]} {b}"]
    for side, team in ((0, a), (1, b)):
        if value['scorers'][side]:
            out.append(f'{team}: ' + ' / '.join(f'{n} {m}′' for n, m in value['scorers'][side]))
    out.append('Half time ' + (f"{value['half_time'][0]}-{value['half_time'][1]}" if value['half_time'] else NOT_RECORDED))
    for team, off, on, minute in value['substitutions']:
        out.append(f'{off} > {on} {minute}′')
    return out
