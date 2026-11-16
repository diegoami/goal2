"""[designed: T170r/#745] Read-only pre-match action audit; no original bytes in output.

The sealed API executes only in PyPy. The original-menu reference stays CPython
and drives real keys to 4B61's menu; it changes no guest data directly.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sealed_probe(raw):
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import REGS, Uc
    from goal2.engine.original_match.match import PLAYER_POSITION, TEAM_KEYS
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession, canonical_hash
    from goal2.game.prematch_seam import PrematchSeam
    assert sys.implementation.name == 'pypy' and sys.version_info[:2] == (3, 11) and Uc is None
    tables = engine_tables.load()
    session = SeasonSession(Image.from_bytes(raw).state(tables))
    assert session.advance().status == 'match'
    m = session.pending_match; seam = PrematchSeam(m)
    def decision():
        for ev in m.events():
            if ev.kind == 'decision':
                assert ev.data['context'] == 'pre_match'
                return ev.data
        raise AssertionError('missing pre_match decision')
    d = decision()
    xi = next(w for w in d['eleven'] if m._player(w, PLAYER_POSITION) >= 2 and m._available(w))
    bench = next(w for w in d['bench'] if m._player(w, PLAYER_POSITION) >= 2 and m._available(w))
    pool = next(w for w in d['pool'] if m._player(w, PLAYER_POSITION) >= 2 and m._available(w))
    opponent = m._squad(m.opts[TEAM_KEYS[1-m.side]])[1]
    cases = []
    for domain, word in (('xi', xi), ('bench', bench), ('pool', pool)):
        cases.extend([
            (f'position:{domain}', {'positions': {word: (m._player(word, 6)+1) % 14}}),
            (f'club-position:{domain}', {'positions': {word: m._player(word, 7)}}),
            (f'own-tactic:{domain}', {'own_tactics': {word: {1: True}}}),
        ])
    cases.append(('mark:xi', {'marking': {xi: opponent}}))
    cases.append(('mark:bench', {'marking': {bench: opponent}}))
    def snapshot():
        return (m.memory_component(), {r:m.m.reg(r) for r in REGS}, copy.deepcopy(m.st),
                copy.deepcopy(m.opts), copy.deepcopy(m.inputs), copy.deepcopy(m._replay_actions),
                m._replay_events, copy.deepcopy(m._frame_state()))
    refusals = []
    for name, answer in cases:
        before = snapshot()
        try:
            m.answer(edit_only=True, **answer)
        except ValueError as exc:
            error = str(exc)
        else:
            raise AssertionError('audit assumption stale: input now accepted '+name)
        assert snapshot() == before, 'refusal consumed data: '+name
        refusals.append({'action': name, 'refusal': error, 'full_memory_all16_state_replay_pure': True})
    # [confirmed: T134] Same-position swap gives an observable current roster
    # without changing XI eligibility. Session.observe is deliberately a route boundary.
    positions = dict(d['positions'])
    pair = next([a,b] for i,a in enumerate(d['eleven']) for b in d['eleven'][i+1:]
                if positions[a] == positions[b])
    boundary_hash = canonical_hash(session.state)
    seam.swap(*pair); changed = decision()
    before = snapshot(); current_state = m.records_after()
    current = Image.from_state(current_state, tables)
    boundary = Image.from_state(session.state, tables)
    assert snapshot() == before, 'public current-state read changed the Match'
    assert current.squad(m.opts['managed'])[:11] == changed['eleven']
    assert current.squad(m.opts['managed']) != boundary.squad(m.opts['managed'])
    assert canonical_hash(session.state) == boundary_hash
    return dict(runtime='pypy3.11', source_fixture_sha256=hashlib.sha256(raw).hexdigest(),
                team_context=d['team_context'], decision_fields=sorted(d),
                managed_record_count=len(d['player_records']), pool_word_count=len(d['pool']),
                pool_records_published='pool_records' in d,
                opponent_roster_published='opponent' in d or 'teams' in d,
                refusals=refusals, current_public_read_pure=True,
                current_roster_equals_decision=True, boundary_roster_differs_from_current=True,
                boundary_hash_unchanged=True, swap=pair,
                boundary_state_hash=boundary_hash, current_preview_hash=canonical_hash(current_state))


def original_mark_rows(upstream):
    sys.path[:0] = [str(upstream), str(upstream/'runtime'), str(upstream/'tools'), str(upstream/'tests')]
    from tests.test_route_sealed import _fixtures
    from original_match.match import Match, Fixture, SITE_SELECT, SITE_MENU, MENU_OWN, PLAYER_POSITION
    from original_match import screens as S
    image, regs, fixture = _fixtures().entry()
    class Reached(Exception):
        pass
    rows = []
    for domain in ('xi-outfield', 'xi-keeper', 'bench-outfield', 'pool-outfield'):
        m = Match(image, Fixture(**fixture), engine='original', tail=False)
        for k,v in regs.items():m.m.set_reg(k,v)
        m.opts['pre_match_edits'] = True  # reference keyboard-policy declaration; no guest patch
        for ev in m.events():
            if ev.kind == 'decision':break
        assert ev.data['context'] == 'pre_match'
        d = ev.data
        if domain == 'xi-keeper':
            word = next(w for w in d['eleven'] if m._player(w, PLAYER_POSITION) == 0 and m._available(w))
        else:
            words = d['eleven'] if domain.startswith('xi') else d['bench'] if domain.startswith('bench') else d['pool']
            word = next(w for w in words if m._player(w, PLAYER_POSITION) >= 2 and m._available(w))
        previous = m._key_for; pane = [1]; presses = [0]
        def key(site):
            if site == SITE_MENU:
                bp = m.m.reg('bp')
                caller = m.m.where(m.m.frame_word(bp,4),m.m.frame_word(bp,2))
                if caller == MENU_OWN:
                    rows.append(dict(domain=domain, word=word, pane=pane[0],
                                     position=m._player(word, PLAYER_POSITION), available=m._available(word),
                                     menu_rows=m.m.frame_word(bp,6)&255,
                                     match_set_up=m.m.rd(0x0C1E,1), in_match_menu_used=m.m.rd(0x0C1F,1)))
                    raise Reached
            if site == SITE_SELECT:
                presses[0] += 1; assert presses[0] <= 200, 'reference cursor did not reach target'
                target_pane = 2 if domain.startswith('pool') else 1
                if pane[0] != target_pane:
                    pane[0] = target_pane
                    return S.LEFT
                if pane[0] == 1:
                    here = m.m.rd(S.SELECT_CURSOR); target = m._squad(m.opts['managed']).index(word)+1
                else:
                    scroll,cursor = m._pool_state(); here = scroll+cursor; target = m._pool().index(word)+2
                if here != target:return S.DOWN if here < target else S.UP
                return ord('T')
            return previous(site)
        # A supported select-screen input opens E44F; independent reference keys
        # inspect T before any requested pair is made. No mutation of guest records.
        pos = dict(d['positions']); off = d['eleven'][-1]
        on = next(w for w in d['bench'] if pos[w] == pos[off])
        m.answer(edit_only=True, substitutions=[[off,on]])
        m._key_for = key
        try:
            for _ in m.events():pass
        except Reached:
            pass
        else:
            raise AssertionError('original own-menu read not reached')
    return dict(runtime='cpython-unicorn', entry_sha256=image.sha256(), menu_controls=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, default=Path(os.environ.get('GOAL2_ARCHAEOLOGY', ROOT.parent/'goal2-archaeology-engine')))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    from goal2.engine.original_match.assets import reference_image
    from goal2.tests import pypy_engine
    raw = reference_image(ROOT/'.cache')
    report = dict(schema='t170r-action-audit/1', goal2_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  upstream_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.upstream,text=True).strip(),
                  sealed=pypy_engine.call('tools.prematch_action_audit:sealed_probe',raw),
                  original=original_mark_rows(args.upstream))
    report['audited_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__).resolve(), ROOT/'goal2/engine/original_match/match.py',
                  ROOT/'goal2/engine/original_match/route_team.py',
                  ROOT/'goal2/ui/s08_squad.py', ROOT/'goal2/ui/s09_player_tactics.py',
                  ROOT/'goal2/ui/s10_team_tactics.py']}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(report,sort_keys=True))


if __name__ == '__main__':main()
