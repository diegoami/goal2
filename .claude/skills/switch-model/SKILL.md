---
name: switch-model
description: Change who implements and who reviews by default, and which models are blocked (harness.json, through switch-model.mjs), safely - live ids, the right login, the effort rule, the client/family detected from Codex session markers or Claude's Anthropic environment, and a one-word probe before anything is written. Use when the user wants another default implementer (the implementer subagent on sonnet, opus, haiku, fable or a model id the session's provider serves, or the main session directly) or reviewer, wants a model blocked or unblocked, when the reviewer keeps failing (exit 3, early stops, Bad Request), or before trying a new model on real reviews.
---

# /switch-model: change the defaults, or the blocked list

[designed: T24] In Codex, implementation uses native `session` or a native OpenAI
model ID. `switch-model.mjs --role implementer` writes
`implementer.defaultsByClient.codex`, preserving Claude's `implementer.default`.
`--show` detects the client; HARNESS_CLIENT=codex|claude selects it explicitly.
The Claude aliases and Anthropic endpoint rules below apply to Claude only.
Reviewer switching remains shared and refuses the current implementer family.

The roster is the owner's and changes often (CLAUDE.md "Choosing models"): it lives in `harness.json`, and
this skill is how it changes. Three things can change:
- **the implementer's default** (`implementer.default`): the model the `implementer` subagent is
  spawned on inside Claude Code, a Claude Code alias (`sonnet`, `opus`, `haiku`, `fable`) or any
  model id the session's provider serves; or `session`, the main session implementing directly
  where the provider cannot spawn one. Both run through the session's Anthropic environment, so
  under Claude `sonnet` is Sonnet and under Z.AI it is GLM-5.3 Flash (MiniMax and Kimi map it their own way); no OpenCode check or probe
  applies, and a model id is taken as given (the next run shows whether the provider honours it);
- **the reviewer's default** (`reviewer.default`): the OpenCode model that reviews unless the
  user names another at the question before a review; never the session's family;
- **the blocked list** (`blocked`): families (`deepseek`) or id fragments that never run anywhere.

The orchestrator itself is never switched here: Codex uses its native session;
Claude uses the Anthropic environment ("Choosing models" rule 0). `--show` prints
the client/family detected by the harness.

A switch is the user's decision, so you propose it and the user says yes. A one-off choice needs
no switch: the question before each implementation and review takes any option.

1. **Why.** Name the reason: a measured failure (the run logs, the measurement comments, the
   model-trials record), a cheaper or better candidate, a token pool that is out, or the user's
   request. A model that failed once on a strange task is not yet a reason (L14).
2. **What runs now.** `node tools/harness/switch-model.mjs --show`: the session's family, both
   defaults, the blocked list, the other registered models.
3. **Candidates, live** (L25), never from memory: for a reviewer, `opencode models openai`,
   `opencode models zai-coding-plan`, `opencode models opencode-go`, and so on, each with its own
   login; leave out the session's family and blocked models. For an implementer, the Claude Code
   aliases above. `--show` lists the registered reviewers, each with its note in `harness.json`.
4. **Dry run.**
   - Implementer: `node tools/harness/switch-model.mjs --role implementer --model sonnet --dry-run`
     (an alias, a model id, or `session`).
   - Reviewer, with a probe: `node tools/harness/switch-model.mjs --role reviewer --model PROVIDER/ID --probe --dry-run`.
     It checks the id against OpenCode's list in the scripts' data directory (exit 3: give the
     user the login command it prints); the effort, unless `--variant` gives one, is `high` for
     a light model and `low` (else `medium`, else the lowest OpenCode offers) for a heavy one
     (L54), `max` refused; it refuses the session's family and a blocked model; the probe is one
     billed one-word call at that effort.
   - Blocked list: `node tools/harness/switch-model.mjs --block <family or id fragment> --dry-run`,
     or `--unblock`. Blocking the default reviewer is refused until the reviewer is switched.
5. **Ask.** Show the user the before and after lines (and the probe's time), with your
   recommendation. Switch only on their yes.
6. **Switch.** Run the same command without `--dry-run` (and without `--probe`, which already
   passed). Then commit `harness.json` on `main` with the reason (and the probe) in the message
   (L6, L25). Keep the old model's entry: the question before a review can still name it.
7. **Watch the first run** on the new default: the log's tail and, for a reviewer, the posted
   review. Afterwards, add a line to the model-trials record. Switch back the same way if it fails.

Exits: 0 switched (or shown, or a dry run); 1 refused (the family rule, the blocked list, or a
taken name); 2 usage; 3 OpenCode, the login or the probe failed, and nothing was written.
