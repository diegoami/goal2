"""[designed: owner#73, T122] Named deviations applied after validating the original input.

[confirmed: F027, archaeology53d7ef5; A5FB/A605/E544/C5F6] The original copies DS066B/C
to each side's remaining byte. Substitution gates test nonzero/unsigned-positive, and
every outgoing player becomes unavailable for re-entry. A twenty-player squad therefore
cannot exhaust255 legitimate substitutions. The original keeps all eligibility decisions.
"""

OWNER_SUBSTITUTIONS = 'owner-substitutions-v1'
ORIGINAL = (5, 2)
OWNER = (255, 5)
TABLE = 0x066B
SELECTOR = 0x9A3D
OWNER_RULE = 'Unlimited in friendlies; five in competitive matches'


def declarations(value):
    """Only this registered, versioned declaration is accepted; there is no byte-patch loader."""
    if not isinstance(value, list) or value not in ([], [OWNER_SUBSTITUTIONS]):
        raise ValueError('unknown or inconsistent guest patch declaration')
    return tuple(value)


def table(core):
    return tuple(core.m.rd(TABLE + i, 1) for i in range(2))


def validate(core):
    if core.patches not in ((), (OWNER_SUBSTITUTIONS,)):
        raise ValueError('unknown or inconsistent guest patch declaration')
    expected = OWNER if core.patches else ORIGINAL
    if table(core) != expected:
        raise ValueError(f'guest substitution table does not match its patch declaration: expected {expected}')


def apply(core, name):
    core._check_waiting()
    if name != OWNER_SUBSTITUTIONS:
        raise ValueError(f'unknown guest patch {name!r}')
    validate(core)
    if core.patches:
        return                         # validated idempotence never replenishes a spent counter
    if core.wait.kind != 'manager-menu':
        raise ValueError('activate the substitution patch at a manager menu before kickoff')
    for i, value in enumerate(OWNER):
        core.m.wr(TABLE + i, value, 1)
    core.patches = (name,)


def unlimited_friendly(core):
    return OWNER_SUBSTITUTIONS in core.patches and core.m.rd(SELECTOR, 1) == 0
