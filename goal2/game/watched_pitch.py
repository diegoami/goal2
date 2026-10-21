"""[designed: T82] Versioned read-only completed-tick presentation samples.

[confirmed: F013/F018/F028, kit424d599; docs/evidence/T81/README.md]
Coordinates remain signed (x transverse, y longitudinal); fixed screen=[y,x].
Slot labels are local ordinals, current player words may rebind each tick.
"""
import json
import struct

VERSION = 2
# [designed: T96] Version 2 adds the officials and the player on the ball; version 1 stays valid.
VERSIONS = (1, 2)
# [confirmed: static 0791:9119 move_referee, 0791:8E24 track_offside_line, 0791:8537 (T96
# research)] The referee's sprite record (row = signed x +0, column = signed y +1), the two
# linesmen's at DS:82E2 + 6 * side, and the pitch slot on the ball, DS:830B.
REFEREE, LINESMEN, HOLDER = 0x82EE, (0x82E2, 0x82E8), 0x830B
MAX_FRAME_PACKET = 4096
MAX_FRAME_BYTES = 16 * 1024 * 1024
MAX_FRAMES = 8192
FRAME_READ_BUDGET = 65536
FRAME_POLL_BUDGET = 32


def signed(value):
    return value - 256 if value > 127 else value


def snapshot(match, event, sequence, watermark):
    """[derived: T81] Only invoke at tick stops, before guest resumes; no full Memory copy."""
    from goal2.engine.original_match.match import PITCH, PITCH_SIZE, BALL
    m = match.m
    sentinel = m.rd(0x0640)
    players = []
    for slot in range(1, 23):
        raw = m.read(m.DS * 16 + PITCH + PITCH_SIZE * slot, PITCH_SIZE)
        team, number = (1, slot) if slot <= 11 else (0, slot - 11)
        word = int.from_bytes(raw[13:15], 'little')
        # [derived: T81] Current guest identity, including substitutions, not initial XI.
        if raw[6] != slot or word != match._squad(match.opts['first' if team == 0 else 'second'])[number-1]:
            raise ValueError('pitch current slot identity differs')
        players.append([slot, team, number, word, signed(raw[0]), signed(raw[1]), raw[18],
                        int.from_bytes(raw[:2], 'little') == sentinel])
    raw = m.read(m.DS * 16 + BALL, 2)
    threshold, remaining = m.rd(0x8319, 1), m.rd(0x831B)
    selector = int(signed(threshold) < remaining)
    table = [signed(v) for v in m.read(m.DS * 16 + 0x7920, 2)]
    def official(address):
        raw = m.read(m.DS * 16 + address, 2)
        return [signed(raw[0]), signed(raw[1])]
    referee = official(REFEREE)
    officials = {'referee': referee + [((referee[0] & 255) | ((referee[1] & 255) << 8)) == sentinel],
                 'linesmen': [official(a) for a in LINESMEN], 'holder': m.rd(HOLDER, 1)}
    return dict(version=VERSION, sequence=sequence, watermark=watermark, minute=event.minute, officials=officials,
                score=list(event.score), subtick=m.rd(0x831D), threshold=threshold,
                remaining=remaining, selector=selector,
                attack=[table[selector], table[1 ^ selector]], sentinel=sentinel,
                ball=[signed(raw[0]), signed(raw[1]), int.from_bytes(raw, 'little') == sentinel],
                players=players)


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate(value, sequence, previous_watermark):
    """[designed] Strict v1 shape; retain out-of-field signed coordinates and raw state."""
    keys = {'version','sequence','watermark','minute','score','subtick','threshold','remaining',
            'selector','attack','sentinel','ball','players'}
    if isinstance(value, dict) and value.get('version') == 2 and type(value['version']) is int:
        keys = keys | {'officials'}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('invalid pitch frame schema')
    if (type(value['version']) is not int or value['version'] not in VERSIONS
            or not integer(value['sequence'], 0, MAX_FRAMES-1) or value['sequence'] != sequence
            or not integer(value['watermark'], previous_watermark, 2**31-1)):
        raise ValueError('invalid pitch frame order/watermark')
    for key, high in [('minute',65535),('subtick',65535),('threshold',255),('remaining',65535),
                       ('selector',1),('sentinel',65535)]:
        if not integer(value[key],0,high):
            raise ValueError('invalid pitch frame schema')
    if value['selector'] != int(signed(value['threshold']) < value['remaining']):
        raise ValueError('invalid pitch frame selector')
    for key, low, high in [('score',0,65535),('attack',-128,127)]:
        if type(value[key]) is not list or len(value[key]) != 2 or not all(integer(x,low,high) for x in value[key]):
            raise ValueError('invalid pitch frame schema')
    def pose(x, y, hidden):
        return (integer(x,-128,127) and integer(y,-128,127) and type(hidden) is bool
                and hidden == (((x & 255) | ((y & 255) << 8)) == value['sentinel']))
    ball = value['ball']
    if type(ball) is not list or len(ball) != 3 or not pose(*ball):
        raise ValueError('invalid pitch frame ball')
    if 'officials' in value:
        officials = value['officials']
        if (not isinstance(officials, dict) or set(officials) != {'referee', 'linesmen', 'holder'}
                or type(officials['referee']) is not list or len(officials['referee']) != 3
                or not pose(*officials['referee']) or not integer(officials['holder'], 0, 255)
                or type(officials['linesmen']) is not list or len(officials['linesmen']) != 2
                or any(type(l) is not list or len(l) != 2 or not all(integer(v, -128, 127) for v in l)
                       for l in officials['linesmen'])):
            raise ValueError('invalid pitch frame officials')
    players = value['players']
    if type(players) is not list or len(players) != 22:
        raise ValueError('invalid pitch frame players')
    for slot, p in enumerate(players,1):
        if (type(p) is not list or len(p) != 8 or any(type(x) is not int for x in p[:7])
                or p[:3] != [slot, int(slot <= 11), slot if slot <= 11 else slot-11]
                or not integer(p[3],1,3060) or not integer(p[6],0,255) or not pose(p[4],p[5],p[7])):
            raise ValueError('invalid pitch frame player')
    return value


def write_frame(stream, token, frame):
    """[designed] Finite lossless journal; overflow aborts instead of dropping poses."""
    packet = json.dumps([token, frame], separators=(',', ':'), allow_nan=False).encode()
    if len(packet) > MAX_FRAME_PACKET or stream.tell() + 4 + len(packet) > MAX_FRAME_BYTES or frame['sequence'] >= MAX_FRAMES:
        raise ValueError('pitch frame budget exceeded; presentation consumer too slow')
    stream.write(struct.pack('!I',len(packet)) + packet)
    stream.flush()
