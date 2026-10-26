"""[designed: owner #433/T136] Country-fitting display identities, never guest/save edits."""
import tempfile
import unittest
import re
import unicodedata
from pathlib import Path
from goal2.tests import requires


def distinct_surname(name):
    value=re.sub('[^a-z]','',unicodedata.normalize('NFKD',name.casefold()))
    while len(value)>4 and value.startswith(('al','el')):
        value=value[2:]
    return value


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
                    self.assertLessEqual(len(name),34);name.encode('cp437')
                    self.assertFalse(any(ord(c)<32 or ord(c)==127 for c in name))
                if country in table():
                    _,families,initials=table()[country]
                    self.assertEqual(names,tuple(f'{i} {f}' for i,f in zip(initials,families)))
                else:
                    first=20*(country-1)+1
                    if data.country_names[country]=='Myanmar':
                        self.assertEqual(names[0],'Aung Win')
                        self.assertTrue(all(len(name.split()[0])>1 for name in names))
                    else:
                        self.assertGreaterEqual(len({distinct_surname(name.split(' ',1)[1]) for name in names}),60)
                    current={f'{data.player_initials[w]} {data.player_names[w]}' for w in range(first,first+20)}
                    self.assertFalse(set(names)&current)

    def test_contrasting_fallback_nations_use_independently_known_family_names(self):
        from goal2.data import load
        from goal2.desktop.core_names import NamesPolicy
        data=load((requires.CACHE/'GOAL.DAT').read_bytes());policy=NamesPolicy(data)
        # Independent country facts, rather than reproducing the resolver's indexing or source parser.
        expected={'Malta':'Vella','Poland':'Nowak','Chile':'González'}
        actual={}
        for country,family in expected.items():
            actual[country]={name.split(' ',1)[1] for name in policy.names(data.country_names.index(country))}
            self.assertIn(family,actual[country]);self.assertNotIn('Musta',actual[country])
        self.assertFalse(actual['Poland']&actual['Chile'])

    def test_extended_profiles_have_readable_male_forms_and_distinct_surname_groups(self):
        from goal2.desktop.core_names import extended_profiles
        particles=('de ','da ','del ','du ','van ','von ','al-','al ','el-','el ','bin ','ben ','ibn ')
        for entry in extended_profiles().values():
            if entry['kind']!='family':continue
            with self.subTest(country=entry['country']):
                families=entry['families']
                self.assertGreaterEqual(len({distinct_surname(name) for name in families}),60)
                for family in families:
                    self.assertTrue(family[0].isupper() or family.startswith(particles),family)
                if entry['country']=='India':self.assertNotIn('Devi',families)
                if entry['country']=='Indonesia':self.assertNotIn('Irawati',families)

    def test_country_curation_keeps_common_roots_without_korean_spelling_duplicates(self):
        from goal2.desktop.core_names import extended_profiles
        profiles={p['country']:p for p in extended_profiles().values()}
        self.assertTrue({'Dlamini','Nkosi','Ndlovu','Mokoena'}<=set(profiles['South Africa']['families']))
        self.assertTrue({'Kim','Ri','Pak','Choe'}<=set(profiles['North Korea']['families']))
        self.assertFalse({'Lee','Park','Terakoshi'}&set(profiles['North Korea']['families']))
        self.assertIn('Al-Kuwari',profiles['Qatar']['families'])
        self.assertIn('al-Mohannadi',profiles['Qatar']['families'])
        self.assertIn('Jónsson',profiles['Iceland']['families'])
        self.assertTrue(all(name.casefold().endswith('son') for name in profiles['Iceland']['families']))


@requires.need(modules=('PySide6',))
class NameLayout(unittest.TestCase):
    def test_long_names_cannot_paint_over_caps_or_roles(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QRect
        from goal2.desktop.core_pool_roster import PoolRoster
        from goal2.desktop.style import load_fonts
        app=QApplication.instance() or QApplication([])
        load_fonts()
        strip=PoolRoster(capacity=1,marks=False)
        self.addCleanup(strip.close)
        strip.resize(314,100);strip.caps={2561:65535}
        strip.set_rows([(2561,'A Randrianantenaina','m','midfield',False,False)],0)
        strip.show();app.processEvents()
        long_image=strip.grab().toImage()
        self.assertIn('A Randrianantenaina',strip.accessibleName())
        self.assertIn('CAPS 65535',strip.accessibleName())
        strip.set_rows([(2561,'A A','m','midfield',False,False)],0)
        app.processEvents();short_image=strip.grab().toImage()
        dpr=long_image.devicePixelRatio()
        # Independent painted-column requirement: changing only a name cannot change
        # any pixel in the existing CAPS and role area, at either native pixel density.
        area=QRect(round(188*dpr),round(32*dpr),round(110*dpr),round(26*dpr))
        self.assertEqual(long_image.copy(area),short_image.copy(area))

    @requires.need(modules=('unicorn',),files=('e039-r0005-date-call.sav','GOAL.DAT'))
    def test_long_country_name_remains_complete_in_the_pool_card(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.core_model import CoreNewGame
        from goal2.desktop.core_window import CoreWindow
        from goal2.data import load
        app=QApplication.instance() or QApplication([])
        data=load((requires.CACHE/'GOAL.DAT').read_bytes())
        game=CoreNewGame(requires.CACHE/'e039-r0005-date-call.sav',requires.CACHE/'GOAL.DAT',requires.CACHE/'unused-long-names.g2core')
        model=game.start(2028,data.country_names.index('Madagascar'),'B Tester')[0]
        before=model.core.save()
        window=CoreWindow(model);self.addCleanup(window.close)
        window.show();window.navigate(2);app.processEvents()
        self.assertTrue(any(len(row[1])>12 for row in window.pool_strip.rows))
        row=next(i for i,row in enumerate(window.pool_strip.rows) if 'Rakotomalala' in row[1])
        window.pool_strip.set_current(row,notify=True);app.processEvents()
        selected=window.pool_selected()
        self.assertIsNotNone(selected)
        name=model.card(selected)['name']
        self.assertIn('Rakotomalala',name)
        # The full identity is available in the actual card, even when the strip elides it.
        self.assertIn(name,window.pool_card.accessibleName())
        window.pool_card.repaint()
        self.assertIn(name.upper(),window.pool_card.drawn)
        window.pool_compare.click();app.processEvents();window.pool_comparison.repaint()
        self.assertEqual(window.pool_comparison.cards[1]['full_name'],name)
        self.assertIn(name,window.pool_comparison.drawn)
        self.assertEqual(model.core.save(),before)


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

    def test_burmese_model_views_keep_complete_personal_names_without_initials(self):
        from goal2.data import load
        data=load((requires.CACHE/'GOAL.DAT').read_bytes())
        model=self.game(data.country_names.index('Myanmar'));before=model.core.save()
        rows=model.pool()['rows'];names={row['name'] for row in rows}
        self.assertEqual(len(rows),80);self.assertEqual(len(names),80)
        self.assertIn('Aung Win',names);self.assertIn('Kyaw Naing',names)
        self.assertTrue(all(len(name.split()[0])>1 for name in names))
        for row in rows:self.assertEqual(model.card(row['player'])['name'],row['name'])
        self.assertEqual(model.core.save(),before)

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

    @requires.need(files=('g16-proof-279904b6-private.zip',))
    def test_original_year_rollovers_keep_country_names_without_migrating_the_guest(self):
        import hashlib
        from zipfile import ZipFile
        from goal2.core import Core
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_names import resolver_for
        from goal2.game.pool_names import table
        bundle=requires.CACHE/'g16-proof-279904b6-private.zip'
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(),
                         '2332459f7bf64be1afd2e92fc61d81f3b9489bf9d01208a3e6ad8edb469d4cd9')
        with ZipFile(bundle) as z:
            for year in (1,4):
                with self.subTest(annual=year):
                    raw=z.read(f'.cache/T123-proof-r2/annual-{year}.g2core')
                    core=Core.load(raw,goal_dat=requires.CACHE/'GOAL.DAT')
                    m=CoreModel(core,requires.CACHE/'GOAL.DAT',requires.CACHE/'unused-rollover.g2core')
                    before=core.save();_,families,initials=table()[20]
                    for p in m.pool()['rows']:
                        if p['player']>=2561:
                            offset=(p['player']-2561)%80
                            self.assertEqual(p['name'],f'{initials[offset]} {families[offset]}')
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

    def test_explicit_original_bank_name_wins_and_intent_survives_save_reopen(self):
        from goal2.data import load
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_names import NamesPolicy,explicit_from_save
        m=self.game();word=m.pool()['rows'][0]['player']
        policy=NamesPolicy(load((requires.CACHE/'GOAL.DAT').read_bytes()))
        english=policy.original_name(2561 if word!=2561 else 2562)
        m.act('rename',word,english)
        self.assertEqual(m.card(word)['name'],english)
        before=m.core.save()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'renamed.g2core';m.save(path);saved=path.read_bytes()
            self.assertIn(word,explicit_from_save(saved))
            again=CoreModel.from_save(path,m.data_path)
            self.assertEqual(again.card(word)['name'],english)
            self.assertEqual(again.core.save(),before)
        self.assertEqual(m.core.save(),before)

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
