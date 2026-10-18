"""[designed: T66] Explicit-data, bounded presentation protocol; no game ownership."""
import copy
import hashlib
import json

MAX_PACKET = 256 * 1024
MAX_JOURNAL = 16 * 1024 * 1024


def raw_rating(record):
    """[confirmed: F014/E012 §1 at424d5998076da1e4efc399c2715689ddb44d3e1a] Original word +12h."""
    word = int.from_bytes(record[18:20], 'little')
    if word == 0x7fff:
        return None
    value = word if word < 32768 else word - 65536
    return value - 10000 if value > 5000 else value


def completion(outcome, names):
    """[derived: F014 at424d5998076da1e4efc399c2715689ddb44d3e1a] Read actual returned words, never predict."""
    from goal2.engine.original_match import Image
    image = Image.from_memory_component(outcome.memory)
    players = image.players()
    result = outcome.result
    ratings = [[{'player': w, 'name': names[w], 'word': int.from_bytes(players[w][18:20], 'little'),
                 'raw': raw_rating(players[w])} for w in image.squad(country)]
               for country in (result['first'], result['second'])]
    return {'board': copy.deepcopy(result['board']), 'ratings': ratings,
            'man_of_the_match': result['man_of_the_match_name']}


class Display:
    """[designed] Strict append-only display stream, detached from active game data."""
    def __init__(self, token):
        self.token = token
        self.sequence = 0
        self.countries = None
        self.events = []
        self.result = None
        self._digest = hashlib.sha256(b'goal2 presentation v1').hexdigest()

    def accept(self, packet):
        if (not isinstance(packet, list) or len(packet) != 4 or packet[0] != self.token
                or type(packet[1]) is not int or packet[1] != self.sequence):
            raise ValueError('stale or out-of-order viewer packet')
        _, _, kind, value = packet
        if kind == 'start' and self.sequence == 0:
            if not isinstance(value, list) or len(value) != 2 or any(not isinstance(v, str) for v in value):
                raise ValueError('invalid viewer countries')
            self.countries = copy.deepcopy(value)
        elif kind == 'event' and self.countries is not None and self.result is None:
            if (not isinstance(value, dict) or set(value) != {'kind','minute','score','data'}
                    or not isinstance(value['kind'], str) or type(value['minute']) is not int
                    or not isinstance(value['score'], list) or len(value['score']) != 2
                    or any(type(v) is not int or v < 0 for v in value['score'])
                    or not isinstance(value['data'], dict)):
                raise ValueError('invalid viewer event')
            self.events.append(copy.deepcopy(value))
        elif kind == 'complete' and self.events and self.events[-1]['kind'] == 'end' and self.result is None:
            if not isinstance(value, dict) or set(value) != {'board','ratings','man_of_the_match'}:
                raise ValueError('invalid viewer completion')
            self.result = copy.deepcopy(value)
        else:
            raise ValueError('invalid viewer transition')
        self._digest = hashlib.sha256((self._digest + json.dumps(packet,sort_keys=True)).encode()).hexdigest()
        self.sequence += 1

    def lines(self):
        lines = ['Original engine — friendly', ' — '.join(self.countries or ['Starting…'])]
        if self.events:
            last = self.events[-1]
            lines.append(f"{last['minute']} min   {last['score'][0]} — {last['score'][1]}")
        else:
            lines.append('Waiting for original engine…')
        for event in self.events:
            if event['kind'] == 'commentary':
                lines.append(f"{event['minute']} min {event['data'].get('text', '')}")
        if self.result:
            lines += ['Original full-time board', f"Man of the match: {self.result['man_of_the_match']}"]
            for name, values in self.result['board']['statistics'].items():
                lines.append(f'{name}: {values[0]} — {values[1]}')
            lines.append(f"Original bars: {self.result['board']['bars']}")
            for country, rows in zip(self.countries, self.result['ratings']):
                lines.append(f'{country} — Raw rating')
                lines.extend(f"{row['name']}: {'blank' if row['raw'] is None else row['raw']}" for row in rows)
        return lines

    def digest(self):
        return self._digest
