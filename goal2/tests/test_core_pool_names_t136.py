"""[designed: owner #433/T136] Country-fitting display identities, never guest/save edits."""
import tempfile
import unittest
from pathlib import Path
from goal2.tests import requires


@requires.need(files=('GOAL.DAT',))
class Policy(unittest.TestCase):
    def test_all_canonical_countries_have_eighty_distinct_printable_country_names(self):
        from goal2.data import load
        from goal2.desktop.core_names import NamesPolicy
        from goal2.game.pool_names import table
        data=load((requires.CACHE/'GOAL.DAT').read_bytes());p=NamesPolicy(data)
        for country in range(1,129):
            with self.subTest(country=country):
                names=p.names(country);self.assertEqual(len(names),80);self.assertEqual(len(set(names)),80)
                for name in names:
                    self.assertLessEqual(len(name),12);name.encode('cp437')
                    self.assertFalse(any(ord(c)<32 or ord(c)==127 for c in name))
                if country in table():
                    _,families,initials=table()[country]
                    self.assertEqual(names,tuple(f'{i} {f}' for i,f in zip(initials,families)))
                else:
                    families={data.player_names[w] for w in data.squad_20[country]}
                    self.assertTrue(all(name.split(' ',1)[1] in families for name in names))


@requires.need(modules=('unicorn',),files=('e039-r0005-date-call.sav','GOAL.DAT'))
class GenuineNames(unittest.TestCase):
    def game(self,country=12):
        from goal2.desktop.core_model import CoreNewGame
        game=CoreNewGame(requires.CACHE/'e039-r0005-date-call.sav',requires.CACHE/'GOAL.DAT',requires.CACHE/'unused-names.g2core')
        return game.start(2028,country,'B Tester')[0]

    def test_germany_display_names_match_the_existing_policy_and_preserve_every_guest_byte(self):
        from goal2.desktop.core_names import resolver_for
        from goal2.game.pool_names import table
        m=self.game();before=m.core.save();resolve=resolver_for(m.state,m.data_path)
        _,families,initials=table()[12]
        for p in m.pool()['rows']:
            offset=(p['player']-2561)%80;expected=f'{initials[offset]} {families[offset]}'
            self.assertEqual(resolve(p['player'],p['name']),expected)
        self.assertEqual(m.core.save(),before)

    def test_explicit_name_and_custom_country_guards_preserve_saved_text(self):
        from goal2.desktop.core_names import NamesPolicy
        from goal2.data import load
        m=self.game();before=m.core.save();word=m.pool()['rows'][0]['player']
        data=load((requires.CACHE/'GOAL.DAT').read_bytes());policy=NamesPolicy(data)
        resolve=policy.resolver(m.state)
        self.assertEqual(resolve(word,'Z Custom'),'Z Custom')
        original=policy.original_name(word)
        self.assertNotEqual(resolve(word,original),original)
        # Host policy mismatch control; the original data file and guest are untouched.
        data.country_names[12]='A custom country'
        self.assertEqual(resolve(word,original),original)
        self.assertEqual(m.core.save(),before)

    def test_view_scope_restores_raw_names_after_nested_contexts_and_errors(self):
        from goal2.core import views
        from goal2.desktop.core_names import resolver_for
        m=self.game();word=m.pool()['rows'][0]['player'];before=m.core.save()
        raw=views.Memory(m.state).player_name(word);resolve=resolver_for(m.state,m.data_path)
        with views.display_player_names(resolve):
            self.assertEqual(views.Memory(m.state).player_name(word),resolve(word,raw))
            with self.assertRaises(ValueError):
                with views.display_player_names(lambda w,n:'N Inner'):
                    self.assertEqual(views.Memory(m.state).player_name(word),'N Inner')
                    raise ValueError('controlled view failure')
            self.assertEqual(views.Memory(m.state).player_name(word),resolve(word,raw))
        self.assertEqual(views.Memory(m.state).player_name(word),raw)
        self.assertEqual(m.core.save(),before)

    def test_two_careers_and_raw_reader_do_not_share_a_name_scope_between_threads(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from goal2.core import views
        from goal2.desktop.core_names import resolver_for
        games=[self.game(12),self.game(13)];word=2561
        before=[m.core.save() for m in games]
        raw=[views.Memory(m.state).player_name(word) for m in games]
        readers=[resolver_for(m.state,m.data_path) for m in games]
        ready=Barrier(3);release=Barrier(3)
        def read(index):
            with views.display_player_names(readers[index]):
                ready.wait(timeout=10);release.wait(timeout=10)
                return views.Memory(games[index].state).player_name(word)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(read,i) for i in (0,1)]
            ready.wait(timeout=10)
            try:
                self.assertEqual([views.Memory(m.state).player_name(word) for m in games],raw)
            finally:release.wait(timeout=10)
            self.assertEqual([f.result() for f in futures],[r(word,n) for r,n in zip(readers,raw)])
        self.assertEqual([m.core.save() for m in games],before)

    @requires.need(files=('e010-r0008-halftime.sav',))
    def test_genuine_match_scorers_and_commentary_use_the_same_scoped_name_reader(self):
        from goal2.core import Core,views
        core=Core.start((requires.CACHE/'e010-r0008-halftime.sav').read_bytes()).core
        state=core.wait.state;before=core.save();plain=views.board(state)
        seen=[]
        def display(word,original):
            seen.append(word);return f'P{word}'
        # Host presentation control over a genuine original match, not a new game-rule claim.
        with views.display_player_names(display):
            named=views.board(state)
            self.assertTrue(any(named['scorers']))
            seen.clear();_,commentary=views.commentary(state,0)
        self.assertTrue(seen)
        self.assertTrue(any(f'P{word}' in line['text'] for word in seen if word for line in commentary))
        for side in named['scorers']:
            for scorer in side:self.assertEqual(scorer['name'],f"P{scorer['player']}")
        self.assertEqual(named['score'],plain['score'])
        self.assertEqual(views.board(state),plain)
        self.assertEqual(core.save(),before)

    def test_model_views_adopt_names_and_a_manual_rename_wins_after_exchange(self):
        from goal2.game.pool_names import table
        m=self.game();incoming=m.pool()['rows'][0]['player'];outgoing=m.team()['squad'][0]['player']
        offset=(incoming-2561)%80;_,families,initials=table()[12];expected=f'{initials[offset]} {families[offset]}'
        before=m.core.save();self.assertEqual(m.card(incoming)['name'],expected)
        self.assertEqual(m.core.save(),before)
        self.assertIsNone(m.act('exchange',outgoing,incoming)['refused'])
        self.assertEqual(next(p['name'] for p in m.team()['squad'] if p['player']==incoming),expected)
        m.act('rename',incoming,'Z Fixture');self.assertEqual(m.card(incoming)['name'],'Z Fixture')

    def test_an_old_save_reopens_with_names_but_no_migration_or_guest_change(self):
        from goal2.desktop.core_model import CoreModel
        from goal2.game.pool_names import table
        m=self.game(13);before=m.core.save()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.g2core';path.write_bytes(before)
            again=CoreModel.from_save(path,m.data_path);word=again.pool()['rows'][0]['player']
            _,families,initials=table()[13];offset=(word-2561)%80
            self.assertEqual(again.card(word)['name'],f'{initials[offset]} {families[offset]}')
            self.assertEqual(again.core.save(),before)
