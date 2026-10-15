# Browser UI: from prototype to playable friendlies

[designed: owner, 2026-10-15] Use the simplest clear browser interface rather than a custom text UI. Connect ordinary controls to the existing Python game. Match-engine visualization comes later. T34 established the dashboard and squad layout with explicitly fictional sample data; it did not connect gameplay.

The sequence below makes each integration slice independently reviewable. Task state remains in GitHub labels; this document records scope and dependencies.

| Task | Player-facing outcome | Difficulty | Depends on |
| --- | --- | --- | --- |
| [T35](tasks/T35.md) · [#88](https://github.com/diegoami/goal2/issues/88) | Start the Python browser server, choose any of the 128 countries and view its actual squad and resolved opponent. | Medium | T34 |
| [T36](tasks/T36.md) · [#89](https://github.com/diegoami/goal2/issues/89) | Confirm an eleven, captain and tactics into GameState; review the actual next matchup. | Medium | T35 |
| [T37](tasks/T37.md) · [#90](https://github.com/diegoami/goal2/issues/90) | Explicitly play a complete friendly, read named results and goals, then play another using retained state. | Medium | T36 |
| [T38](tasks/T38.md) · [#91](https://github.com/diegoami/goal2/issues/91) | Save and resume the same session through browser controls with deterministic continuation. | Medium | T37 |

[designed] T37 is the browser-playable friendly milestone; T38 adds persistence. This is the existing friendly game in a usable browser interface, not an implementation of the competition calendar or four-year cycle. Existing engine assumptions remain visible where relevant.

[designed] Keep the existing Python GameState, matchup resolver, full-friendly runner and session-save format authoritative. A small Python standard-library server serves packaged HTML/CSS/JavaScript and explicit JSON actions; no frontend framework or production dependency is needed. Use a documented single-session model, with localhost as the default bind address and an explicit host option for access from another computer. Static sample preview and live gameplay have distinct launch commands.

[designed] Task files define scope and dependencies; their existence does not start implementation. Record the owner’s implementer/reviewer choices before dispatch, retaining any explicit batch choice for its stated tasks.

[designed: owner, 2026-10-15] Luna High implements and MiniMax M3 reviews T35–T38. T37/T38 estimates are medium because they reuse the existing runner and session format; their main risks are integration, duplicate requests and failure handling.

[designed] Campaign rules, recovery, competitions and cycle rollover are sequenced in the [full-cycle backlog](full-cycle-backlog.md). Plan match visualization separately against available engine events and archaeological evidence; do not invent ball positions or present a result summary as a live visual engine. Multiple managers remain a later game milestone.
