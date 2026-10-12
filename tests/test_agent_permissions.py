"""The OpenCode reviewer's outside-the-worktree grants (the owner, 2026-10-11): all of /tmp is open
to it, so a model's loose scratch file there no longer ends a run with nothing posted
(isle-wars-archaeology d30a137 hit it three times); every other path outside the worktree stays
rejected. The reviewer is the one OpenCode agent: the main session or a Claude agent implements
(CLAUDE.md "Choosing models", 2026-10-11)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# the one grant outside /tmp: the goal2-archaeology checkout tools/check_provenance.py reads
# (GOAL2_ARCHAEOLOGY's default sibling checkout), the folder and what is in it
BUNDLE = ("~/projects/goal2-archaeology", "~/projects/goal2-archaeology/*")


def grants(agent):
    """The `external_directory` block of an agent's frontmatter, as {pattern: action}."""
    front = (ROOT / ".opencode" / "agents" / f"{agent}.md").read_text().split("---")[1]
    block = re.search(r"^  external_directory:\n((?:    .*\n)+)", front, re.M)
    assert block, f"{agent}: no external_directory block"
    return dict(re.findall(r'^    "([^"]+)": (\w+)$', block.group(1), re.M))


def under_tmp(pattern):
    """Whether a grant stays inside /tmp once `.` and `..` are resolved (a glob is a name)."""
    if not pattern.startswith("/"):
        return False
    parts = []
    for part in pattern.split("/")[1:]:
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return bool(parts) and parts[0] == "tmp"


AGENTS = ("reviewer",)


class AgentTmpGrantTests(unittest.TestCase):
    def test_the_reviewer_is_the_one_opencode_agent(self):
        names = sorted(p.stem for p in (ROOT / ".opencode" / "agents").glob("*.md"))
        self.assertEqual(names, ["reviewer"])

    def test_tmp_is_open_to_the_reviewer(self):
        for agent in AGENTS:
            g = grants(agent)
            self.assertEqual(g.get("/tmp"), "allow", agent)
            self.assertEqual(g.get("/tmp/*"), "allow", agent)

    def test_the_archaeology_checkout_is_open_to_the_reviewer(self):
        # tools/check_provenance.py reads the vendored files' source commits there (T01 Done-when 3);
        # a rejected path ends a review with nothing posted ("Choosing models" rule 4)
        for agent in AGENTS:
            g = grants(agent)
            for p in BUNDLE:
                self.assertEqual(g.get(p), "allow", (agent, p))

    def test_nothing_else_outside_the_worktree_is_granted(self):
        for agent in AGENTS:
            outside = {p for p, action in grants(agent).items()
                       if action == "allow" and not under_tmp(p) and p not in BUNDLE}
            self.assertEqual(outside, set(), agent)

    def test_a_dotted_path_out_of_tmp_is_not_under_tmp(self):
        # Luna's R1 on PR 119: "/tmp/../home/*" starts with "/tmp/" but leaves /tmp
        for p in ("/tmp/../home/*", "/tmp/./../etc", "/tmpfoo/*", "tmp/*"):
            self.assertFalse(under_tmp(p), p)
        for p in ("/tmp", "/tmp/*", "/tmp/opencode/*", "/tmp/a/./b"):
            self.assertTrue(under_tmp(p), p)


if __name__ == "__main__":
    unittest.main()
