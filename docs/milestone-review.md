# Milestone reviews

[designed: owner, 2026-10-20, after Geoclick2027's release reviews] A milestone review is one big,
independent review of everything merged since the previous milestone. It is **not run by the
harness** and no session starts it: the main session gives the owner the prompt and the owner starts
a reviewer CLI with `tools/milestone_review.sh`, on whatever tool and model they pick (owner,
2026-10-29). It is the only mandated review (CLAUDE.md rule 4): PRs merge on their checks between
milestones, so the milestone issue lists the PRs merged since the last milestone without a review.

## When

A milestone is a coherent set of merged work: a queue milestone in `docs/plan.md`, a playable
build, or whenever the owner calls one. It is marked by an annotated tag `m<n>-<slug>` (for
example `m3-campaign-ui`) on **exactly the reviewed commit** of `main`.

## How it happens

1. The main session proposes a milestone (or the owner calls one) and opens a **milestone issue**,
   labelled `milestone-review`, whose body carries these lines, exactly:

   ```text
   **Milestone**: m<n>-<slug>
   **Candidate**: `<full 40-character SHA on main>`
   **Previous milestone**: `<previous tag, or a full SHA for the first one>`
   ```

   then the PRs merged since (`gh pr list --state merged --search "merged:>=<date>"`), the checks
   run on the candidate (`python3 tools/check_premerge.py --expected-head <sha> --slow`: every
   game test, the slow ones included), what changed in plain words, the claims to verify with `file:line`, and the known owner
   decisions (not defects). From then on `main` takes only fixes for the milestone's findings.
   [designed: owner, 2026-10-21] The body **ends with the reviewer's prompt**, ready to paste:

   ````text
   ## Prompt for the reviewer
   In a clean checkout of goal2: `git fetch origin && git checkout --detach <candidate SHA>`,
   then start OpenCode there and choose the agent `milestone-reviewer` (Tab), on the model you want.
   Paste:

   ```text
   Review the goal2 milestone on issue #<n>, as your instructions say. Start with: gh issue view <n>.
   ```
   ````

   The prompt is short because the agent file (`.opencode/agents/milestone-reviewer.md`) carries
   the reviewer's instructions and this issue carries the facts.
2. The owner starts the review: from an OpenCode session with the issue's prompt (above), or with
   the launcher, from any clean checkout of this repository:

   ```bash
   tools/milestone_review.sh <issue> opencode openai/gpt-6.1-sol#low   # OpenCode
   tools/milestone_review.sh <issue> claude opus                        # Claude Code CLI
   tools/milestone_review.sh <issue> codex gpt-6.1-sol                  # Codex CLI
   ```

   The script reads the candidate from the issue, checks the checkout out at it (detached; it
   refuses when tracked files are dirty) and runs the CLI in the foreground with the reviewer's
   instructions, `.opencode/agents/milestone-reviewer.md`. No worktree, no systemd unit, no
   family rule: the owner picks the model, and a different family than the implementers' is
   recommended, not required.
3. The reviewer posts to GitHub itself: **one issue per reproduced finding** (labels `review` and
   `bug`, `tests`, `design`, `cleanup` or `documentation`), and **one verdict comment** on the
   milestone issue, AGREE or BLOCK. Nothing is pasted back.
4. BLOCK: the MUST-FIX findings are fixed in ordinary PRs, the issue's Candidate line moves to the
   new `main` commit, and the review runs again. After a third BLOCK the decision goes to the
   owner. AGREE: the main session tags the reviewed SHA
   (`git tag -a m<n>-<slug> <sha> -m "<issue URL>" && git push origin m<n>-<slug>`), closes the
   issue, and SHOULD findings stay open as ordinary issues. The owner's playtest accompanies the
   review; the owner may also tag without a review, and the issue records that.

## Severities

- **MUST-FIX**: a defect in this milestone's changes that must be fixed before the tag (a wrong
  game outcome, a fidelity break against the vendored model, a crash, a save that does not load, a
  check that passes without testing what it claims).
- **SHOULD**: worth fixing, not blocking.
- **OUT OF SCOPE**: real, but not caused by this milestone's changes.
