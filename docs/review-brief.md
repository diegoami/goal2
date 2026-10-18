# The review brief's own sections

Every review brief carries these two sections, in full, after the numbered block of
`process.md` §5 (or, in the review profile, after the brief's numbered lines). The reviewer reads
the brief in another file, so paste them; never point to this one. Write "Blocking means" for the
task; paste the second section as it is. (L47, L49)

[designed: #226; L115] When a brief includes a task or supplementary quotation, keep its full
literal text and put it inside a text fence longer than every fence it contains (for example,
four backticks around a task with triple-backtick blocks). This keeps source-relative links in the
quotation from being resolved as links in the generated root brief. Stage every author log the
review cites in the review worktree's own ignored `.cache`; never search sibling worktrees for a
missing file.

[designed: #204] For an issue-based task, put every current review target assertion and
reviewer instruction before the exact top-level heading `# Issue #156 task contract`
(substitute a positive canonical decimal issue ID, without leading zeroes). Paste the complete
issue contract and historical notes after it, inside text fences longer than any quoted fences.
Target extraction stops at this heading only outside backtick or tilde fences; quoted examples,
arbitrary Evidence/Notes/Issue headings and malformed IDs do not end target validation. Existing
`# T<nn>` task-title handling remains unchanged. Keep actual current targets before the boundary;
this boundary separates historical evidence, never repairs a mismatched review target.

```text
## Blocking means

Any one is enough; a blocking finding means rework, never approve.
1. A Done-when line fails, or cannot be run as written.
2. What this task protects can be got past: <name it: the guard, check, permission, invariant,
   rule value or file this task exists to protect>. A bypass you proved is blocking, even when it
   looks like an edge case. Never "follow-up hardening" or "outside the threat model" unless the
   task says so; if it does, quote the line. (L47)
3. Behaviour the task forbids, or behaviour nobody asked for, inside a file the task requires. (L44)
4. <project-specific items: a constant with no evidence, a test that passes with the behaviour
   deleted, a status written into a document>
Not blocking: wording, style, and defects in code the PR did not change: file those as follow-ups.
When unsure, say how likely the problem is. Rate it blocking only if it is likely and would get
past what the task protects; otherwise it is a follow-up. (L53)

## Report every blocking finding in this one review

This review is your only pass before the author fixes. Do not stop at the first blocking
finding: finish reading the whole diff and the task file, check every Done-when line and
every item under "Blocking means", and report all blocking findings together.

- Before you write the verdict, make one last pass over the full diff for anything you have
  not yet rated, and say "Final pass done" as the last line before the verdict.
- Number the findings R1, R2, … in order of severity. A finding you held back because an
  earlier one was already blocking is a review defect: if two problems share a cause, list
  both and say so.
- Do not rely on a later round. The author fixes everything you list, and the next review
  checks those fixes and new code only, not anything you saw but did not report.
- If you ran out of time or context before covering the whole diff, say which files or
  sections you did not cover. Do not approve in that case.
```

[designed: T73] For an explicitly selected direct Claude backend, main also supplies
the trusted external policy and its required commands. Audit the retained local
base/head inventory and every diff chunk; print the requested exact PR/head/base
identity, `COVER <inventory-id>: audited <concrete scope/result>` for each item,
and `CONTROL: ran <trusted command> -> <observed substantive result>`. Run every
DW yourself and distinguish parent/synthetic evidence from your own execution.
Planned forbidden canaries must be denied; a denied required check blocks approval.
Do not post, merge, change routing/permissions or launch a nested model.
