"""[designed: T46; derived: F007/F024/F027 at archaeology
0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb] Pure campaign CPU preparation.
The top-ability selector remains a stand-in for the original B11F setup.
"""
from goal2.ai.cpu import get_computer_tactics, pick_computer_eleven
from goal2.game.eligibility import available_words


def prepare(state,country):
    """[designed] Read current squad/condition/tactics without mutating state/RNG."""
    if type(country) is not int or not 1<=country<=128:
        raise ValueError('invalid opponent country')
    if country==state.managed_country:
        raise ValueError('computer preparation cannot replace the human side')
    record=state.countries[country]
    squad=[int.from_bytes(record[i:i+2],'little') for i in range(0,40,2)]
    if len(record)!=191 or len(set(squad))!=20 or any(not 1<=w<len(state.players) for w in squad):
        raise ValueError('opponent needs twenty distinct valid squad IDs')
    if any(len(state.players[w])!=20 or state.players[w][0]!=country for w in squad):
        raise ValueError('opponent squad contains a foreign or malformed player')
    eligible = available_words(state.players, squad)
    if len(eligible)<11:
        raise ValueError('opponent has fewer than eleven available players')
    eleven=pick_computer_eleven(state.players,eligible)
    return {'country':country,'eleven':tuple(eleven),
            'squad':tuple(eleven+[w for w in squad if w not in eleven]),
            'tactics':get_computer_tactics(record)}
