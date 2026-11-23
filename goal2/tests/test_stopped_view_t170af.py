"""[designed: T170af/#822] Driver owns every current read and its lifetime."""
import copy
from dataclasses import FrozenInstanceError
import threading
from types import SimpleNamespace
import unittest

from goal2.game.native_driver import NativeMatchDriver
from goal2.game.stopped_view import StoppedMatchView
from goal2.tests.test_native_driver_t170ac import Owner,event
from goal2.tests.test_stopped_snapshot_t170ae import sample


def stopped():
    packet,data=sample();owner=Owner();owner.managed_country=7
    owner.packet.update(events=[event('decision',copy.deepcopy(data))],decision=3)
    return owner,NativeMatchDriver(owner),packet,data


def respond(owner,packet):
    return owner.reply('stopped_preview',**{k:copy.deepcopy(v) for k,v in packet.items() if k not in ('request','action')})


class Controls(unittest.TestCase):
    def test_held_read_is_single_flight_and_never_pulls_or_defaults(self):
        owner,d,p,data=stopped();before=(d.events,d.frames,d.shown_count,d.painted_sequence)
        self.assertIsNone(d.stopped_view);d.request_view();d.set_held(True)
        self.assertEqual(owner.sent,[('stopped_preview',{'decision':3})])
        with self.assertRaises(ValueError):d.request_view()
        with self.assertRaises(ValueError):d.answer({})
        with self.assertRaises(ValueError):d.resume()
        respond(owner,p);self.assertIsNone(d.tick(0));view=d.stopped_view
        self.assertIsInstance(view,StoppedMatchView);self.assertEqual(view.snapshot.decision,3)
        self.assertEqual(d.status,'decision');self.assertEqual(d.waiting['event']['data'],data)
        for _ in range(3):self.assertIsNone(d.tick(99))
        self.assertEqual(len(owner.sent),1);self.assertEqual((d.events,d.frames,d.shown_count,d.painted_sequence),before)
        d.answer({});self.assertIsNone(d.stopped_view)
        self.assertEqual(owner.sent[-1],('answer',{'decision':3,'answer':{}}))

    def test_refusal_is_repairable_and_answer_attempt_invalidates_view(self):
        owner,d,p,data=stopped();d.request_view();owner.number+=1
        owner.queue.put(('season_error',dict(request=owner.number,error='pure read refusal',lost=False)))
        d.tick(0);self.assertEqual(d.status,'decision');self.assertIsNone(d.stopped_view)
        d.request_view();respond(owner,p);d.tick(0);self.assertIsNotNone(d.stopped_view)
        d.answer({'edit_only':True,'tactics':{1:True}});self.assertIsNone(d.stopped_view)
        owner.number+=1;owner.queue.put(('season_error',dict(request=owner.number,error='pure answer refusal',lost=False)))
        d.tick(0);self.assertEqual(d.waiting['decision'],3);self.assertIsNone(d.stopped_view)
        d.request_view();respond(owner,p);d.tick(0);self.assertIsNotNone(d.stopped_view)
        d.close();self.assertIsNone(d.stopped_view);self.assertTrue(owner.closed)

    def test_mismatched_reply_loss_and_close_invalidate_without_replay(self):
        for corrupt in ('request','decision','data','country','hash','death','lost'):
            owner,d,p,data=stopped();d.request_view();d.set_held(True)
            if corrupt=='death':owner.queue.put(('death','lost'))
            elif corrupt=='lost':
                owner.number+=1;owner.queue.put(('season_error',dict(request=owner.number,error='lost',lost=True)))
            else:
                got=respond(owner,p)
                if corrupt=='request':got['request']+=1
                elif corrupt=='decision':got['preview']['decision']+=1
                elif corrupt=='data':got['data']['eleven'].reverse()
                elif corrupt=='country':got['preview']['managed_country']=8
                else:got['preview']['state_hash']='bad'
            d.tick(0);self.assertEqual(d.status,'lost',corrupt);self.assertTrue(owner.closed)
            self.assertIsNone(d.stopped_view);d.tick(99);self.assertEqual(len(owner.sent),1)
        owner,d,p,data=stopped();d.request_view();d.close();respond(owner,p);d.tick(0)
        self.assertIsNone(d.stopped_view);self.assertEqual(d.status,'closed')

    def test_phase_thread_and_new_decision_invalidate(self):
        owner=Owner();owner.managed_country=7;d=NativeMatchDriver(owner)
        with self.assertRaises(ValueError):d.request_view()
        owner,d,p,data=stopped();errors=[]
        def other():
            for call in (d.request_view,lambda:d.stopped_view):
                try:call()
                except RuntimeError:errors.append(True)
        t=threading.Thread(target=other);t.start();t.join(1);self.assertEqual(len(errors),2)
        d.request_view();respond(owner,p);d.tick(0);old=d.stopped_view
        d.answer({});owner.reply('answer');d.tick(0)
        owner.batch(events=[event('decision',data)],decision=4,total=4);d.tick(0)
        self.assertIsNone(d.stopped_view);self.assertEqual(old.snapshot.decision,3)

    def test_ready_view_loss_under_hold_and_pending_playback_remains_frozen(self):
        owner,d,p,data=stopped();d.request_view();respond(owner,p);d.tick(0);d.set_held(True)
        owner.queue.put(('death','lost while covered'));d.tick(0)
        self.assertIsNone(d.stopped_view);self.assertEqual(d.status,'lost');self.assertTrue(owner.closed)
        from goal2.tests.test_season_pitch_t170ab import frame
        owner=Owner();d=NativeMatchDriver(owner);d.tick(0);d.set_held(True)
        owner.batch(frames=[frame(0,3)]);d.tick(10)
        self.assertEqual(d.frames,[]);self.assertIsNone(d.frame)
        d.set_held(False);self.assertEqual(d.tick(10)['sequence'],0)

    def test_wrong_read_refusal_request_fails_closed(self):
        owner,d,p,data=stopped();d.request_view();d.set_held(True)
        owner.queue.put(('season_error',dict(request=owner.number+2,error='wrong reply',lost=False)))
        d.tick(0);self.assertEqual(d.status,'lost');self.assertIsNone(d.stopped_view)


class Decoder(unittest.TestCase):
    def test_native_records_identity_only_and_detached_display_data(self):
        owner,d,p,data=stopped();d.request_view();respond(owner,p);d.tick(0);view=d.stopped_view
        identities=SimpleNamespace(player_renames={2:'Owner'},manager_name='Manager',
            players=[b'stale']*3061,countries=[b'stale']*129,managed_squad=[99]*20,campaign='stale')
        state=view.display_state(identities)
        self.assertEqual(tuple(state.players),view.players);self.assertEqual(tuple(state.countries),view.countries)
        self.assertEqual(state.managed_squad,list(range(1,21)));self.assertEqual(state.player_renames,{2:'Owner'})
        self.assertIsNone(state.campaign);self.assertEqual(state.extra_squad,[])
        state.players[2]=b'changed';state.countries[8]=b'changed';state.player_renames[2]='Changed'
        self.assertEqual(view.record(2),bytes.fromhex(data['player_records'][1][1]))
        self.assertEqual(view.opponents,tuple(range(21,41)));self.assertEqual(identities.player_renames,{2:'Owner'})
        self.assertEqual(view.display_state().player_renames,{})
        with self.assertRaises(FrozenInstanceError):view.squad=()
        with self.assertRaises(TypeError):view.players[2]=b'bad'
        with self.assertRaises(ValueError):view.record(True)
        self.assertEqual(view.marking_word(2),0);self.assertFalse(view.available(12))
        self.assertEqual(view.team_context,data['team_context'])


if __name__=='__main__':unittest.main()
