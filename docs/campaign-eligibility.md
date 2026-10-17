# Campaign availability and fixture status

[derived: F027 sections2/6/7/9, goal2-archaeology
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb`] Player status is byte+0x10.
The one-based set helpers decrement their element argument before shifting:
elements3/4/5/6/8 are masks0x04/08/10/20/80 (substituted off, carried booking,
booked this match, sent off, suspended). Availability3216 requires signed
positive energy and clear elements8/6/3. A carried booking or booking alone
is not an availability refusal. F027 is a proposed static reading with isolated
original-routine probes; it does not establish full fixture-end parity.

[designed: T44; derived: 3216] Campaign preview and kickoff share the same
availability gate. An unavailable managed starter blocks Play with a reason;
management refuses an invalid eleven atomically and allows the human to replace
players. Unavailable selected players can be removed from the browser draft;
unavailable unselected players cannot be added. Available computer squad words
are filtered before the existing selection policy, and fewer than eleven cause
an explicit refusal. Standalone friendly behavior retains its prior path.
The separate CPU age/ability policy bug is recorded in #145 and folded into
T46 #106; availability filtering does not correct that ranking policy.

[derived: B27F/B7FA, F027] Every nonzero squad word of both played fixture
countries receives B27F once, including unused bench. Clear an old suspended
bit; a sent-off bit creates a new ban and clears sent-off. A booking becomes
a carried booking when none was carried; if one was carried, create a ban and
clear the carried booking. Clear the match booking. Other bits and all other
record bytes pass through. A kind0 slot never plays through B7FA and serves no
ban. The active scheduled friendly is kind1 and does serve bans. Other countries'
status does not expire when these two countries play; calendar days, reads,
Save and Load do not serve bans.

[derived: B27F; designed: T44] The quick campaign runner completes the pure
status operation after energy/confidence processing. B27F uses no RNG and
changes only the current player's status, so this commutes with other players'
energy/confidence calls. The adapter refuses a second completion in the same
simulation. The existing fixture/token guard prevents a second published
transition, and all modified records and fixture history publish as one candidate.
A failure discards the candidate. The `campaign_energy` marker adds an
`eligibility` completion receipt without changing earlier fields or save format.

[derived: F018/F027; designed: T44] Injuries use the existing energy transition,
not a new timer: zero energy can recover through the actual ordered3651/3558
branch chosen for the fixture. Signed-negative energy is also unavailable, but
is shown as unavailable energy rather than asserted to be the zero-energy injury.
No healing occurs from rendering, selecting, saving or loading a player.
Browser counters derive zero/one carried bookings and zero/one ban fixtures
from the existing bits; no invented duration is stored. Full player records
remain in the existing explicit save schema. A saved transition resumes with
identical status, recovery, RNG and fixture history.

[designed: T45] Current campaigns use twenty squad and eighty disjoint reserve
identities. The reserve B27F caller lives in campaign_pool.py. This adapter consumes current player/event state; the friendly quick
runner produces no foul events. Tests inject explicit events/state without a
production incident endpoint. [designed: T51] Original competitive events and the full original tail pass
through the competitive adapter; an
original watched-result publisher must not reapply Python status/recovery over
original returned records. No complete original fixture-tail parity is claimed.

```sh
python3 -m unittest goal2.tests.test_campaign_eligibility -v
python3 tools/browser-ui/prove-campaign-eligibility.py
```

[designed: T45] The disjoint eighty-reserve BA4E prefix now runs before the current
squad operations described above. See [campaign-pool.md](campaign-pool.md) for
ordered recovery/confidence/status calls, save membership and remaining boundaries.
Standalone friendlies and original watched-result publication do not run this prefix.
