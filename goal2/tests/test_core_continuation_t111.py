"""[designed: T111] Real continental screens and annual continuation; never construct guest states."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from goal2.tests import requires

MANIFEST = json.loads((requires.ROOT / 'docs/evidence/T111/artifacts.json').read_text())
ARTIFACTS = MANIFEST['artifacts']
NEEDS = dict(modules=('unicorn',), files=tuple(a['name'] for a in ARTIFACTS) + ('GOAL.DAT',))


def loaded(index):
    from goal2.core import Core
    from goal2.core.driver import Driver
    item = ARTIFACTS[index]
    raw = (requires.CACHE / item['name']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item['sha256']
    return Driver(Core.load(raw, goal_dat=requires.CACHE / 'GOAL.DAT'))


def fix_eleven(d, message):
    """[designed: T111 test policy] Pick a ready same-line replacement; the original decides legality."""
    from goal2.core import views
    m=views.Memory(d.wait.state);rows=views.team(d.wait.state)['squad']
    cards={r['player']:views.player_card(d.wait.state,r['player']) for r in rows}
    off=next(r for r in rows if r['eleven'] and cards[r['player']]['readiness']!=m.code_str(0x1771,0x42A6))
    on=next(r for r in reversed(rows) if not r['eleven'] and r['line']==off['line']
            and cards[r['player']]['readiness']==m.code_str(0x1771,0x42AF))
    if d.wait.kind=='match-menu' and not d.stoppage():d.prematch_swap(off['player'],on['player'])
    else:d.substitute(off['player'],on['player'])


def check_groups(case, wait, view):
    """Independent text oracle: every shown country/row count and fixture pair is on the original page."""
    flat = ' '.join(wait.text.split())
    group = next(g for g in view['groups'] if g['number'] == wait.view['group'])
    case.assertIn(f"Group {group['group']}", flat)
    for row in group['rows']:
        case.assertIn(row['name'], flat)
        case.assertIn('│'.join(str(row[k]) for k in ('played','won','drawn','lost')), wait.text)
    for fixture in group['fixtures']:
        case.assertIn(fixture['first_name'], flat);case.assertIn(fixture['second_name'], flat)
    for row in view.get('top_scorers',[]):
        line=next(line for line in wait.text.splitlines() if row['name'] in line)
        case.assertIn(str(row['goals']),line)


def check_bracket(case, wait, view):
    case.assertIn(str(view['year']), wait.text)
    for match in view['matches']:
        for name in (match['first_name'],match['second_name']):
            if name:case.assertIn(name,wait.text)
        if match['played']:
            case.assertIn(f"{match['score'][0]}v{match['score'][1]}",wait.text)
            line=wait.text.splitlines()[match['y']-1+(match['winner']!=match['first'])]
            case.assertIn(view['winner_mark'],line)
            case.assertIn(match['first_name'] if match['winner']==match['first'] else match['second_name'],line)
    for row in view['top_scorers']:
        line=next(line for line in wait.text.splitlines() if row['name'] in line)
        case.assertIn(str(row['goals']),line)
    for place in view['places']:case.assertIn(place['name'],wait.text)


@requires.need(**NEEDS)
class Finals(unittest.TestCase):
    def test_finals_groups_are_the_original_page_and_escape_returns_to_menu(self):
        from goal2.core import views
        from goal2.core.screens import DOWN
        d = loaded(1)
        d.goto('tournament')
        self.assertEqual(d.wait.kind, 'tournament')
        self.assertEqual(d.wait.view['display'], 'finals')
        view = views.tournament(d.wait.state, **{k:d.wait.view[k] for k in ('country','world','display')})
        self.assertEqual(len(view['groups']), 2)
        check_groups(self, d.wait, view)
        first = d.wait.view['group']
        saved=d.core.save()
        d.press(DOWN, expect=('tournament',))
        self.assertNotEqual(d.wait.view['group'], first)
        check_groups(self, d.wait, view)
        from goal2.core import Core
        from goal2.core.driver import Driver
        restored=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
        restored.press(DOWN,expect=('tournament',))
        self.assertEqual(restored.core.memory_sha256(),d.core.memory_sha256())
        d.back();self.assertEqual(d.wait.kind, 'manager-menu')


@requires.need(**NEEDS, slow=True)
class Continuation(unittest.TestCase):
    def test_aging_and_pool_at_the_real_qualifying_boundary(self):
        from goal2.core import views
        d = loaded(0)
        before = d.wait.state
        d.play_round(fix_eleven=fix_eleven)
        after = d.wait.state
        self.assertEqual((views.Memory(before).game(0x3C), views.Memory(after).game(0x3C)), (2,3))
        self.assertEqual(d.core.memory_sha256(),loaded(1).core.memory_sha256())
        def records(state):
            m=views.Memory(state)
            words={r['player'] for r in views.team(state)['squad']} | {r['player'] for r in views.pool(state)['rows']}
            return {w:bytes(m.mem[m.far(views.PLAYERS)+20*w:m.far(views.PLAYERS)+20*w+20]) for w in words}
        old,new=records(before),records(after)
        self.assertEqual(len(old.keys() & new.keys()),100)
        for word in old.keys() & new.keys():
            a,b=old[word],new[word]
            self.assertEqual(b[1],a[1]+1);self.assertEqual(b[2:4],a[2:4])
            self.assertEqual((b[5],b[7]),(a[5],a[7]))
            # [confirmed: F016 32EB] Continuing ability, including the word arithmetic and low byte.
            age,peak,rating=b[1],b[2],b[3]
            k=(peak-age)//2 if age<peak else max(0,age-peak-3)
            self.assertEqual(b[4],(((rating*((16-k)&65535))&65535)//16)&255,word)

    def test_continental_bracket_and_next_phase(self):
        from goal2.core import views
        from goal2.core.screens import RETURN
        d=loaded(2)
        d.goto('tournament')
        self.assertEqual(d.wait.kind,'championship-browse')
        self.assertEqual(d.wait.view['display'],'championship')
        view=views.bracket(d.wait.state,d.wait.view['country'])
        # [confirmed: this real checkpoint and 91CE] Only the two semi-final fixtures exist initially.
        self.assertEqual(len(view['matches']),2)
        check_bracket(self,d.wait,view)
        from goal2.core.screens import LEFT
        d.press(LEFT,expect=('tournament',))
        check_groups(self,d.wait,views.tournament(d.wait.state,**{k:d.wait.view[k] for k in ('country','world','display')}))
        d.back()
        saved=d.core.save()
        d.trail=[]
        for _ in range(8):
            d.play_round(fix_eleven=fix_eleven)
            if views.Memory(d.wait.state).game(0x3C)==5:break
        self.assertEqual(views.Memory(d.wait.state).game(0x3C),5)
        brackets=[w for w in d.trail if w.kind=='championship-bracket']
        self.assertTrue(brackets)
        for wait in brackets:check_bracket(self,wait,views.bracket(wait.state,wait.view['country']))
        self.assertEqual(len(views.bracket(brackets[-1].state,brackets[-1].view['country'])['places']),3)
        self.assertTrue(any(k=='championship-bracket' for k,_ in d.pages))
        from goal2.core import Core
        from goal2.core.driver import Driver
        replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
        for _ in range(8):
            replay.play_round(fix_eleven=fix_eleven)
            if views.Memory(replay.wait.state).game(0x3C)==5:break
        self.assertEqual(replay.core.memory_sha256(),d.core.memory_sha256())
        # [confirmed: F017 57E5/56F3; this real continuation] The next Play announces one managed replacement
        # and returns to the menu without consuming a fixture.
        before=d.wait.state;m=views.Memory(before)
        old={r['player'] for r in views.team(before)['squad']}|{r['player'] for r in views.pool(before)['rows']}
        fixture=m.game(0x26,2)
        d.play_round(fix_eleven=fix_eleven)
        after=d.wait.state;n=views.Memory(after)
        new={r['player'] for r in views.team(after)['squad']}|{r['player'] for r in views.pool(after)['rows']}
        self.assertEqual(len(old-new),1);self.assertEqual(len(new-old),1)
        self.assertEqual(n.game(0x26,2),fixture)
        retired=next(iter(old-new));replacement=next(iter(new-old))
        a=n.far(views.PLAYERS)+20*retired
        self.assertEqual(bytes(n.mem[a:a+20]),bytes(20))
        self.assertEqual(n.byte(n.far(views.PLAYERS)+20*replacement),views.team(after)['country'])
        papers=[p for kind,p in d.pages if kind=='bulletin']
        self.assertTrue(any('IS TO RETIRE' in p['middle']['lines'] for p in papers))


@requires.need(**(NEEDS | {'modules':('unicorn','PySide6')}),slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app=QApplication.instance() or QApplication([]);load_fonts()

    def test_finals_and_bracket_pages_fit_and_show_the_memory_view(self):
        from goal2.core import views
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixtures_page import core_fixtures_view
        from goal2.desktop.fixed_page import problems
        for index in (1,2):
            d=loaded(index)
            with tempfile.TemporaryDirectory() as folder:
                model=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
                before=model.memory_sha256();w=CoreWindow(model);w.show();self.app.processEvents()
                try:
                    w.navigate(3);core_fixtures_view(w,1);self.app.processEvents()
                    if index==1:
                        self.assertEqual(w.core_tournament_content.currentIndex(),0)
                        self.assertTrue(w.core_group_board.groups)
                    else:
                        self.assertEqual(w.core_tournament_content.currentIndex(),1)
                        view=views.bracket(model.state)
                        for match in view['matches']:
                            self.assertIn(match['first_name'],w.core_bracket_board.text())
                            self.assertIn(match['second_name'],w.core_bracket_board.text())
                        r=w.core_round;r.queue=[('championship-bracket',view)];r.after='menu';r.next_page()
                        self.assertEqual(r.page_content.currentIndex(),2)
                        self.assertEqual(r.round_bracket_board.text(),w.core_bracket_board.text())
                        group_view=views.tournament(model.state,display='finals')
                        group_view['selected_group']=2
                        r.queue=[('tournament-table',group_view)];r.next_page()
                        self.assertIn('Group B',r.page_board.text())
                        for row in group_view['groups'][1]['rows']:self.assertIn(row['name'],r.page_board.text())
                        # Restore the real bracket view for the four-size bounds.
                        r.queue=[('championship-bracket',view)];r.next_page()
                    for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
                        w.resize(round(.9*width),round(.9*height));self.app.processEvents();self.app.processEvents()
                        self.assertEqual(problems(w),[],(index,width,height,problems(w)))
                    self.assertEqual(model.memory_sha256(),before)
                finally:w.close();self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
