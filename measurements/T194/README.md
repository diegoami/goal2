# T194 actual-match selection

Only three class decorators change. `before.log` fails because40 full-match scenarios remain active with GOAL2_SLOW=0. `fast-after.log` excludes exactly those40; `slow-after.log` selects all40. Four HomeSide/Boundary checks stay active. `body-identity.json` proves every existing function and class body unchanged after removing class decorators from the AST comparison. No scenario/assertion/case/fixture/seed/timeout is removed or changed. This probe inspects discovery; it does not play a new original/reference match.

Existing actual-match validation is preserved in614 codeheadab8484b4 defaultFAST194/194 (the affected T167/T180 classes pass in that run) and T192 accepted8230e472 preparedFAST; the only candidate changes are decorators. Original logs are retained in their task measurements/CI, with no relabelled failures. Explicit slow selection still enables the original complete scenarios. Full suites remain integrated-milestone checks underT189.

Model: inherited Codex GPT-6 family; exact variant unavailable.
