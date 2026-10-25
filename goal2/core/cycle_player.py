"""[designed: T123] A bounded scripted manager through original Driver keys.

This is acceptance policy, not a new rules engine. Original eligibility, assistant
selection, substitutions, takers and shootout availability remain authoritative.
[confirmed: F027/F030/F031 at archaeology 53d7ef5; genuine T114/T118/T120/#395
consumer inputs at goal2 c0c7057e] Driver choices leave guest legality authoritative.
"""
from goal2.core import views
from goal2.core.driver import DriverError
from goal2.core.screens import INSERT, RETURN

POLICY = 'g16-original-keys-owner-substitutions-v1'


class Player:
    def __init__(self, driver):
        self.driver = driver
        self.refused = None
        self.repairs = 0

    def _repair(self):
        d = self.driver
        self.repairs += 1
        if self.repairs > 32:
            raise DriverError('G16 policy exceeded 32 original lineup repairs in one round')
        rows = views.team(d.wait.state)['squad']
        cards = {r['player']: views.player_card(d.wait.state, r['player']) for r in rows}
        mem = views.Memory(d.wait.state)
        selected = mem.code_str(0x1771, 0x42A6)
        ready = mem.code_str(0x1771, 0x42AF)
        bad = next((r for r in rows if r['eleven'] and cards[r['player']]['readiness'] != selected), None)
        if bad is not None:
            replacement = next((r for r in reversed(rows) if not r['eleven'] and r['line'] == bad['line']
                                and cards[r['player']]['readiness'] == ready), None)
            if replacement is None:
                raise DriverError('G16 policy has no ready same-line reserve for the original refusal')
            if d.wait.kind == 'match-menu' and not d.stoppage():
                d.prematch_swap(bad['player'], replacement['player'])
                action = 'prematch_swap'
            else:
                result = d.substitute(bad['player'], replacement['player'])
                if not result['made']:
                    raise DriverError('Original refused G16 repair substitution: ' + str(result))
                action = 'substitute'
        else:
            # [designed; confirmed: T114 original C controls] Restore an edited
            # XI position through C; never manufacture a position byte.
            changed = next((r for r in rows if r['eleven'] and
                            cards[r['player']]['position'] != cards[r['player']]['club_position']), None)
            if changed is None:
                raise DriverError('G16 policy cannot repair this original refusal: ' + str(self.refused))
            result = d.round_position(changed['player'], 'c')
            if result.get('refused'):
                raise DriverError('Original refused the G16 club-position repair')
            action = 'restore_club_position'
        self.refused = None
        return action

    def step(self):
        """One named decision; all changes are the original's response to Driver keys."""
        d = self.driver
        with d.core.live_frames():
            if self.refused is not None:
                return self._repair()
            kind = d.wait.kind
            if kind == 'manager-menu':
                desk = views.desk(d.wait.state)
                if desk['sacked']:
                    raise DriverError('G16 reached a genuine sacking; reappointment needs a supported original route')
                self.repairs = 0
                stage = desk['stage']
                # [designed: T123; confirmed: T107 INSERT/F031] Ask the original
                # assistant for the squad while changes are allowed. A refusal
                # is dismissed by its original key, never bypassed.
                if stage not in views.FINALS_STAGES:
                    d.goto('select-squad')
                    d.press(INSERT, expect=('select-squad', 'squad-change-refused'))
                    if d.wait.kind == 'squad-change-refused':
                        d.press(RETURN, expect=('select-squad',))
                    d.to_menu()
                result = d.round_start(False)
                action = 'round_start'
            elif kind == 'match-menu' and not d.stoppage():
                result = d.kick_off()
                action = 'kick_off'
            elif kind in d.INTERVAL_KINDS or d.stoppage():
                result = d.play_on()
                action = 'play_on'
            elif kind == 'match-menu-fulltime':
                result = d.finish()
                action = 'finish'
            elif kind == 'substitution-notice':
                # A managed notice is answered by offering the original bench;
                # no legal reserve is invented. Play/EA09 decides any repair.
                result = d.notice(True)
                action = 'notice'
            elif kind in ('round-paused', 'bulletin-achievement', 'bulletin-congratulations'):
                result = d.round_continue()
                action = 'round_continue'
            elif kind == 'shootout-announcement':
                result = d.shootout_start()
                action = 'shootout_start'
            elif kind == 'shootout-order':
                order = views.shootout_order(d.wait.state, d.wait.view)
                choice = next((r for r in order['players'] if r['available'] and r['rank'] is None), None)
                if choice is None:
                    raise DriverError('Original shootout order has no available unpicked player')
                result = d.shootout_pick(choice['player'])
                action = 'shootout_pick'
            elif kind in ('set-piece-select', 'set-piece-pitch'):
                result = d.taker_key('c' if kind == 'set-piece-select' else RETURN)
                action = 'taker_key'
            elif kind == 'match-live':
                result = d.live_step()
                action = 'live_step'
            elif kind == 'match-summary-save-prompt':
                result = d.summary_done()
                action = 'summary_done'
            else:
                raise DriverError(f'Unsupported G16 decision {kind} at {d.wait.site}')
            if isinstance(result, dict) and result.get('refused'):
                self.refused = result['refused']
            return action
