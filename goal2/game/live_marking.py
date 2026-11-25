"""[designed: T170as] The retained bench's live marking domain."""


def live_marking_targets(word, eleven, opponents, players, setup):
    """[confirmed: 1771:49B8/F010] Zone and available outfield opponents."""
    def available(player):
        record = players[player]
        return 0 < record[14] < 128 and not record[16] & 0xA4

    if not setup or not word or word not in eleven or not 2 <= players[word][6] < 14 or not available(word):
        return ()
    return (0, *(w for w in opponents[1:11] if w and available(w)))


def worker_marking_targets(match, word):
    from goal2.engine.original_match.image import Image
    from goal2.game import engine_tables

    data = match.waiting
    sides = data['team_context']['sides']
    opponent = sides[1 - sides.index(match.opts['managed'])]
    image = Image.from_state(match.records_after(), engine_tables.load())
    return live_marking_targets(word, data['eleven'], image.squad(opponent), image.players(),
                                data['team_context']['match_set_up'])
