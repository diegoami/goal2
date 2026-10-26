"""T93/F034: manager record to original text cells (1771:0947, 214B:026D/00FF).

The host rejects malformed record widths/lengths; the original Pascal runtime
trusts them. This validation is a consumer boundary, not original error behavior.
"""

_LOW = '☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼'


def screen_text(payload: bytes) -> str:
    """Decode VGA text cells: NUL is blank; low bytes/DEL are font glyphs.

    No stripping, C-string termination, replacement or transliteration occurs.
    Unicode names the standard IBM PC glyphs; font appearance can vary.
    """
    return ''.join(' ' if b == 0 else _LOW[b-1] if b < 32 else '⌂' if b == 127
                   else bytes([b]).decode('cp437') for b in payload)


def manager_payload(initial: int, surname_record: bytes) -> bytes:
    """Format one 13-byte manager record, preserving its Pascal length exactly.

    F002 R005: one length byte and twelve payload bytes. 1771:0947 uses
    one initial (even zero), CS:0945's space, then the declared surname, and
    23E4:0644 stores at most fourteen bytes. Padding is never part of the name.
    """
    if type(initial) is not int or not 0 <= initial <= 255:
        raise ValueError('initial must be a byte')
    if len(surname_record) != 13 or surname_record[0] > 12:
        raise ValueError('manager surname must be a 13-byte record with length <=12')
    return (bytes([initial]) + b' ' + surname_record[1:1+surname_record[0]])[:14]


def manager_text(initial: int, surname_record: bytes) -> str:
    """The original display's text, including any leading/trailing blank cells."""
    return screen_text(manager_payload(initial, surname_record))
