"""[designed: T63] Pure synchronous adapter; publication and workers belong to T64/T65.
[confirmed: archaeology 3656a2d26e0f57a410d648edeaa6cd9eb7d1f607, E033/F025]
The accepted original engine owns events, setup reseeding and post-match updates.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from goal2.engine.original_match import Image, Fixture, Match
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.game.state import GameState, to_savestate, CLOCK_OFFSET

if TYPE_CHECKING:
    from goal2.game.campaign import CampaignState
    from goal2.engine.original_match.match import Event


# [confirmed: F023 §1; 1771:038C at the accepted source pin] The allocated
# fixture block is 0x4B48 bytes: 2400 regular rows, eight aggregates and a sentinel.
REGULAR_FIXTURES = 2400
FIXTURE_STORAGE_BYTES = 0x4B48


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in {low}..{high}')


def engine_year(campaign: CampaignState) -> int:
    """[derived: accepted F025 §2–3] Two rises per cycle, relative to the initial stage.

    New games start at word 0 in stage 2 (base year 0 mod 4) or stage 5
    (2 mod 4). Later entries to stages 2 and 5 increment the 16-bit word.
    This is independent of the rebuild's four ordinal playing-year labels.
    """
    from goal2.game.campaign import opening_calendar
    opening_calendar(campaign.start_year)
    _integer(campaign.cycle, 1, 2**31-1, 'cycle')
    _integer(campaign.stage, 2, 8, 'stage')
    word = 2 * (campaign.cycle - 1) + int(campaign.stage >= 5) - int(campaign.start_year % 4 == 2)
    if word < 0:
        raise ValueError('campaign position precedes its initial stage')
    return word & 0xFFFF


def prepare_watched(state: GameState, original: bytes, fixture: Fixture) -> Image:
    """[designed: T63] Preserve the public friendly-only preparation contract."""
    return _prepare_match(state,original,fixture,competitive=False)


def _prepare_match(state: GameState, original: bytes, fixture: Fixture, *, competitive: bool) -> Image:
    """[designed] Validate and serialize a private candidate with exact source endpoints/index.

    [confirmed: E033 Image/Match] Calendar order does not assign a home side.
    [designed] Campaign rows use T41a's original:<number> identity; legacy
    rows lacking a source index are refused rather than assigned a new one.
    """
    if not isinstance(fixture, Fixture):
        raise ValueError('a source Fixture is required')
    for value, name in ((fixture.first,'first country'),(fixture.second,'second country'),
                        (state.managed_country,'managed country')):
        _integer(value,1,128,name)
    from goal2.engine.original_match.match import KINDS
    kinds=tuple(k for k in KINDS if k!=1) if competitive else (1,)
    if type(fixture.kind) is not int or fixture.kind not in kinds or fixture.first == fixture.second:
        raise ValueError('two distinct countries and a supported fixture kind are required')
    if state.managed_country not in (fixture.first, fixture.second):
        raise ValueError('managed country must be a fixture endpoint')
    template = Image.from_memory_component(state.mem)
    _integer(fixture.index,1,REGULAR_FIXTURES,'original regular fixture index')
    if (template.far(0xA92B)+FIXTURE_STORAGE_BYTES > MEM_SIZE
            or template.rd(0xA92B)+FIXTURE_STORAGE_BYTES > 65536):
        raise ValueError('fixture storage lies outside the accepted guest allocation')
    next_free = template.rd_far(0xA923,0x28)
    if len(state.players) != 3061 or any(len(p) != 20 for p in state.players):
        raise ValueError('players must contain 3061 records of 20 bytes')
    if len(state.countries) != 129 or any(len(c) != 0xBF for c in state.countries):
        raise ValueError('countries must contain 129 records of 191 bytes')
    for words, size, name in ((state.managed_squad,20,'squad'),(state.starting_eleven,11,'eleven')):
        if len(words) != size:
            raise ValueError(f'{name} needs {size} player words')
        for word in words:
            _integer(word,1,3060,f'{name} player')
        if len(set(words)) != size:
            raise ValueError(f'{name} must contain distinct players')
    if not set(state.starting_eleven) <= set(state.managed_squad):
        raise ValueError('eleven must belong to the managed squad')
    _integer(state.captain,0,3060,'captain')
    if state.captain and state.captain not in state.starting_eleven:
        raise ValueError('captain must belong to the eleven')
    _integer(state.country_tactics,0,255,'tactics')
    for seed in (state.rng_seed_7b62,state.rng_seed_8336):
        _integer(seed,0,65535,'RNG seed')
    campaign = copy.deepcopy(state.campaign)
    if campaign is not None:
        campaign.__post_init__()
        class_low,class_high=(1,1360) if campaign.stage<5 else (1361,2400)
        _integer(fixture.index,class_low,class_high,'source class fixture index')
        pending = campaign.next_fixture
        if (pending is None or (pending.cycle,pending.stage) != (campaign.cycle,campaign.stage)
                or (pending.side_a,pending.side_b,pending.kind) != (fixture.first,fixture.second,fixture.kind)
                or pending.fixture_id != f'original:{fixture.index}'):
            raise ValueError('source fixture differs from the pending scheduled fixture')
        _integer(campaign.start_year,1,65535,'source base year')
        if campaign.world is not None:
            # [confirmed: F023 §1] +28 is next free, including the class's source start.
            numbers=[]
            for row in campaign.world.fixtures:
                try:number=int(row.fixture_id.removeprefix('original:'))
                except ValueError as exc:raise ValueError('source world fixture IDs must be original:<number>') from exc
                if row.fixture_id != f'original:{number}':
                    raise ValueError('source world fixture IDs must be canonical original:<number>')
                _integer(number,1,REGULAR_FIXTURES,'original regular fixture index')
                low,high=(1,1360) if campaign.stage<5 else (1361,2400)
                _integer(number,low,high,'source class fixture index')
                numbers.append(number)
            if numbers != list(range(numbers[0],numbers[-1]+1)):
                raise ValueError('a complete source-ordered calendar is required')
            next_free=numbers[-1]+1
    _integer(next_free,2,REGULAR_FIXTURES+1,'declared next-free fixture')
    if campaign is not None:
        _integer(next_free,class_low+1,class_high+1,'source class next-free fixture')
    _integer(fixture.index,1,next_free-1,'source fixture index')
    candidate = copy.deepcopy(state)
    # [derived: F029] XI is squad order; retain every bench word when moving a starter.
    candidate.managed_squad = list(state.starting_eleven) + [
        w for w in state.managed_squad if w not in state.starting_eleven]
    # [confirmed: T62 build guard] DS:0E6C is immutable foot-table data, not a clock.
    candidate.match_state['clock'] = template.rd(CLOCK_OFFSET)
    # [designed] +2F was a legacy UI placeholder. Preserve its opaque byte;
    # the actual original captain is supplied via Match's declared captain input.
    candidate.captain = state.countries[state.managed_country][0x2F]
    image = Image.from_savestate(to_savestate(candidate, original))
    if campaign is not None:
        # [confirmed: F023 §1–2/F025 §2–3] Known source calendar fields;
        # never inherit a stage-2 template's count/base/class into a stage-5 start.
        game=image.far(0xA923)
        image.memory[game+0x28:game+0x2A]=next_free.to_bytes(2,'little')
        image.memory[game+0x38:game+0x3A]=engine_year(campaign).to_bytes(2,'little')
        image.memory[game+0x3A:game+0x3C]=campaign.start_year.to_bytes(2,'little')
        image.memory[game+0x3C]=campaign.stage
        image.memory[game+0x40]=int(campaign.stage>=5)
    return image


@dataclass(frozen=True)
class WatchedOutcome:
    """[designed] Completed original output; caller decides when/how to publish it."""
    result: dict
    memory: bytes
    events: tuple[Event, ...]
    seeds: tuple[int,int]
    engine_year: int


def run_watched_match(state: GameState, original: bytes, fixture: Fixture, *,
                      reference_seed: int | None = None, delay_byte: int | None = None,
                      record_draws: bool = False) -> WatchedOutcome:
    """[designed: T63/T65] Complete the original with default play-on answers.

    Reference overrides are explicit diagnostics; normal play keeps setup's
    fixture-index * (engine-year + 1) reseed. No live-state mutation or Python
    energy/form update occurs. Events here are a completed diagnostic transcript;
    a future worker must stream directly from Match.events(), never replay this.
    """
    image=prepare_watched(state,original,fixture)
    return _drive_match(state,image,fixture,reference_seed=reference_seed,delay_byte=delay_byte,
                        record_draws=record_draws)


# [confirmed: vendored kit goal2/engine/original_match/match.py MENU_CONTEXT/DECIDED_AT_MENU] The
# decisions where the original offers the managed side its bench: the half-time menu (0791:9AE3),
# Enter in play (0791:945B) and the stoppage notice (0791:8103).
BENCH_CONTEXTS = ('half_time', 'pause', 'substitution')
# [confirmed: goal2-archaeology F027 C-DISC-24 (E544), E015-r0013 state 790] With no substitutions
# left the original's players screen shows this panel and makes no swap.
NO_MORE_SUBSTITUTES = 'no more substitutes'
# [confirmed: the kit's Match._close_plan and _flush] The events one menu visit ends with; the first
# other event (a tick, a decision, commentary) means the original plays on.
MENU_OUTCOMES = ('substitution', 'refused', 'substitution_requested', 'tactics', 'position', 'player_tactics')
# [designed: T102] The reason of an inferred refusal (_report) with substitutions still left: the
# original showed nothing goal2 can quote.
NOT_MADE = 'not made by the original'


def _drive_match(state,image,fixture,*,reference_seed=None,delay_byte=None,record_draws=False,
                 substitutions=None,quick_at_half_time=False,_observe=None,_observe_pitch=None,policy=None):
    """[designed: T51] Shared completed-original driver; no publication or Python tail.

    [designed: T102] `policy` answers the bench decisions (BENCH_CONTEXTS) for a watching player;
    without one every decision keeps the play-on default. It has three methods:
    `decide(event)` returns the (off, on) pairs to answer (empty plays on); `pause_now(sequence)`,
    asked after each observed pitch sample, returns True for the original's Enter in play
    (Match.pause), and `pause_dropped(sequence)` hears when the original could not take that Enter
    (#316); `answered(report)` receives what the engine made of each answer with pairs
    (`made`, `refused` with the reason, `requested` at a pause, and the engine's
    `substitutions_left`) once the original plays on. Answering is the only way it touches the match.
    [confirmed: the kit's Match._on_notice] An empty answer at a `substitution` stoppage that carries
    `requested` pairs still makes them (the default is what was asked for); its report has those
    pairs as `asked`, as if they had been answered (#316).
    """
    if reference_seed is not None:
        _integer(reference_seed,0,65535,'reference seed')
    if delay_byte is not None:
        _integer(delay_byte,0,255,'delay byte')
    match = Match(image,fixture,managed=state.managed_country,captain=state.captain or None,
                  seed=reference_seed,delay_byte=delay_byte,record_draws=record_draws,substitutions=substitutions)
    if _observe_pitch is not None:
        match.opts['ticks'] = True
    frame_sequence = 0
    events = []
    previous_decision = None
    report = None
    for ev in match.events():
        if report is not None and ev.kind not in MENU_OUTCOMES:
            policy.answered(_report(match, report))
            report = None
        if _observe_pitch is not None and ev.kind == 'tick':
            from goal2.game.watched_pitch import snapshot
            _observe_pitch(snapshot(match, ev, frame_sequence, len(events)))
            frame_sequence += 1
            if policy is not None and policy.pause_now(frame_sequence - 1) and not _pause(match):
                policy.pause_dropped(frame_sequence - 1)
            continue
        events.append(copy.deepcopy(ev))
        if _observe is not None:
            _observe(copy.deepcopy(ev))
        if report is not None:
            if ev.kind == 'substitution' and ev.data.get('team') == match.side:
                report['made'].append([ev.data['off'], ev.data['on']])
            elif ev.kind == 'refused' and ev.data.get('job') == 'sub':
                report['reasons'][(ev.data['player'], ev.data['target'])] = ev.data.get('reason')
            elif ev.kind == 'substitution_requested':
                report['requested'] = [list(pair) for pair in ev.data['pending']]
        if ev.kind == 'decision':
            # [designed: T65] Unknown contexts cannot be silently defaulted.
            if ev.data.get('context') not in ('half_time','substitution','pause','extra_time','shootout_order'):
                raise RuntimeError('unsupported original decision under default play-on policy')
            if policy is not None and ev.data['context'] in BENCH_CONTEXTS:
                # [designed: T102] The watching player answers; a refused eleven is offered again.
                pairs = [[int(off), int(on)] for off, on in policy.decide(copy.deepcopy(ev))]
                if pairs:
                    match.answer(substitutions=pairs)
                else:
                    match.answer()
                    if ev.data['context'] == 'substitution':
                        # The engine's default makes the requested pairs; they are reported as asked.
                        pairs = [[int(off), int(on)] for off, on in ev.data.get('requested') or []]
                if pairs:
                    report = {'context': ev.data['context'], 'asked': pairs, 'made': [], 'reasons': {},
                              'requested': []}
                previous_decision = None
                continue
            identity = (ev.minute,ev.data)
            if ev.data.get('refused') or identity == previous_decision:
                raise RuntimeError('original decision refused or made no progress under default play-on policy')
            previous_decision = copy.deepcopy(identity)
            match.answer(quick=True) if quick_at_half_time and ev.data.get('context')=='half_time' else match.answer()
        elif ev.kind != 'refused':
            previous_decision = None
    if report is not None:
        policy.answered(_report(match, report))
    # [confirmed: E033] result() requires completion after the B7FA player-update tail.
    result = copy.deepcopy(match.result())
    memory = match.memory_component()
    after = Image(memory)
    return WatchedOutcome(result,memory,tuple(events),(after.rd(0x7B62),after.rd(0x8336)),image.year())


def _pause(match):
    """[designed: T102] The original's Enter in play; asked when the match has no poll left (the
    final whistle, a waiting decision, the kit's shoot-out) it is dropped, as a key pressed then
    would be. Returns whether it was taken [designed: #316]."""
    from goal2.engine.original_match.match import MatchError
    try:
        match.pause()
    except MatchError:
        return False
    return True


def _report(match, report):
    """[designed: T102] What the engine made of one answer.
    [derived: the kit emits a `substitution` event for each swap made and a `refused` event for a
    job it gives up with a reason; at 0 substitutions left its plan presses no Enter for the swap
    (goal2/engine/original_match/screens.py), so neither event comes] A pair asked and neither
    made nor requested is inferred refused:
    with the kit's reason when it gave one, else, with no substitutions left, the original's
    panel, whose words are [confirmed: F027 E544; E015-r0013 state 790], else the fallback
    [designed: T102] 'not made by the original'.
    [confirmed: the kit's Match._decide reads the counter at DS:9B3A + side (screens.SUBS_LEFT)]
    The counter is the engine's, read and never written."""
    from goal2.engine.original_match import screens
    left = match.m.rd(screens.SUBS_LEFT + match.side, 1)
    done = [tuple(pair) for pair in report['made']] + [tuple(pair) for pair in report['requested']]
    refused = []
    for off, on in report['asked']:
        if (off, on) in done:
            continue
        reason = report['reasons'].get((off, on))
        refused.append([off, on, reason or (NO_MORE_SUBSTITUTES if left == 0 else NOT_MADE)])
    return {'context': report['context'], 'asked': report['asked'], 'made': report['made'],
            'requested': report['requested'], 'refused': refused, 'substitutions_left': left}
