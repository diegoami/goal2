# Owner substitution interaction contract

[designed: owner clarification, 2026-11-08; goal2#662] Opening the bench is distinct from a natural ball stoppage. Esc or Enter from play opens the own bench/player list. Enter on any player toggles the independent SUBSTITUTION REQUESTED state; a dedicated request/cancel button may provide the same action. No off/on player pair is queued while play is active. Leaving this bench resumes the match with the request retained or cancelled as actually acknowledged.

A natural eligible stoppage (ball out, foul or another original opportunity) holds play and shows SUBSTITUTION OPPORTUNITY. Esc and Enter accept it and open the legal bench; swaps take effect immediately through the guest. The opportunity indicator is also shown in team view and clears after each confirmed swap. Half-time swaps are immediate without requesting first.

[derived: separate guest observations] Clear the presentation indicator only after an actual confirmed swap, not on submission/refusal. Preserve guest legality and remaining allowance; do not infer a one-swap restriction or automatic resume from indicator clearing. Team lineups must reflect the acknowledged new XI. Request/opportunity timeouts and cancellation follow actual guest state, not a fabricated UI cancellation.

The assistant's earlier statement that Esc itself should set the substitution request was wrong. So was treating any opened bench as an eligible ball stoppage. T203/#662 tests the exact user keyboard path and the entire natural-opportunity lifecycle; historical harness success on another navigation path is not proof of this one.
