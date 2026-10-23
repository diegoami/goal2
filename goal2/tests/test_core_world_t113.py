"""[designed: T113] World Cup reads checked against the original, reached only by original keys."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

from goal2.tests import requires

ARTIFACTS = json.loads((requires.ROOT/'docs/evidence/T113/artifacts.json').read_text())['artifacts']
NEEDS = dict(modules=('unicorn',),files=tuple(a['name'] for a in ARTIFACTS)+('GOAL.DAT',))


def loaded(index):
    from goal2.core import Core
    from goal2.core.driver import Driver
    item=ARTIFACTS[index];raw=(requires.CACHE/item['name']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    return Driver(Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT'))


def group_oracle(case,wait,view):
    group=next(g for g in view['groups'] if g['number']==wait.view['group'])
    case.assertIn('Group '+group['group'],wait.text)
    for row in group['rows']:
        line=next(line for line in wait.text.splitlines() if '│'+row['name'] in line)
        values=re.search(r'║(\d+)│(\d+)│(\d+)│(\d+)║\s*(\d+)│\s*(\d+)║\s*(\d+)│',line)
        case.assertIsNotNone(values,line)
        case.assertEqual(tuple(map(int,values.groups())),tuple(row[k] for k in ('played','won','drawn','lost','for','against','points')))
    for f in group['fixtures']:
        line=next(line[36:] for line in wait.text.splitlines()
                  if f['first_name'] in line[36:] and f['second_name'] in line[36:])
        if f['played']:case.assertIn(f"{f['score'][0]}v{f['score'][1]}",line.replace(' ',''))
        else:case.assertRegex(line,r'\sv\s')
    scorers_oracle(case,wait,view)


def scorers_oracle(case,wait,view):
    for row in view['top_scorers']:
        line=next(line for line in wait.text.splitlines() if row['name'] in line)
        case.assertIn(str(row['goals']),line)


def bracket_oracle(case,wait,view):
    case.assertIn(str(view['year']),wait.text)
    if view['world'] and view['places']:
        case.assertNotIn('TOP SCORERS',wait.text)
        case.assertEqual(view['top_scorers'],[])
    for match in view['matches']:
        for index,key in enumerate(('first_name','second_name')):
            if match[key]:case.assertIn(match[key],wait.text.splitlines()[match['y']-1+index])
        if match['played']:
            line=wait.text.splitlines()[match['score_y']-1]
            case.assertIn(f"{match['score'][0]}v{match['score'][1]}",line.replace(' ',''))
            winner=0 if match['winner']==match['first'] else 1
            case.assertEqual(wait.text.splitlines()[match['y']-1+winner][match['x']+14],view['winner_mark'])
    scorers_oracle(case,wait,view)
    for place in view['places']:case.assertIn(place['name'],wait.text)


@requires.need(**NEEDS)
class World(unittest.TestCase):
    def test_the_world_bracket_and_all_eight_completed_groups_are_the_original(self):
        from goal2.core import Core,views
        from goal2.core.driver import Driver
        from goal2.core.screens import LEFT,RIGHT,DOWN,SPACE
        d=loaded(1);d.goto('tournament')
        self.assertEqual(d.wait.kind,'championship-browse');self.assertTrue(d.wait.view['world'])
        bracket=views.bracket(d.wait.state,d.wait.view['country'],world=True)
        self.assertEqual(len(bracket['slots']),16);self.assertEqual(len(bracket['matches']),8)
        bracket_oracle(self,d.wait,bracket)
        d.press(SPACE,expect=('championship-browse',))
        self.assertEqual(d.wait.view['country'],33)
        bracket_oracle(self,d.wait,views.bracket(d.wait.state,33,world=True))
        d.press(LEFT,expect=('tournament',))
        view=views.tournament(d.wait.state,**{k:d.wait.view[k] for k in ('country','world','display')})
        self.assertEqual(len(view['groups']),8);self.assertEqual(view['country'],1)
        self.assertEqual(len({r['country'] for g in view['groups'] for r in g['rows']}),32)
        self.assertTrue(any(r['played'] for g in view['groups'] for r in g['rows']))
        self.assertEqual(views.tournament(d.wait.state,country=128,world=True,display='finals'),view)
        seen=set()
        for _ in range(8):
            group_oracle(self,d.wait,view);seen.add(d.wait.view['group']);d.press(DOWN,expect=('tournament',))
        self.assertEqual(seen,set(range(1,9)))
        saved=d.core.save();d.press(DOWN)
        replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'));replay.press(DOWN)
        self.assertEqual(d.core.memory_sha256(),replay.core.memory_sha256())
        d.press(SPACE);self.assertEqual(d.wait.view['country'],1)
        d.back();self.assertEqual(d.wait.kind,'manager-menu')
        early=loaded(0);early.goto('tournament')
        group_oracle(self,early.wait,views.tournament(early.wait.state))
        early.press(RIGHT,expect=('championship-browse',))
        pending=views.bracket(early.wait.state,world=True)
        self.assertEqual(pending['matches'],[]);self.assertEqual(pending['places'],[])
        bracket_oracle(self,early.wait,pending)


@requires.need(**NEEDS,slow=True)
class Continuation(unittest.TestCase):
    def test_the_original_finishes_the_world_cup_and_starts_the_next_cycle(self):
        from goal2.core import Core,views
        from goal2.core.driver import Driver
        d=loaded(1);saved=d.core.save();d.trail=[]
        rounds=0
        for _ in range(8):
            d.play_round();rounds+=1
            if views.Memory(d.wait.state).game(0x38,2)==2:break
        self.assertEqual(d.wait.kind,'manager-menu')
        # [confirmed: this original-key continuation] The new continental campaign opens at stage 2/fixture 1.
        m=views.Memory(d.wait.state)
        self.assertEqual((m.game(0x38,2),m.game(0x3C),m.game(0x40),m.game(0x26,2)),(2,2,0,1))
        brackets=[w for w in d.trail if w.kind=='championship-bracket' and w.view['world']]
        self.assertTrue(brackets)
        for w in brackets:bracket_oracle(self,w,views.bracket(w.state,w.view['country'],world=w.view['world']))
        final=views.bracket(brackets[-1].state,brackets[-1].view['country'],world=True)
        self.assertEqual(len(final['matches']),16);self.assertEqual(len(final['places']),3)
        self.assertTrue(any(kind=='championship-bracket' and page['world'] for kind,page in d.pages))
        replay=Driver(Core.load(saved,goal_dat=requires.CACHE/'GOAL.DAT'))
        for _ in range(rounds):replay.play_round()
        self.assertEqual(replay.core.memory_sha256(),d.core.memory_sha256())


@requires.need(**(NEEDS|{'modules':('unicorn','PySide6')}),slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.style import load_fonts
        cls.app=QApplication.instance() or QApplication([]);load_fonts()

    def test_world_groups_bracket_and_round_pages_fit_and_show_the_stored_facts(self):
        from goal2.core import views
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        from goal2.desktop.fixtures_page import core_fixtures_view
        from goal2.desktop.fixed_page import problems
        for index in (0,1,2):
            d=loaded(min(index,1))
            final=None
            if index==2:
                d.trail=[]
                for _ in range(4):d.play_round()
                last=next(w for w in reversed(d.trail) if w.kind=='championship-bracket' and w.view['world'])
                final=views.bracket(last.state,last.view['country'],world=True)
            with tempfile.TemporaryDirectory() as folder:
                model=CoreModel(d.core,requires.CACHE/'GOAL.DAT',Path(folder)/'game.g2core')
                before=model.memory_sha256();w=CoreWindow(model);w.show();self.app.processEvents()
                try:
                    w.navigate(3);core_fixtures_view(w,1);self.app.processEvents()
                    if index<2:self.assertIn('WORLD CUP',w.core_tournament_title.text())
                    if index==0:
                        self.assertEqual(w.core_tournament_content.currentIndex(),0)
                        self.assertEqual(len(w.core_group_board.groups),8)
                        for g in w.core_group_board.groups:
                            w.core_group_board.offset=g['number']-1;w.core_group_board.show_window()
                            for row in g['rows']:self.assertIn(row['name'],w.core_group_board.text())
                    else:
                        view=final or views.bracket(model.state,world=True)
                        if index==1:self.assertEqual(w.core_tournament_content.currentIndex(),1)
                        r=w.core_round;r.queue=[('championship-bracket',view)];r.after='menu';r.next_page()
                        self.assertIn('WORLD CUP',r.round_bracket_board.title)
                        for match in view['matches']:
                            self.assertIn(match['first_name'],r.round_bracket_board.text())
                            self.assertIn(match['second_name'],r.round_bracket_board.text())
                        if index==1:self.assertEqual(r.round_bracket_board.text(),w.core_bracket_board.text())
                        if final:
                            self.assertNotIn('TOP SCORERS',r.round_bracket_board.text())
                            for row in final['places']:self.assertIn(row['name'],r.round_bracket_board.text())
                    for width,height in ((1440,900),(1050,780),(900,640),(2560,1600)):
                        w.resize(round(.9*width),round(.9*height));self.app.processEvents();self.app.processEvents()
                        self.assertEqual(problems(w),[],(index,width,height,problems(w)))
                    self.assertEqual(model.memory_sha256(),before)
                finally:w.close();self.app.processEvents()


if __name__=='__main__':unittest.main()
