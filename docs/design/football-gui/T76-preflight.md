# T76 concrete acceptance details

designed: T76; derived: main planning evidence (`../../evidence/T76/preflight/README.md`, removed 2026-10-20; on branch `local`)
These requirements pin the existing task; planning mocks are not implementation
acceptance. Source baseline is accepted `f1697ef628508ac19130299194d751990ca7fa9e`.

[designed] Keep the existing twenty-row source-order `squad` table and seven
columns, its full integer UserRole IDs and availability role, existing captain
selector and tactic object names/masks/order. Add a named grouped XI and bench
board using the actual position strings, raw player-detail reading area, and a
visible draft cue. Do not interpret groups as positions on a pitch or normalize
raw attributes. Captain marking includes the word Captain. The Confirm/Discard
bar remains visible while this page scrolls; minimal page-footer support in
pages.py is in scope, with unchanged navigation/page ownership. Scoped squad
style selectors and one scenario helper avoid crowding the shared dispatcher.

[designed] The new scenario must use genuine QTest keyboard/mouse inputs and
assert focus/activation and the intended selection before evaluating results.
Country13 supplies IDs241–260: choose250–260, captain260, all eight bits255.
Compare encoded state AND save bytes before and after each draft checkbox,
tactic and captain event. Confirm publishes only validated management; Discard
recovers confirmed values. Invalid10/12-player drafts and a captain outside XI
are refused without mutation. Mark starter260 and reserve241 unavailable in an
owned generated fixture (energy0/status0x88); keep the former removable and
refuse adding the latter. Preserve the accepted eligibility guards, labels and
full-ID halftime substitution semantics. Player detail must match every named
raw field of the selected source record, including availability.

[designed] Prove active drafts survive page navigation and country preview/
Return. Actions have accessible names and are reachable by Tab/Shift-Tab;
Space operates native checkbox controls and Enter operates the focused action.
Capture initial, grouped XI/bench, selected-player detail, long names, dirty and
invalid drafts, focused controls and the persistent action bar at1440×900,
1050×780 and900×700 at1x, and900×640 at2x where available native screen requires
it. Scroll the single content region to expose all values; never accept a
screenshot of clipped text as evidence of readability. No fabricated original
art, formation, skill scale or normalized percentage.

[designed] `--negative-controls` on the squad scenario runs saved-byte controls
and restores source in finally: baseline missing new hierarchy fails; truncating
captain/full player ID above255 and premature checkbox/tactic publication must
fail intended assertions in the NEW scenario. Run the applicable retained
management and halftime regressions against those mutations too, noting actual
coverage rather than claiming a legacy test detects every new condition.
Pending halftime must be exercised independently using real worker publication
and cancellation, not simulated solely by a busy flag.

[designed] DW3 includes the named unit modules and these retained commands:
`tools/desktop-ui/prove-management.py`, `prove-friendlies.py`, `prove-pool.py`,
`prove-halftime.py`; and `tools/desktop-ui/acceptance.py --scenario management`,
`campaign-pool`, `campaign-halftime` with the verified template/data arguments.
Retain the country-selection acceptance and T75 overview scenario and controls;
run shell1x/2x for footer/navigation changes. No mutation oracle or fixture may
be weakened. Exact clean-head premerge remains mandatory after review.

[designed] Main owns final native Windows execution of the real new scenario in
fresh actual1x/2x Qt processes, with source/resource/capture/report hashes,
OS/Python/Qt identity, clean process exit and unchanged existing launcher/save
hashes. A native runtime mock establishes feasibility only. Freeze and push the
product/scenario source before requesting this run; later evidence-only commits
carry explicit byte-identity validation rather than a self-referential head
claim. SDL is not part of this page; do not start a Pygame view for screenshots.

## Blocking Windows cleanup regression (#233)

[designed: main; derived: actual Windows validation and isolated native reproduction]
Both original T76 native1x/2x attempts logged an uncaught Qt-slot WinError32 during
QuickJobs cancellation despite exit0/reportPASS. They are failure evidence, not
accepted clean cancellation. Pure-stdlib owned-process reproduction proved the
venv launcher wait returned before its actual child finished teardown: retained
child handle unsignaled and owned stderr delete failed at1.4ms; at26.7ms the
handle was signaled and delete succeeded. No persistent orphan was observed.

[designed] A one-file mechanical production fix in jobs.py may retry only Windows
PermissionError.winerror32 from its own TemporaryDirectory cleanup, with a strict
bounded budget no greater than0.5s and unchanged existing cancellation bounds.
Do not suppress errors or change worker interpreter/dependencies. Keep folder
ownership until successful cleanup; permanent sharing violations and all other
errors propagate. Retrying pending cleanup must remain possible after failure.
No model/state/save/engine/publication changes are authorized. Supporting tests
in test_desktop_quick_jobs.py and the owned squad scenario must prove transient
sharing success, bounded permanent failure, no nonsharing retry/swallow, retained
ownership/retry and encoded state/save preservation.

[designed] The real squad scenario captures uncaught Qt callback exceptions and
asserts no owned worker folder remains after Cancel. Add fail-before/pass-after
proof against the actual old cleanup behavior; a setup failure cannot count.
Native1x/2x must rerun against a newly frozen pushed checkpoint with no uncaught
exceptions and all original invariants. Main must veto raw tracebacks even if
process exits0. Preserve original native-01 byte-for-byte and label its cleanup
failure honestly; new success evidence uses a separate attempt directory.
