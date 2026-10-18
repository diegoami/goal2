# Bounded implementation sequence

[designed: owner #182, 2026-10-18] These six contracts are proposals for main-session
retriage, not a runtime implementation or dispatch. The owner authorized native
Luna High for Easy, Sol Low for Medium and Sol Medium for Hard tasks, with
independent MiniMax M3 reviews; no model is silently substituted. No slice here is
classified Easy because each crosses existing stateful UI interactions. A changed
scope/difficulty needs the main session's retriage before dispatch.

| Contract | Small useful outcome | Difficulty / implementer | Merge after |
| --- | --- | --- | --- |
| [T74](../../tasks/T74.md) | Shared Qt visual tokens, shell, navigation, existing save/resume access | Medium / Sol Low | Accepted #182 plan, T70, T71, T66, T80 |
| [T75](../../tasks/T75.md) | Country selection identity and overview, preview/active coherence | Medium / Sol Low | T74, #181/PR183 |
| [T76](../../tasks/T76.md) | Squad/bench/player detail and eight-tactic draft workspace | Hard / Sol Medium | T75, T47, #164 |
| [T77](../../tasks/T77.md) | Focused reserve search/exchange page, same pool policy | Medium / Sol Low | T76, T71 |
| [T78](../../tasks/T78.md) | Fixture/result scoreboard and existing standings presentation | Medium / Sol Low | T75, T49, T51 |
| [T79](../../tasks/T79.md) | Shared Qt/Pygame match presentation and transition | Hard / Sol Medium | T74, T76, T78, T66 |

[designed] Every row uses MiniMax M3 review. Child issues are intentionally
unassigned; main creates them from these bodies after accepting/retriaging this
plan. Parent #182 remains open for runtime deliverable4. The task index lists
contracts, while GitHub labels own execution status.

[designed] Suggested limited fan-out: T74 then T75; after that, T76 and T78 may
run together in separate page modules. T77 follows the squad identity/control seam.
T79 follows both T66 and the accepted scoreboard. Preserve all task worktrees.
No parallel task may overwrite another's `window.py`: T74 creates page boundaries,
T75/T76/T78 own their page modules, and the main session sequences minimal shell
bindings. Ordinarily merge accepted main before shell changes; re-read T66's accepted head before touching watched integration; if its
API differs, amend the proposed contract during preflight rather than guessing.

[designed] Per-slice preflight must turn proposed `redesign.py` scenarios into
failing assertions on the then-current main and a temporary positive control,
retaining saved contents when undoing any mutation. Tests compare real Qt events
and existing state/save encodings; they do not accept screenshots or a CSS class
as proof of behavior. Existing country-selection, management, pool, halftime,
standings, competitive and T66 proof tools remain regression gates where relevant.
The task's new scenario must fail when its claimed UI/guard is removed; old green
tests do not prove new layout behavior. Commands with `<verified-…>` placeholders
are future contracts, not runnable claims from this planning PR.

[designed] Real Windows evidence is a gate in every runtime slice. If Windows
access is unavailable, stop/report that Done-when rather than substituting browser
or offscreen results. Retain launcher/saves and worktrees; use newly generated
screenshots of the rebuild only, with original-resource hashes instead of bytes.
No redesign slice may smuggle rule changes, schedule generators or original assets.

[designed: main preflight903312e] [T80](../../tasks/T80.md) separately supplies
live competitive Play before T50 qualifying progression. T78 can style validated
saved results independently; its controls consume accepted capability checks,
without pretending that a competitive result adapter makes live Play or Watch
available. Main sequences T66/T80 integration before conflicting Qt bindings.
