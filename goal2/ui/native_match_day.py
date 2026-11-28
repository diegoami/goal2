"""[designed: T170at/#869] One explicit retained native match-day entry."""

from PySide6.QtCore import QObject, QTimer

from goal2.game.native_season import NativeSeasonOwner
from goal2.game.season import canonical_hash
from goal2.game.season_publication import SeasonCampaign, SeasonPublication
from goal2.ui.cells import Cells
from goal2.ui.held_prematch import HeldPrematchFlow
from goal2.ui.native_pitch import NativePitchScreen
from goal2.ui.screen import Screen


class NativeMatchOpening(Screen):
    GRID = True
    title = 'Native match'
    escape_text = 'Cancel'

    def __init__(self, day):
        super().__init__(day.window)
        self.closing = day.close
        body = Cells(90, 25, 'nativeMatchOpening')
        self.body_layout.addWidget(body, 1)
        self.status = body.text('Opening the native match…', 'h1', 0, 0, 90)

    def escape(self):
        self.closing()
        self.window_.pop()


class NativeMatchDay(QObject):
    """One explicit route action with a single reply consumer at every phase."""

    def __init__(self, window, model, state, *, on_boundary, on_failure, on_goal,
                 on_tournament, on_stats, watch=None, show_bulletins=False,
                 show_round_results=False, round_number=None, campaign=None, engine_owner=None):
        super().__init__(window)
        if not all(callable(callback) for callback in
                   (on_boundary, on_failure, on_goal, on_tournament, on_stats)):
            raise ValueError('Native match day requires explicit owner callbacks.')
        if watch is not None and type(watch) is not bool:
            raise ValueError('The watch preference must be a boolean or None.')
        if type(show_bulletins) is not bool:
            raise ValueError('The bulletin preference must be a boolean.')
        if type(show_round_results) is not bool:
            raise ValueError('The round results preference must be a boolean.')
        if round_number is not None and (type(round_number) is not int or round_number < 1):
            raise ValueError('The displayed round number must be a positive integer or None.')
        if campaign is not None and (not isinstance(campaign, SeasonCampaign)
                                    or campaign.canonical_hash != canonical_hash(state)):
            raise ValueError('The native match day must start from its campaign state.')
        country = model.state.managed_country
        self.window = window
        self.model = model
        self.on_boundary = on_boundary
        self.on_failure = on_failure
        self.on_goal = on_goal
        self.on_tournament = on_tournament
        self.on_stats = on_stats
        self.watch = watch
        self.show_bulletins = show_bulletins
        self.show_round_results = show_round_results
        self.round_number = round_number
        self.results = None
        self.round_screen = None
        self.bulletin = None
        self.preferences = None
        self.entry_observation = None
        self.publication = SeasonPublication(campaign) if campaign is not None else None
        self.campaign_revision = campaign.revision if campaign is not None else None
        self.phase = 'opening'
        self.prematch = None
        self.pitch = None
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.poll)
        owner = model if engine_owner is None else engine_owner
        self.native = NativeSeasonOwner(owner, state, frames=True, post_match_review=True)
        if self.native.managed_country != country:
            self.native.close()
            raise ValueError('The identity model belongs to another native country.')
        try:
            self.opening = window.push(NativeMatchOpening(self))
        except Exception:
            self.native.close()
            raise
        window.destroyed.connect(self.close)
        self.timer.start()

    def poll(self):
        if self.phase in ('closed', 'failed', 'finished'):
            return
        try:
            if self.phase in ('opening', 'advancing'):
                status = self.native.poll()
                if status == 'lost':
                    self.fail(self.native.message)
                elif self.phase == 'opening' and status == 'boundary':
                    self.native.take_observations()
                    self.phase = 'advancing'
                    self.native.advance()
                elif status == 'prematch':
                    if self.show_round_results and self.window.current() is not self.opening:
                        return
                    self.entry_observation = self.take_observation()
                    if self.show_round_results:
                        self.open_round_results()
                    else:
                        self.open_prematch()
                elif status in ('boundary', 'terminal'):
                    self.deliver_boundary()
            elif self.phase == 'prematch' and self.native.status == 'lost':
                self.fail(self.prematch.message)
            elif self.phase == 'resuming':
                driver = self.pitch.controller.driver
                if driver.status == 'resumed':
                    self.deliver_boundary()
                elif driver.status == 'complete':
                    self.completed(self.pitch)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            self.fail(str(exc))

    def open_round_results(self):
        from goal2.game.native_round_view import NativeRoundResults
        from goal2.ui.s14_round import RoundScreen

        self.results = NativeRoundResults(self.entry_observation, self.native.fixture,
                                          self.model.goaldat.country_names, self.round_number)
        self.phase = 'before_results'
        self.round_screen = self.window.push(RoundScreen(self.window, self.results.before, self.finish_before_results))

    def leave_results(self, phase):
        if self.phase != phase or self.window.current() is not self.round_screen:
            return False
        self.window.pop()
        self.round_screen = None
        return True

    def finish_before_results(self):
        if self.leave_results('before_results'):
            try:
                self.open_prematch()
            except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                self.fail(str(exc))

    def open_prematch(self):
        native = self.native
        self.prematch = HeldPrematchFlow(
            self.window, self.model, native.controller, native.fixture, native.replies,
            on_handoff=self.handoff, on_close=lambda _: self.close(),
            on_tournament=self.on_tournament, on_stats=self.on_stats, watch=self.watch,
        )
        self.phase = 'prematch'
        self.prematch.open()

    def handoff(self, flow, packet, preferences):
        try:
            if self.phase != 'prematch' or flow is not self.prematch or self.opening not in self.window.stack:
                raise ValueError('Unexpected native pitch handoff.')
            connection = self.native.handoff()
            if connection.packet != packet:
                raise ValueError('Native first-packet identity changed.')
            pitch = NativePitchScreen(
                self.window, self.model, self.native, connection=connection,
                on_decision=self.unexpected_stop, on_goal=self.on_goal,
                on_complete=self.completed, on_failure=lambda _, message: self.fail(message),
                half_time_controls=True, choice_controls=True, pause_controls=True,
                opportunity_controls=True, substitution_controls=True, extra_time_controls=True,
            )
            if preferences['watch'] is False:
                pitch.quick_result()
            self.preferences = dict(preferences)
            # The pre-match pages above this flow's opening page own no lease after handoff.
            while self.window.current() is not self.opening:
                page = self.window.stack.pop()
                self.window.page.removeWidget(page)
                page.deleteLater()
            self.pitch = self.window.push(pitch)
            self.phase = 'playing'
        except (IndexError, KeyError, RuntimeError, TypeError, ValueError) as exc:
            self.fail(str(exc))

    def unexpected_stop(self, screen, waiting):
        context = waiting['event']['data'].get('context')
        raise ValueError(f'Unexpected native stopped context: {context}')

    def completed(self, screen):
        if screen is not self.pitch:
            raise ValueError('Native completion belongs to another pitch.')
        self.phase = 'complete'
        screen.set_enter('Resume round', self.resume)

    def resume(self):
        if self.phase != 'complete' or self.window.current() is not self.pitch:
            return
        self.pitch.resume_native()
        self.phase = 'resuming'
        self.pitch.set_enter('', lambda: None)

    def take_observation(self):
        observations = self.native.take_observations()
        if len(observations) != 1:
            raise ValueError('Native match day expected one verified observation.')
        return observations[0]

    def deliver_boundary(self):
        if (self.show_bulletins or self.show_round_results) and self.window.current() is not (self.pitch or self.opening):
            return
        observation = self.take_observation()
        self.timer.stop()
        if self.show_round_results and self.open_boundary_results(observation):
            return
        self.show_boundary(observation)

    def open_boundary_results(self, observation):
        from goal2.game.native_round_view import completed_round_results
        from goal2.ui.s14_round import RoundScreen

        if self.results is None:
            before = completed_round_results(observation, self.model.goaldat.country_names, self.round_number)
            if not before['results']:
                return False
            after = None
        else:
            before = self.results.before
            after = self.results.after(observation)
        self.phase = 'after_results'
        self.round_screen = self.window.push(RoundScreen(
            self.window, before, lambda: self.finish_after_results(observation),
            after=after, onward_text='Continue round'))
        return True

    def finish_after_results(self, observation):
        if self.leave_results('after_results'):
            try:
                self.show_boundary(observation)
            except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                self.fail(str(exc))

    def show_boundary(self, observation):
        if self.show_bulletins:
            from goal2.game.bulletin_view import native_bulletins
            from goal2.ui.s05_bulletin import BulletinScreen

            packets = (self.entry_observation, observation) if self.entry_observation is not None else (observation,)
            pages = native_bulletins(*(packet['observation'] for packet in packets))
            if pages:
                self.phase = 'bulletin'
                self.bulletin = self.window.push(BulletinScreen(
                    self.window, pages, lambda: self.finish_bulletin(observation)))
                return
        self.finish_boundary(observation)

    def finish_bulletin(self, observation):
        if self.phase == 'bulletin' and self.window.current() is self.bulletin:
            self.window.pop()
            self.bulletin = None
            self.finish_boundary(observation)

    def finish_boundary(self, observation):
        if self.phase in ('publishing', 'finished', 'failed', 'closed'):
            return
        self.phase = 'publishing'
        try:
            if self.publication is not None:
                if self.publication.campaign.revision != self.campaign_revision:
                    raise ValueError('The campaign changed while the native round was open.')
                self.publication.complete_native(self.native, observation)
            self.phase = 'finished'
            self.on_boundary(self, observation)
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            self.fail(str(exc))

    def fail(self, message):
        if self.phase in ('failed', 'closed'):
            return
        self.close()
        self.phase = 'failed'
        self.opening.status.setText(message or 'The native match could not continue.')
        self.on_failure(self, message)

    def close(self, *_):
        if self.phase in ('closed', 'failed'):
            return
        self.phase = 'closed'
        self.timer.stop()
        if self.publication is not None:
            self.publication.cancel()
        if self.prematch is not None:
            self.prematch.close()
        if self.pitch is not None:
            self.pitch.closing()
        if self.round_screen is not None:
            self.round_screen.timer.stop()
        self.native.close()
