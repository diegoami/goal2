"""[designed: T183b/#594] Current metadata, not inherited halftime context.

The original arm executes actual E44F then Ins on the projected current input;
the native arm executes the accepted preparation/assistant in a PyPy child.
This is an assistant projection proof, not a native-route bootstrap claim.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires
from goal2.tests.pypy_engine import call
from goal2.game.best_twenty_state import prepare, candidate

ROOT=Path(__file__).resolve().parents[2]


def original(prepared):
    from goal2.engine.original_match import Image
    from goal2.engine.original_match.machine import Machine, MEM_SIZE
    from goal2.game import engine_tables
    image=Image.from_state(prepared.native,engine_tables.load())
    source=Image.from_memory_component(prepared.source.mem)
    lo=image.load*16;hi=image.DS*16
    image.memory[lo:hi]=source.memory[lo:hi]
    m=Machine(image.memory,image.load)
    reads=[]
    def key(replay):
        site=m.where(m.stack_word(2),m.stack_word(0))
        reads.append(site)
        if len(reads)==2:
            m.stop('selected');return
        if site!='0791:E61F':raise AssertionError('unexpected original key site '+site)
        m.wr(0xA976,0xB6B6)
        m.set_reg('ax',(m.reg('ax')&0xFF00)|0xB6)
        m.return_from(True)
    def poll(replay):
        m.set_reg('ax',(m.reg('ax')&0xFF00)|1);m.return_from(True)
    m.at('214B:08DD',key);m.at('214B:0723',poll)
    end=m.far_call('0791:E44F',(prepared.source.managed_country,),'0791:0000',m.seg(0x3052),0x3000)
    m.set_reg('bp',0x3456)
    if m.run(end,fresh=True)!='selected':raise AssertionError('original did not stop after Ins')
    if reads!=['0791:E61F','0791:E61F']:raise AssertionError(reads)
    image.memory[:MEM_SIZE]=m.read(0,MEM_SIZE)
    return image


@requires.need(modules=('unicorn',),files=('GOAL.DAT','e010-r0008-halftime.sav'))
class CurrentCareer(unittest.TestCase):
    def setUp(self):
        from goal2.desktop.model import DesktopModel
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.model=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',Path(self.folder.name)/'game.g2save',country=4)

    def test_current_records_calendar_pool_and_immutable_tables_are_projected(self):
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        exchanges=0
        for year,stage,low in ((1990,5,1361),(1992,2,1)):
            with self.subTest(year=year):
                self.model.new_campaign(4,year)
                self.model.set_position(self.model.state.managed_squad[3])
                incoming=next(r['id'] for r in self.model.pool_view()['reserves'] if r['availability']['available'])
                if self.model.pool_view()['window']['allowed']:
                    self.model.exchange(self.model.state.managed_squad[-1],incoming)
                    exchanges+=1
                before=copy.deepcopy(self.model.state)
                p=prepare(self.model.state);im=Image.from_state(p.native,engine_tables.load())
                self.assertEqual(self.model.state,before)
                self.assertEqual(im.memory[im.far(0xA91B):im.far(0xA91B)+3061*20],b''.join(before.players))
                self.assertEqual(im.memory[im.DS*16+0xC1E:im.DS*16+0xC20],bytes(2))
                self.assertEqual(im.memory[im.far(0xA923)+0x3C],stage)
                self.assertEqual(im.rd_far(0xA923,0x26),low)
                words=[int.from_bytes(im.memory[im.far(0xA927)+2*(im.rd(0x6D1A)+n):im.far(0xA927)+2*(im.rd(0x6D1A)+n)+2],'little') for n in range(80)]
                self.assertEqual(words,before.campaign.reserve_ids)
                expected=[int(f.fixture_id.split(':')[1]) for f in before.campaign.fixtures]
                at=im.far(0xA92F)+before.managed_country*72
                actual=[int.from_bytes(im.memory[at+2*n:at+2*n+2],'little') for n in range(36)]
                self.assertEqual(actual,[0]*(36-len(expected))+expected)
                source=Image.from_memory_component(before.mem)
                self.assertEqual(im.memory[im.DS*16+0xE60:im.DS*16+0xE80],source.memory[source.DS*16+0xE60:source.DS*16+0xE80])
        self.assertGreater(exchanges,0,'the cases must exercise a real model exchange')

    def test_actual_original_keys_equal_native_and_candidate_is_private(self):
        from goal2.engine.original_match import Image
        from goal2.game import campaign_pool,engine_tables
        from goal2.tests.test_best_twenty_t183a import records
        for year in (1990,1992):
            with self.subTest(year=year):
                self.model.new_campaign(4,year)
                if year==1990:
                    self.assertTrue(self.model.pool_view()['window']['allowed'])
                    incoming=next(r['id'] for r in self.model.pool_view()['reserves'] if r['availability']['available'])
                    self.model.exchange(self.model.state.managed_squad[-1],incoming)
                word=self.model.state.starting_eleven[3]
                self.model.set_position(word)
                bench=next(w for w in self.model.state.managed_squad if w not in self.model.state.starting_eleven)
                self.model.swap(word,bench)
                self.model.rename_manager('A Manager')
                self.model.rename_player(self.model.state.managed_squad[2],'Example')
                self.model.set_team_tactic(8)
                before=copy.deepcopy(self.model.state)
                p=prepare(self.model.state)
                expected=records(original(p))
                answer=call('goal2.tests.test_best_twenty_t183a:native',p.native)
                actual=records(Image.from_state(answer['state'],engine_tables.load()))
                for key in expected:self.assertEqual(actual[key],expected[key],key)
                result=candidate(p,answer)
                self.assertEqual(self.model.state,before)
                self.assertEqual(result.managed_squad,answer['squad'])
                self.assertEqual(result.starting_eleven,answer['squad'][:11])
                self.assertEqual(result.campaign.reserve_ids,answer['pool'])
                self.assertEqual(result.players,before.players)
                self.assertEqual(result.player_renames,before.player_renames)
                self.assertEqual(result.manager_name,before.manager_name)
                self.assertEqual(result.country_tactics,before.country_tactics)
                self.assertEqual(result.countries[4][0x2D],before.country_tactics)
                self.assertEqual(result.campaign.world,before.campaign.world)
                self.assertEqual((result.match_count,result.last_match,result.match_state),(before.match_count,before.last_match,before.match_state))
                campaign_pool.validate(result)

    def test_missing_or_unsupported_calendar_and_refused_reply_do_not_mutate(self):
        before=copy.deepcopy(self.model.state)
        p=prepare(self.model.state)
        with self.assertRaisesRegex(ValueError,'allowed selection'):
            candidate(p,{'allowed':False,'refusal':'tour'})
        self.assertEqual(self.model.state,before)
        missing=copy.deepcopy(before);missing.campaign.world=None
        with self.assertRaisesRegex(ValueError,'complete current calendar'):prepare(missing)
        later=copy.deepcopy(before);later.campaign.stage=3
        with self.assertRaisesRegex(ValueError,'native season calendar'):prepare(later)
        self.assertEqual(self.model.state,before)
        p.native['memory']='not a valid input'
        with self.assertRaisesRegex(ValueError,'input changed'):candidate(p,{'allowed':True,'refusal':None})
        self.assertEqual(self.model.state,before)

    def test_malformed_reply_is_rejected_and_source_is_preserved(self):
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        p=prepare(self.model.state);before=copy.deepcopy(self.model.state)
        answer=call('goal2.tests.test_best_twenty_t183a:native',p.native)
        answer['squad']=list(reversed(answer['squad']))
        with self.assertRaisesRegex(ValueError,'differs from its records'):candidate(p,answer)
        self.assertEqual(self.model.state,before)
        answer['squad']=list(reversed(answer['squad']))
        image=Image.from_state(answer['state'],engine_tables.load())
        image.memory[image.DS*16+0xA91B] ^= 1
        answer['state']=image.state(engine_tables.load())
        with self.assertRaisesRegex(ValueError,'storage identity'):candidate(p,answer)
        self.assertEqual(self.model.state,before)

    def test_retained_captain_is_kept_and_removed_captain_is_cleared(self):
        from goal2.engine.original_match import Image
        p=prepare(self.model.state)
        answer=call('goal2.tests.test_best_twenty_t183a:native',p.native)
        old=set(self.model.state.starting_eleven);new=set(answer['squad'][:11])
        self.assertTrue(old&new,'fixture needs an actual retained captain choice')
        self.assertTrue(old-new,'fixture needs an actual outgoing captain choice')
        for captain,expected in ((min(old&new),min(old&new)),(min(old-new),0)):
            with self.subTest(captain=captain):
                self.model.confirm(list(self.model.state.starting_eleven),captain,self.model.state.country_tactics)
                source=copy.deepcopy(self.model.state)
                prepared=prepare(source)
                self.assertEqual(prepared.input_hash,p.input_hash,'UI captain is separate from opaque country+2F')
                result=candidate(prepared,answer)
                self.assertEqual(result.captain,expected)
                self.assertEqual(self.model.state,source)
                self.assertEqual(result.countries[4][0x2F],source.countries[4][0x2F])
                original_image=Image.from_memory_component(source.mem)
                result_image=Image.from_memory_component(result.mem)
                lo=original_image.load*16;hi=original_image.DS*16
                self.assertEqual(result_image.memory[lo:hi],original_image.memory[lo:hi],'backing code must not be replaced by sealed tables')

    def test_completed_world_prefix_is_projected_and_candidate_round_trips(self):
        from goal2.desktop.worker import play
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        from goal2.game.session_save import encode,decode
        self.model.state=play(self.model.state,self.model.template_bytes)
        before=copy.deepcopy(self.model.state)
        self.assertTrue(before.campaign.world.results)
        p=prepare(before);image=Image.from_state(p.native,engine_tables.load())
        self.assertEqual(image.rd_far(0xA923,0x26),1361+len(before.campaign.world.results))
        for row in before.campaign.world.results:
            n=int(row['fixture_id'].split(':')[1]);at=image.far(0xA92B)+8*(n-1)
            self.assertEqual(list(image.memory[at:at+2]),row['score'])
        answer=call('goal2.tests.test_best_twenty_t183a:native',p.native)
        result=candidate(p,answer)
        saved,template=decode(encode(result,self.model.template_bytes))
        self.assertEqual(saved,result)
        self.assertEqual(template,self.model.template_bytes)
        self.assertEqual(self.model.state,before)
