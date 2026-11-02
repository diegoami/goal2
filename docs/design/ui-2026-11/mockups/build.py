#!/usr/bin/env python3
"""[designed: T157] Writes the static mockups of docs/design/ui-2026-11 as HTML (mockups/sNN-*.html, sharing
mockups/style.css) and, with --render, renders each to a 1440x900 PNG in ../images/ with a headless Chromium.

These are pictures of a design, not app code; they choose no toolkit (T158 does). The names, scores and fixtures
are those of the original's run T156-R1 (docs/original-game/playthrough.md), so each mockup can be read beside
the capture it replaces.

    python3 docs/design/ui-2026-11/mockups/build.py                 # write the HTML
    python3 docs/design/ui-2026-11/mockups/build.py --render CHROME # and render the PNGs
CHROME is a Chrome/Chromium (or chrome-headless-shell) binary.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE.parent / "images"

# Holland in T156-R1 (hub, step 13): the eleven, then the bench. Role codes as docs/vision-266/role-codes.
LINE = {"G": "g", "S": "d", "C": "d", "b": "d", "B": "d", "D": "m", "Ç": "m", "m": "m", "M": "m", "F": "m",
        "w": "a", "W": "a", "¢": "a", "$": "a"}
HOLLAND = [("F V Breukelen", "G"), ("R Koeman", "S"), ("B Van Aerle", "C"), ("A V Tiggelen", "C"),
           ("J Wouters", "D"), ("R Witschge", "m"), ("F Rijkaard", "M"), ("D Bergkamp", "F"), ("B Roy", "w"),
           ("R Gullit", "W"), ("M Van Basten", "$"),
           ("S Menzo", "G"), ("F De Boer", "S"), ("D Blind", "C"), ("W Jonk", "Ç"), ("P Bosz", "Ç"),
           ("J Van't Ship", "M"), ("A Winter", "m"), ("P Van Vossen", "$"), ("W Kieft", "$")]
NORWAY = [("E Thorstvedt", "G"), ("R Bratseth", "S"), ("S Mordt", "C"), ("A Lydersen", "b"), ("G Giske", "B"),
          ("K Halle", "D"), ("G Mykland", "Ç"), ("E Hendriksen", "m"), ("K Rekdal", "M"), ("R Nilsen", "w"),
          ("J Fjortoft", "$")]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rc(code):
    return f'<span class="rc {LINE[code]}">{esc(code)}</span>'


def kbd(*keys):
    return "".join(f"<kbd>{esc(k)}</kbd>" for k in keys)


def top(context=True, crumb="", nxt=None):
    if not context:
        return f'<header class="top"><span class="brand">GOAL2<small>the 1993 game, rebuilt</small></span>' \
               f'<span class="crumb">{esc(crumb)}</span></header>'
    return ('<header class="top"><span class="brand">GOAL2</span>'
            '<span class="comp"><b>2028</b> European Championship · <b>QUALIFYING</b></span>'
            '<span class="who">Holland <span>· manager K Ees</span></span>'
            f'<span class="crumb">{esc(crumb)}</span>'
            f'<span class="next">Next: {nxt or "<b>Norway</b> · friendly · away"}</span></header>')


def keybar(keys, primary=None):
    parts = [f'<span class="kk">{kbd(*k) if isinstance(k, tuple) else kbd(k)} {esc(label)}</span>' for k, label in keys]
    if primary:
        key, label = primary
        parts.append(f'<span class="btn primary">{esc(label)} {kbd(key)}</span>')
    return '<footer class="keys">' + "".join(parts) + "</footer>"


def strip(players=HOLLAND, on=None, title="Holland", split=11, extra=""):
    rows = []
    for i, (name, code) in enumerate(players):
        if i == split:
            rows.append('<li class="sep"></li>')
        cls = ' class="on"' if name == on else ""
        rows.append(f'<li{cls}>{rc(code)} {esc(name)}</li>')
    return (f'<section class="box strip"><h2>{esc(title)}</h2>{extra}<ul class="list">' + "".join(rows) + "</ul></section>")


def bars(rows):
    out = []
    for label, value, word in rows:
        out.append(f'<span>{esc(label)}</span><span class="bar"><i style="width:{value * 100 // 9}%"></i></span>'
                   f'<span class="{"word" if word else "muted"}">{esc(word or str(value))}</span>')
    return '<div class="bars">' + "".join(out) + "</div>"


def page(title, body, keys, primary=None, context=True, crumb="", overlay="", nxt=None):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(title)}</title>'
            f'<link rel="stylesheet" href="style.css"></head><body>{top(context, crumb, nxt)}'
            f'<main>{body}</main>{keybar(keys, primary)}{overlay}</body></html>')


SKILLS = [("keeping", 8, ""), ("kicking", 7, ""), ("tackling", 6, ""), ("heading", 6, ""), ("marking", 2, ""),
          ("passing", 2, ""), ("crossing", 2, ""), ("feinting", 2, ""), ("control", 2, ""), ("dribbling", 2, ""),
          ("shooting", 2, ""), ("penalties", 2, "")]
CHARS = [("hardness", 4, "pushy"), ("fitness", 3, "ok"), ("energy", 4, "fine"), ("morale", 7, "brimming"),
         ("leadership", 0, "none")]


def card(name="F V Breukelen", role="G", status="ready to play", status_cls="good", tactics=None, chars=CHARS,
         skills=SKILLS, extra="", pos="goalkeeper", meta="age 33 · caps 0 · goals 0 · 6′1″ · right foot · performance ★★★★"):
    tactics = tactics or [("position", "leave box P"), ("possession", "keep ball"), ("passing", "throw the ball"),
                          ("tackling", "avoid injury"), ("mark", "—")]
    trows = "".join(f"<dt>{esc(a)}</dt><dd>{esc(b)}</dd>" for a, b in tactics)
    return f'''<section class="box grow col" style="gap:12px">
  <div style="display:flex;align-items:baseline;gap:16px">{rc(role)}<h1>{esc(name)}</h1>
    <span class="sub">{esc(meta)}</span>
    <span style="margin-left:auto;font-weight:800;color:var(--{status_cls})">{esc(status)}</span></div>
  <div class="sub">position <b style="color:var(--text)">{esc(pos)}</b> · club position <b style="color:var(--text)">{esc(pos)}</b> · cards <b style="color:var(--text)">none</b></div>
  {extra}
  <div style="display:flex;gap:24px;min-height:0">
    <div class="grow"><h3 style="margin:0 0 8px;color:var(--frame);font-size:14px;letter-spacing:1.5px">SKILLS</h3>{bars(skills)}</div>
    <div style="width:380px" class="col">
      <div><h3 style="margin:0 0 8px;color:var(--frame);font-size:14px;letter-spacing:1.5px">TACTICS</h3><dl class="kv">{trows}</dl></div>
      <div><h3 style="margin:0 0 8px;color:var(--frame);font-size:14px;letter-spacing:1.5px">CHARACTERISTICS</h3>{bars(chars)}</div>
    </div>
  </div>
</section>'''


SCREENS = {}


def screen(fn):
    SCREENS[fn.__name__.replace("_", "-")] = fn
    return fn


@screen
def s01_import():
    body = '''<div class="col" style="margin:auto;width:900px">
<section class="box" style="padding:30px 34px">
  <span class="tag new">goal2 addition · first start only</span>
  <h1 style="margin:14px 0 6px">Import your game data</h1>
  <p class="sub" style="margin:0 0 20px">goal2 plays the original's game from your own data files. Choose the folder that holds them;
  goal2 checks each file and copies it into its data folder. Your saved careers are never touched.</p>
  <table><tr><th>File</th><th>Needed for</th><th>Check</th></tr>
   <tr><td class="mono">GOAL.DAT</td><td>countries, players, fixtures</td><td style="color:var(--good)">✓ found, verified</td></tr>
   <tr><td class="mono">e039-r0005-date-call.sav</td><td>the original's start</td><td style="color:var(--bad)">✗ missing in this folder</td></tr></table>
  <p style="margin:18px 0 0;color:var(--bad)">One file is missing: e039-r0005-date-call.sav. Choose the folder that holds both files.</p>
  <div class="field" style="margin-top:18px"><span class="muted">Folder</span> <span class="mono">D:\\games\\goal2-data</span></div>
</section></div>'''
    return page("Import data", body, [("Esc", "quit")], ("Enter", "Choose folder…"), context=False,
                crumb="first start")


@screen
def s02_start():
    body = '''<div class="col" style="margin:auto;width:1040px;gap:18px">
<div style="text-align:center"><div class="brand" style="font-size:64px;letter-spacing:10px">GOAL2</div>
<div class="sub">the 1993 international management game · version 2</div></div>
<div style="display:flex;gap:18px">
<section class="box grow"><h2>Continue</h2>
  <div class="menu"><div class="item primary on">Continue Holland, 2028 qualifying<span class="k"><kbd>Enter</kbd></span></div></div>
  <dl class="kv" style="margin-top:14px"><dt>manager</dt><dd>K Ees</dd><dt>next</dt><dd>Cyprus · qualifying · home</dd>
  <dt>saved</dt><dd>T156 · today 21:04</dd></dl></section>
<section class="box" style="width:400px"><h2>Load a saved game?</h2>
  <div class="menu"><div class="item">Load another save<span class="k"><kbd>Y</kbd></span></div>
  <div class="item">New game<span class="k"><kbd>N</kbd></span></div>
  <div class="item">Quit<span class="k"><kbd>Esc</kbd></span></div></div></section>
</div>
<section class="box"><h2>Saved games</h2><table>
 <tr><th>Name</th><th>Country</th><th>Year · stage</th><th>Next</th><th>Saved</th></tr>
 <tr class="on"><td>T156</td><td>Holland</td><td>2028 · qualifying</td><td>Cyprus (H)</td><td>today 21:04</td></tr>
 <tr><td>SAVED</td><td>Holland</td><td>2028 · qualifying</td><td>Norway (A)</td><td>today 20:31</td></tr>
 <tr><td>ITALY-90</td><td>Italy</td><td>2030 · finals</td><td>Brazil (N)</td><td>29 Oct</td></tr></table>
 <p class="sub" style="margin:10px 0 0">A save that cannot be opened says why here, with <kbd>Y</kbd> try again or <kbd>N</kbd> back (the original's “file not found · try again? (Y/N)”).</p></section>
</div>'''
    return page("Start", body, [("Y", "load a saved game"), ("N", "new game"), (("↑", "↓"), "choose save"),
                                ("Esc", "quit")], ("Enter", "Continue"), context=False, crumb="title")


@screen
def s03_new_game():
    digits = "".join(f'<span class="btn{" primary" if i == 1 else ""}" style="font-size:28px;width:70px;justify-content:center">{i}</span>' for i in range(1, 7))
    body = f'''<div class="col" style="margin:auto;width:900px">
<section class="box" style="padding:30px 34px"><h2>New game</h2>
 <h1 style="margin:0 0 6px">How many managers?</h1>
 <p class="sub">Each manager takes a country of their own; they play in turn at the manager's desk.</p>
 <div style="display:flex;gap:14px;margin:24px 0">{digits}</div>
 <p class="sub">One manager is the usual game. With more, the country and name steps repeat for each,
 and the desk gains <b>next player</b>.</p>
 <div class="box" style="margin-top:18px;background:var(--panel-2);display:flex;align-items:center;gap:14px">
  <span class="tag">busy state</span><span>Hang on a tick: preparing the 128 countries…</span></div>
</section></div>'''
    return page("New game", body, [(("←", "→"), "number"), ("Esc", "back to title")], ("Enter", "Accept"),
                context=False, crumb="new game · step 1 of 3")


@screen
def s04_country():
    countries = ["Denmark", "Germany", "Holland", "Sweden", "Scotland", "France", "England", "Russia", "Yugoslavia",
                 "Switzerland", "R.C.S", "Wales", "Eire", "Portugal", "Italy", "Romania"]
    clist = "".join(f'<li{" class=\"on\"" if c == "Holland" else ""}>{c}<span class="r muted">{r}</span></li>'
                    for c, r in zip(countries, [9, 2, 3, 11, 20, 4, 6, 7, 10, 18, 15, 25, 12, 16, 5, 13]))
    teamb = bars([("keeper", 8, ""), ("defence", 6, ""), ("midfield", 8, ""), ("attack", 6, "")])
    charb = bars([("hardness", 4, "average"), ("fitness", 8, "supreme"), ("energy", 8, "electrified"),
                  ("morale", 3, "lacking")])
    body = f'''<div class="col grow">
<section class="box" style="display:flex;align-items:center;gap:28px">
  <div><div class="sub">Player 1 · choose your country</div><h1>Holland</h1></div>
  <dl class="kv"><dt>status</dt><dd>major</dd><dt>manager</dt><dd>D Advocaat</dd></dl>
  <dl class="kv"><dt>world</dt><dd>14 <span class="muted">(top 14)</span></dd><dt>Europe</dt><dd>3 <span class="muted">(top 3)</span></dd></dl>
  <dl class="kv"><dt>formation</dt><dd>3-6-1</dd><dt>skill</dt><dd>exceptional</dd></dl>
  <div style="margin-left:auto;text-align:right"><div class="sub">level of difficulty</div><div class="big sel">SIMPLE</div></div>
</section>
<div style="display:flex;gap:18px" class="grow">
 <section class="box grow"><h2>Skills</h2>{teamb}<h2 style="margin-top:16px">Performance</h2>{bars([("keeper", 9, ""), ("defence", 9, ""), ("midfield", 9, ""), ("attack", 9, "")])}</section>
 <section class="box grow"><h2>Team tactics</h2><dl class="kv"><dt>defence system</dt><dd>full pitch</dd><dt>protection</dt><dd>stand ground</dd><dt>offside</dt><dd>offside trap</dd></dl>
 <h2 style="margin-top:14px">Player defaults</h2><dl class="kv"><dt>positioning</dt><dd>push forward</dd><dt>possession</dt><dd>keep ball</dd><dt>passing</dt><dd>short passes</dd><dt>tackling</dt><dd>avoid injury</dd><dt>marking</dt><dd>man to man</dd></dl></section>
 <section class="box grow"><h2>Characteristics</h2><div class="sub" style="margin-bottom:8px">average caps 0 · age 28</div>{charb}</section>
</div>
<section class="box" style="display:flex;align-items:center;gap:16px"><span class="muted">Manager's name</span>
 <div class="field grow"><span>Kees</span><span class="cursor"></span><span class="muted" style="margin-left:auto;font-size:15px">4 / 14</span></div>
 <span class="sub">Enter on a country opens this line; Enter again starts the career.</span></section>
</div>
<section class="box" style="width:300px"><h2>Countries · world rank</h2><ul class="list">{clist}</ul>
<p class="sub" style="margin:10px 0 0">16 of 128 · <kbd>←</kbd><kbd>→</kbd> next group</p></section>'''
    return page("Country", body, [(("↑", "↓"), "country"), (("←", "→"), "group of 16"), ("Ins", "world / continental rank"),
                                  ("Space", "players"), ("Esc", "back")], ("Enter", "Choose Holland"),
                context=False, crumb="new game · step 2 of 3 · country and name")


@screen
def s05_bulletin():
    body = '''<div class="col grow" style="max-width:1392px">
<div style="text-align:center;font:900 46px/1 Georgia,'DejaVu Serif',serif;letter-spacing:4px;padding:6px 0 4px;border-bottom:3px double var(--line)">THE SOCCER BULLETIN</div>
<div style="display:flex;gap:18px" class="grow">
 <section class="box" style="width:330px;font-family:Georgia,'DejaVu Serif',serif"><h2>Physio's room</h2><p style="font-size:20px">WITSCHGE BACK IN TRAINING</p><p class="sub">The midfielder is “ready to play” again after Saturday's knock.</p></section>
 <section class="box grow" style="font-family:Georgia,'DejaVu Serif',serif;text-align:center"><h2>Front page · 1 of 2</h2>
  <div style="font-size:52px;font-weight:900;line-height:1.05;margin:30px 0">K EES HAS GOT IT RIGHT</div>
  <div style="font-size:30px">HOLLAND DO THE JOB — JUST</div>
  <p class="sub" style="margin-top:26px;font-size:19px">Norway 0 – 1 Holland · friendly · Bergkamp 83</p></section>
 <section class="box" style="width:330px;font-family:Georgia,'DejaVu Serif',serif"><h2>Football association</h2><p style="font-size:20px">“A FINE START”</p><p class="sub">Next: Cyprus at home, the first qualifier of Group C.</p></section>
</div></div>'''
    return page("Bulletin", body, [("Esc", "skip all news")], ("Enter", "Next page"), crumb="news", nxt="<b>Cyprus</b> · qualifying · home")


@screen
def s06_hub():
    items = [("team info", ""), ("fixture list", ""), ("tournament", ""), ("history", ""), ("select squad", "Space")]
    menu = "".join(f'<div class="item">{n}<span class="k">{kbd(k) if k else ""}</span></div>' for n, k in items)
    body = f'''<div class="col" style="width:420px">
<section class="box"><h2>Manager</h2><dl class="kv"><dt>name</dt><dd>K Ees</dd><dt>rating</dt><dd>unknown</dd></dl></section>
<section class="box"><h2>Team</h2><div class="big">Holland</div><dl class="kv"><dt>world</dt><dd>14</dd><dt>Europe</dt><dd>3</dd></dl></section>
<section class="box"><h2>Next opponents</h2><div class="big sel">Norway</div><dl class="kv"><dt>world</dt><dd>32</dd><dt>Europe</dt><dd>18</dd><dt>match</dt><dd>friendly · away</dd></dl></section>
<section class="box"><h2>Managers</h2><div>1 · K Ees <span class="muted">(Holland)</span></div></section>
</div>
<div class="col grow">
<div class="menu">
 <div class="item primary on">▶ play next game<span class="sub" style="margin-left:14px">Norway away · friendly</span><span class="k"><kbd>Enter</kbd></span></div>
 {menu}
 <div class="item" style="opacity:.75">autopilot: let the assistant manage<span class="tag new" style="margin-left:10px">goal2 · later</span><span class="k"><kbd>A</kbd></span></div>
</div>
<section class="box"><h2>Before the match</h2><ul class="list" style="font-size:16px">
 <li><span style="color:var(--good)">●</span> 20 in the squad · all ready to play</li>
 <li><span style="color:var(--warn)">●</span> no captain chosen yet: you choose him at kick-off (or <kbd>C</kbd> lets the computer)</li></ul></section>
</div>
{strip()}'''
    return page("Manager's desk", body, [("F1", "help"), ("F3", "load goal"), ("F4", "load summary"), ("F7", "save"),
                                         ("F10", "quit"), ("T", "team tactics"), (("↑", "↓"), "choose")],
                ("Enter", "Play next game"),
                crumb="manager's desk")


@screen
def s07_team_info():
    countries = ["Germany", "Argentina", "Italy", "England", "Cameroon", "R.C.S", "Eire", "Yugoslavia", "Brazil",
                 "Spain", "Belgium", "Romania", "Costa Rica", "Holland", "Colombia", "Uruguay"]
    clist = "".join(f'<li{" class=\"on\"" if c == "Norway" else ""}>{c}</li>' for c in countries[:8]) + \
        '<li class="on">Norway<span class="r">next opponent</span></li>' + \
        "".join(f"<li>{c}</li>" for c in countries[8:15])
    body = f'''<div class="col grow">
<section class="box" style="display:flex;gap:28px;align-items:center"><h1>Norway</h1>
<dl class="kv"><dt>status</dt><dd>average</dd><dt>manager</dt><dd>E Olsen</dd></dl>
<dl class="kv"><dt>world</dt><dd>32 (top 30)</dd><dt>Europe</dt><dd>18 (top 17)</dd></dl>
<dl class="kv"><dt>formation</dt><dd>4-5-1</dd><dt>skill</dt><dd>capable</dd></dl></section>
<div style="display:flex;gap:18px" class="grow">
<section class="box grow"><h2>Skills</h2>{bars([("keeper", 6, ""), ("defence", 6, ""), ("midfield", 5, ""), ("attack", 4, "")])}
<h2 style="margin-top:14px">Performance</h2>{bars([("keeper", 9, ""), ("defence", 9, ""), ("midfield", 9, ""), ("attack", 9, "")])}</section>
<section class="box grow"><h2>Team tactics</h2><dl class="kv"><dt>defence system</dt><dd>half pitch</dd><dt>protection</dt><dd>sag back to box</dd><dt>offside</dt><dd>play safe</dd></dl>
<h2 style="margin-top:14px">Player defaults</h2><dl class="kv"><dt>positioning</dt><dd>stay back</dd><dt>possession</dt><dd>quick pass</dd><dt>passing</dt><dd>long passes</dd><dt>tackling</dt><dd>go in hard</dd><dt>marking</dt><dd>zonal</dd></dl></section>
<section class="box grow"><h2>Characteristics</h2><div class="sub" style="margin-bottom:8px">average caps 22 · age 26</div>{bars([("hardness", 7, "tough"), ("fitness", 8, "supreme"), ("energy", 8, "electrified"), ("morale", 5, "could be worse")])}</section>
</div></div>
<section class="box" style="width:300px"><h2>Check out all the competitors</h2><ul class="list">{clist}</ul></section>'''
    return page("Team info", body, [(("↑", "↓", "←", "→"), "country"), ("Ins", "world / continental rank"),
                                    ("Space", "players"), ("T", "tactics"), ("Esc", "desk")],
                ("Enter", "Fixtures of Norway"), crumb="team info")


@screen
def s08_squad():
    head = '''<div style="display:flex;gap:10px;align-items:center"><span class="btn primary" style="font-size:16px;padding:6px 14px">Squad (20)</span>
<span class="btn" style="font-size:16px;padding:6px 14px">Pool</span><span class="sub">←→ toggles · Ins: the assistant's recommended 20</span></div>'''
    body = f'''<div class="col grow">{head}{card()}
<section class="box" style="display:flex;gap:14px;align-items:center;padding:10px 16px"><span class="tag">move player</span>
<span>Enter on a pool player, <kbd>←</kbd> back to the squad, Enter on the player he replaces. One exchange, shown before it is made:</span>
<span class="sel" style="margin-left:auto">B Gathergood ⇄ S Menzo</span></section></div>
{strip(on="F V Breukelen")}'''
    return page("Squad", body, [(("↑", "↓"), "player"), (("←", "→"), "squad / pool"), ("Ins", "assistant's 20"),
                                ("R", "next position"), ("C", "club position"), ("T", "his tactics"), ("F2", "new name"),
                                ("Esc", "desk")], ("Enter", "Move player"), crumb="select squad")


@screen
def s09_player_tactics():
    rows = [("position", "push forward P"), ("possession", "keep ball"), ("passing", "short passes"),
            ("tackling", "avoid injury"), ("mark", "Protect zone")]
    trs = "".join(f'<tr{" class=\"on\"" if i == 4 else ""}><td>{a}</td><td>{b}</td></tr>' for i, (a, b) in enumerate(rows))
    body = f'''<div class="col grow">
<section class="box" style="display:flex;gap:20px;align-items:baseline">{rc("C")}<h1>R Koeman</h1><span class="sub">sweeper · club position sweeper · ready to play</span></section>
<div style="display:flex;gap:18px" class="grow">
<section class="box" style="width:560px"><h2>His own tactics</h2><table>{trs}</table>
<p class="sub" style="margin:14px 0 0">Enter steps the highlighted line to its next option. <b>P</b> marks a line set for this player, not by the team's defaults.
The mark line steps from zone to each opponent by name; marks are cleared after every match.</p></section>
<section class="box grow"><h2>Skills</h2>{bars(SKILLS[:6])}<h2 style="margin-top:14px">Characteristics</h2>{bars(CHARS)}</section>
</div></div>{strip(on="R Koeman")}'''
    return page("Player tactics", body, [(("↑", "↓", "←", "→"), "line"), ("Esc", "back to the card")],
                ("Enter", "Alter tactic"), crumb="select squad · R Koeman · tactics")


@screen
def s10_team_tactics():
    rows = [("defence system", "half pitch", "full pitch"), ("protection", "stand ground", "sag back to box"),
            ("offside", "offside trap", "play safe"), ("positioning", "push forward", "stay back"),
            ("possession", "keep ball", "quick pass"), ("passing", "short passes", "long passes"),
            ("tackling", "avoid injury", "go in hard"), ("marking", "man to man", "zonal")]
    trs = "".join(f'<tr{" class=\"on\"" if i == 0 else ""}><td>{a}</td><td><b>{b}</b></td><td class="muted">{c}</td></tr>'
                  for i, (a, b, c) in enumerate(rows))
    body = f'''<div class="col grow">
<section class="box" style="display:flex;gap:28px;align-items:center"><h1>Holland</h1><span class="sub">formation <b style="color:var(--text)">3-6-1</b> · next Norway away</span></section>
<div style="display:flex;gap:18px" class="grow">
<section class="box grow"><h2>Team tactics · player defaults</h2><table><tr><th>line</th><th>now</th><th>other option</th></tr>{trs}</table>
<p class="sub" style="margin:14px 0 0">Changed just now: defence system full pitch → <b class="sel">half pitch</b>. The last five lines are the defaults every player
follows unless his own tactics say otherwise (P).</p></section>
<section class="box" style="width:420px"><h2>Characteristics</h2>{bars([("hardness", 4, "average"), ("fitness", 8, "supreme"), ("energy", 8, "electrified"), ("morale", 3, "lacking")])}</section>
</div></div>{strip()}'''
    return page("Team tactics", body, [(("↑", "↓"), "line"), ("Esc", "desk")], ("Enter", "Change line"),
                crumb="team tactics")


@screen
def s11_fixtures():
    fx = [("Russia", "R.C.S", "friendly", ""), ("Yugoslavia", "Bulgaria", "friendly", ""),
          ("Yugoslavia", "Luxembourg", "qualifying", ""), ("Iceland", "France", "friendly", ""),
          ("Belgium", "Switzerland", "friendly", ""), ("Denmark", "Poland", "friendly", ""),
          ("Wales", "Albania", "friendly", ""), ("Denmark", "Belgium", "qualifying", "✓"),
          ("Holland", "Cyprus", "qualifying", "✓you"), ("Albania", "France", "friendly", ""),
          ("Malta", "Austria", "friendly", ""), ("Greece", "Sweden", "friendly", "")]
    trs = "".join(
        f'<tr class="{"on" if i == 7 else ("us" if w == "✓you" else "")}"><td class="n">{"✓" if "✓" in w else ""}</td><td style="text-align:right">{a}</td><td class="n muted">v</td><td>{b}</td><td>{k}</td><td>{"your match" if w == "✓you" else ("watch" if w == "✓" else "auto result")}</td></tr>'
        for i, (a, b, k, w) in enumerate(fx))
    body = f'''<div class="col grow"><section class="box grow"><h2>Fixtures and results · round 2</h2>
<table><tr><th class="n">watch</th><th style="text-align:right">home</th><th></th><th>away</th><th>match</th><th>at kick-off</th></tr>{trs}</table>
<p class="sub" style="margin:12px 0 0">✓ marks a match you will watch. The action on the right names what Enter does now: on a marked row, “auto result”; on an unmarked row,
“watch match”; on your own friendly, cancel or rearrange it.</p></section></div>'''
    return page("Fixtures", body, [(("↑", "↓"), "scroll"), ("Esc", "desk")], ("Enter", "Auto result (unmark)"),
                crumb="fixture list", nxt="<b>Cyprus</b> · qualifying · home")


@screen
def s12_tournament():
    table = [("Holland", 1, 1, 0, 0, 2, 1, 2), ("R.C.S", 0, 0, 0, 0, 0, 0, 0), ("Bulgaria", 0, 0, 0, 0, 0, 0, 0),
             ("Cyprus", 1, 0, 0, 1, 1, 2, 0)]
    trs = "".join(f'<tr class="{"us" if r[0] == "Holland" else ""}"><td>{r[0]}</td>' + "".join(f'<td class="n">{v}</td>' for v in r[1:]) + "</tr>" for r in table)
    fx = [("Holland", "2", "1", "Cyprus"), ("R.C.S", "", "", "Bulgaria"), ("R.C.S", "", "", "Cyprus"),
          ("Bulgaria", "", "", "Holland"), ("Cyprus", "", "", "Bulgaria"), ("Holland", "", "", "R.C.S")]
    frs = "".join(f'<tr><td style="text-align:right">{a}</td><td class="n">{x}{"–" if x else "v"}{y}</td><td>{b}</td></tr>' for a, x, y, b in fx)
    tabs = lambda names, on: "".join(f'<span class="btn{" primary" if n == on else ""}" style="font-size:16px;padding:6px 14px">{n}</span>' for n in names)
    body = f'''<div class="col grow">
<div style="display:flex;gap:10px;align-items:center"><span class="sub">display</span>{tabs(["Qualifying", "Finals", "Championship"], "Qualifying")}
<span style="width:30px"></span><span class="sub">continent</span>{tabs(["Europe", "Africa", "Americas", "Asia"], "Europe")}</div>
<div style="display:flex;gap:18px" class="grow">
<section class="box grow"><h2>Group C · European qualifying</h2><table><tr><th>team</th><th class="n">P</th><th class="n">W</th><th class="n">D</th><th class="n">L</th><th class="n">F</th><th class="n">A</th><th class="n">T</th></tr>{trs}</table>
<p class="sub" style="margin:12px 0 0">Group 3 of 8 · ↑↓ another group. The Championship display shows the bracket; on a World Cup bracket Ins shows the Championship results.</p></section>
<section class="box" style="width:480px"><h2>Group C matches</h2><table>{frs}</table></section>
</div></div>'''
    return page("Tournament", body, [(("↑", "↓"), "group"), ("Space", "continent"), (("←", "→"), "display"),
                                     ("Ins", "Championship results"), ("Esc", "desk")], None, crumb="tournament", nxt="<b>Belgium</b> · friendly · home")


@screen
def s13_history():
    body = '''<div class="col grow"><div style="display:flex;gap:18px">
<section class="box grow"><h2>Statistics</h2><table><tr><th></th><th class="n">home now</th><th class="n">top</th><th class="n">away now</th><th class="n">top</th><th class="n">all now</th><th class="n">top</th></tr>
<tr><td>consecutive wins</td><td class="n">0</td><td class="n">0</td><td class="n">1</td><td class="n">1</td><td class="n">1</td><td class="n">1</td></tr>
<tr><td>consecutive defeats</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td></tr>
<tr><td>games without a win</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td></tr>
<tr><td>games without defeat</td><td class="n">0</td><td class="n">0</td><td class="n">1</td><td class="n">1</td><td class="n">1</td><td class="n">1</td></tr></table></section>
<section class="box" style="width:360px"><h2>Successes</h2><table><tr><th></th><th class="n">1st</th><th class="n">2nd</th><th class="n">3rd</th><th class="n">4th</th></tr>
<tr><td>World Cup</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td></tr><tr><td>Championship</td><td class="n">0</td><td class="n">0</td><td class="n">0</td><td class="n">0</td></tr></table></section></div>
<div style="display:flex;gap:18px" class="grow">
<section class="box grow"><h2>Results</h2><table><tr><th>season</th><th></th><th class="n">W</th><th class="n">D</th><th class="n">L</th><th class="n">F</th><th class="n">A</th><th>best place</th></tr>
<tr><td>2027/28</td><td>EC</td><td class="n">1</td><td class="n">0</td><td class="n">0</td><td class="n">2</td><td class="n">1</td><td>qualifying</td></tr></table></section>
<section class="box" style="width:300px"><h2>Top scorers</h2><div>D Bergkamp · 1<br>J Wouters · 1<br>B Roy · 1</div></section>
<section class="box" style="width:300px"><h2>Top caps</h2><div>R Witschge · 2<br>R Koeman · 2</div></section></div>
<section class="box"><h2>Records</h2><table><tr><th></th><th>biggest win</th><th>biggest defeat</th></tr><tr><td>home</td><td>Holland 2 v 1 Cyprus</td><td class="muted">—</td></tr><tr><td>away</td><td>Norway 0 v 1 Holland</td><td class="muted">—</td></tr><tr><td>neutral</td><td class="muted">—</td><td class="muted">—</td></tr></table></section>
</div>'''
    return page("History", body, [("Esc", "desk")], None, crumb="history · Holland", nxt="<b>Belgium</b> · friendly · home")


@screen
def s14_round():
    res = [("Russia", 2, 1, "R.C.S", "friendly"), ("Yugoslavia", 2, 1, "Bulgaria", "friendly"),
           ("Yugoslavia", 3, 0, "Luxembourg", "qualifying"), ("Iceland", 2, 0, "France", "friendly"),
           ("Belgium", 1, 0, "Switzerland", "friendly"), ("Denmark", 0, 1, "Poland", "friendly"),
           ("Wales", 1, 0, "Albania", "friendly"), ("Denmark", 2, 0, "Belgium", "qualifying")]
    trs = "".join(f'<tr><td style="text-align:right">{a}</td><td class="n"><b>{x} – {y}</b></td><td>{b}</td><td class="muted">{k}</td></tr>' for a, x, y, b, k in res)
    body = f'''<div class="col grow" style="max-width:1100px;margin:0 auto">
<section class="box grow"><h2>Round 2 · the results so far</h2><table>{trs}
<tr class="us"><td style="text-align:right">Holland</td><td class="n">v</td><td>Cyprus</td><td>qualifying · your match is next</td></tr></table>
<p class="sub" style="margin:14px 0 0">The results arrive one by one; Space pauses, ←→ change the pace. Then your match: the match menu, where you
pick the team, choose the captain and kick off.</p></section></div>'''
    return page("Round", body, [("Space", "pause"), (("←", "→"), "speed")], ("Enter", "To your match"),
                crumb="play next game · round 2", nxt="<b>Cyprus</b> · qualifying · home")


def lineup(players, side):
    return "".join(f'<li>{rc(c)} {esc(n)}</li>' for n, c in players[:11])


@screen
def s15_match_menu():
    body = f'''<div class="col grow">
<section class="box" style="display:flex;align-items:center;gap:30px">
 <div class="score"><span style="color:var(--home)">Norway</span><span class="s">0</span><span class="muted" style="font-size:18px">v</span><span class="s">0</span><span>Holland</span></div>
 <span class="sub">FRIENDLY · location: Norway · before kick-off</span>
 <span style="margin-left:auto" class="sub">automatic action replay <b style="color:var(--text)">OFF</b> (Ins)</span></section>
<div style="display:flex;gap:18px" class="grow">
 <section class="box" style="width:300px"><h2>Norway · 4-5-1</h2><ul class="list">{lineup(NORWAY, "h")}</ul></section>
 <div class="col grow">
  <div style="display:flex;gap:12px"><div class="menu grow"><div class="item">Norway team tactics</div><div class="item">Norway players</div></div>
   <div class="menu grow"><div class="item">Holland team tactics<span class="k"><kbd>T</kbd></span></div><div class="item">Holland players<span class="k"><kbd>Space</kbd></span></div></div></div>
  <div class="menu"><div class="item">tournament</div><div class="item">match stats</div>
   <div class="item primary on">▶ play<span class="sub" style="margin-left:14px">next: choose your captain, then kick-off</span><span class="k"><kbd>Enter</kbd></span></div></div>
  <p class="sub" style="margin:0">After a half: the same menu with HALF TIME and the score; after the final whistle <b>exit</b> replaces <b>play</b>; when a knockout
  is level, EXTRA TIME with play again.</p>
 </div>
 <section class="box" style="width:300px"><h2>Holland · 3-6-1</h2><ul class="list">{lineup(HOLLAND, "v")}</ul></section>
</div></div>'''
    return page("Match menu", body, [(("↑", "↓", "←", "→"), "choose"), ("Ins", "action replay on/off")],
                ("Enter", "Play"), crumb="match menu · Norway v Holland")


@screen
def s16_captain():
    names = HOLLAND[:11]
    rows = "".join(f'<li{" class=\"on\"" if n == "B Van Aerle" else ""}>{rc(c)} {esc(n)}{"<span class=\"r tag\">C pick</span>" if n == "A V Tiggelen" else ""}</li>' for n, c in names)
    body = f'''<div class="col grow">
<section class="box" style="display:flex;align-items:center;gap:20px;border-color:var(--select)">
 <span class="big sel" style="white-space:nowrap">Choose your captain to kick off</span>
 <span class="sub">The match starts as soon as a captain is chosen. Enter: the highlighted player · C: the computer picks (A V Tiggelen)
 · no key: the computer's pick stands after a short wait.</span></section>
<div style="display:flex;gap:18px" class="grow">
 {card("B Van Aerle", "C", pos="centre back", meta="age 29 · caps 41 · goals 1 · 5′11″ · right foot", skills=[("keeping", 1, ""), ("kicking", 6, ""), ("tackling", 8, ""), ("heading", 7, ""), ("marking", 8, ""), ("passing", 6, ""), ("crossing", 4, ""), ("feinting", 4, ""), ("control", 6, ""), ("dribbling", 4, ""), ("shooting", 3, ""), ("penalties", 4, "")], tactics=[("position", "stay back"), ("possession", "keep ball"), ("passing", "short passes"), ("tackling", "go in hard"), ("mark", "—")], chars=[("hardness", 6, "tough"), ("fitness", 7, "match fit"), ("energy", 7, "fine"), ("morale", 6, "good"), ("leadership", 7, "inspiring")])}
 <section class="box" style="width:300px"><h2>Holland's eleven</h2><ul class="list">{rows}</ul></section>
</div>
<p class="sub" style="margin:0">The same stop, with the same keys, chooses a corner or goal-kick taker during the match, and the penalty order (Esc undoes a pick) before a shoot-out.</p>
</div>'''
    return page("Captain", body, [(("↑", "↓"), "player"), ("C", "computer select")], ("Enter", "Captain: kick off"),
                crumb="Norway v Holland · captain")


def pitch_html(width=1000, height=560):
    home = [(6, 50, "G"), (18, 30, "C"), (18, 70, "C"), (14, 50, "S"), (35, 50, "D"), (30, 20, "M"), (30, 80, "M"),
            (46, 50, "F"), (46, 15, "W"), (46, 85, "W"), (50, 56, "$")]
    away = [(94, 50, "G"), (88, 50, "S"), (84, 30, "C"), (84, 70, "C"), (78, 15, "B"), (78, 85, "B"), (66, 30, "M"),
            (66, 70, "M"), (60, 50, "Ç"), (52, 42, "W"), (57, 64, "F")]
    ps = "".join(f'<div class="p v" style="left:{x}%;top:{y}%">{esc(c)}</div>' for x, y, c in home)
    ps += "".join(f'<div class="p h" style="left:{x}%;top:{y}%">{esc(c)}</div>' for x, y, c in away)
    lines = ('<div class="line" style="left:50%;top:0;bottom:0;border-width:0 0 0 2px"></div>'
             '<div class="line" style="left:0;top:25%;width:15%;height:50%;border-left:0"></div>'
             '<div class="line" style="right:0;top:25%;width:15%;height:50%;border-right:0"></div>'
             '<div class="line" style="left:calc(50% - 60px);top:calc(50% - 60px);width:120px;height:120px;border-radius:50%"></div>')
    return f'<div class="pitch" style="width:{width}px;height:{height}px">{lines}{ps}<div class="ball" style="left:51%;top:50%"></div></div>'


def match_header(minute="17", events=("Bratseth wins the toss", "Nilsen to take kick off"), score=(0, 0)):
    ev = "".join(f"<div>{esc(e)}</div>" for e in events)
    return f'''<section class="box" style="display:flex;align-items:center;gap:30px;padding:10px 18px">
 <div class="score"><span style="color:var(--home)">Norway</span><span class="s">{score[0]}</span><span class="s">{score[1]}</span><span>Holland</span></div>
 <span class="big" style="font-size:30px">{minute}′</span><span class="sub">FRIENDLY</span>
 <div style="margin-left:auto;text-align:right;font-size:19px">{ev}</div></section>'''


@screen
def s17_pitch():
    comm = ["1′ Bratseth wins the toss", "1′ Nilsen to take kick off", "9′ Goal kick: Holland", "12′ Witschge corner",
            "14′ FOUL by Nilsen", "14′ Nilsen BOOKED", "15′ Witschge INJURED", "17′ Rijkaard on the ball"]
    body = f'''<div class="col grow">{match_header()}
<div style="display:flex;gap:18px" class="grow"><div>{pitch_html()}</div>
<section class="box grow"><h2>Commentary</h2><ul class="list" style="font-size:16px">{"".join(f"<li>{esc(c)}</li>" for c in comm)}</ul>
<p class="sub" style="margin:14px 0 0">Speed »»»»» · marks: positions · <span class="tag">your side: white</span></p></section></div></div>'''
    return page("Pitch", body, [(("↑", "↓"), "display"), (("←", "→"), "speed"), ("R", "result"), ("Space", "commentary"),
                                ("F9", "sound")], ("Esc", "Bench"), crumb="watching · Norway v Holland")


@screen
def s18_match_stop():
    over = '''<div class="scrim"><div class="dialog"><span class="tag">the match stops</span>
<h2 style="margin-top:12px">**** GOAL **** by Bergkamp</h2><p>Norway 0 – 1 Holland, 83′. Do you want an action replay?</p>
<p class="sub">Then: “Do you want to save this goal?” and its file name (G-1.HIL), in this same box. Other stops use it too:
SUBSTITUTION OPPORTUNITY (your player injured: any key opens the bench), the other side's substitution, the shoot-out.</p>
<div class="row"><span class="btn">No <kbd>N</kbd></span><span class="btn primary">Yes, show it <kbd>Y</kbd></span></div></div></div>'''
    body = f'''<div class="col grow">{match_header("83", ("**** GOAL ****", "by Bergkamp"), (0, 1))}
<div style="display:flex;gap:18px" class="grow"><div>{pitch_html()}</div><section class="box grow"><h2>Commentary</h2></section></div></div>'''
    return page("Match stop", body, [("Y", "yes"), ("N", "no")], None, crumb="watching · Norway v Holland",
                overlay=over)


@screen
def s19_bench():
    extra = '''<div style="display:flex;gap:14px;align-items:center"><span class="big sel">MAKE SUBSTITUTIONS NOW</span>
<span class="btn">substitutions left <b style="font-size:22px;margin-left:6px">5</b></span>
<span class="sub">half time · Norway 0–0 Holland</span></div>
<div class="box" style="background:var(--panel-2);padding:8px 14px">One exchange, two Enters in either order: <b>who comes off</b> (highlighted: R Witschge, injured), then <b>who goes on</b>. The line names both before the second Enter.</div>'''
    players = HOLLAND[:5] + HOLLAND[6:11] + [("R Witschge", "m")] + [("B Gathergood", "G")] + HOLLAND[12:20]
    body = f'''<div class="col grow">{card("R Witschge", "m", pos="left midfield", meta="age 28 · caps 0 · goals 0 · 5′11″ · left foot · performance ★★★★", skills=[("keeping", 1, ""), ("kicking", 6, ""), ("tackling", 6, ""), ("heading", 3, ""), ("marking", 6, ""), ("passing", 7, ""), ("crossing", 8, ""), ("feinting", 4, ""), ("control", 7, ""), ("dribbling", 7, ""), ("shooting", 5, ""), ("penalties", 4, "")], status="injured", status_cls="bad", extra=extra, chars=[("hardness", 3, "gentle"), ("fitness", 0, "injured"), ("energy", 0, "can't play"), ("morale", 4, "below par"), ("leadership", 0, "none")])}</div>
{strip(players=players[:11] + players[11:20], on="R Witschge")}'''
    return page("Bench", body, [(("↑", "↓"), "player"), ("R", "next position"), ("C", "club position"), ("T", "his tactics"),
                                ("Esc", "match menu")], ("Enter", "Take off this player"),
                crumb="Norway v Holland · players")


@screen
def s20_board():
    stats = [("corners", 1, 1), ("free kicks", 5, 6), ("penalties", 0, 0), ("shots", 2, 6), ("on target", 0, 2),
             ("saves", 1, 2), ("fouls", 4, 3), ("bookings", 2, 0), ("red cards", 0, 0)]
    trs = "".join(f'<tr><td class="n">{a}</td><td class="n muted">{k}</td><td class="n">{b}</td></tr>' for k, a, b in stats)
    body = f'''<div class="col grow">
<section class="box" style="display:flex;align-items:center;gap:30px"><div class="score"><span style="color:var(--home)">Norway</span><span class="s">0</span><span class="s">1</span><span>Holland</span></div>
<span class="big">FULL TIME</span><span class="sub">half time 0:0 · FRIENDLY</span><span style="margin-left:auto" class="sel">MAN OF THE MATCH R Bratseth</span></section>
<div style="display:flex;gap:18px" class="grow">
<section class="box" style="width:300px"><h2>Norway scorers</h2><div class="muted">—</div></section>
<section class="box grow"><h2>Match statistics</h2><table><tr><th class="n">Norway</th><th></th><th class="n">Holland</th></tr>{trs}</table>
<div style="margin-top:12px">{bars([("possession", 4, "50 %"), ("territory", 4, "48 %")])}</div></section>
<section class="box" style="width:300px"><h2>Holland scorers</h2><div>D Bergkamp <span class="sel">83′</span></div></section></div>
<p class="sub" style="margin:0">A quick result shows this board with a QUICK RESULT banner in place of the statistics. After a watched match, exit asks
“Save the match summary?” (Y/N, file name S-1.SUM); F4 at the desk reopens a saved summary on this board.</p></div>'''
    return page("Match board", body, [("Esc", "bench")], ("Enter", "Continue"), crumb="Norway v Holland · full time")


@screen
def s21_save_quit():
    over = '''<div class="scrim"><div class="dialog"><h2>Save the game</h2><p>Please enter the name of the saved game.</p>
<div class="field"><span>T156</span><span class="cursor"></span><span class="muted" style="margin-left:auto">.GL</span></div>
<p class="sub" style="margin-top:14px">The last name you used is offered. The same box asks for a goal file (F3, G-1.HIL) or a summary (F4, S-1.SUM).
F10 asks “Are you sure you want to quit? (Y/N)” and then “Do you want to save this game? (Y/N)”.</p>
<div class="row"><span class="btn">Cancel <kbd>Esc</kbd></span><span class="btn primary">Save <kbd>Enter</kbd></span></div></div></div>'''
    body = '<div class="col grow"><section class="box grow"><h2>Manager\'s desk</h2></section></div>' + strip()
    return page("Save", body, [("Esc", "cancel")], ("Enter", "Save"), crumb="manager's desk · save", overlay=over)


@screen
def s22_help():
    over = '''<div class="scrim"><div class="dialog" style="width:860px"><span class="tag">F1 · on every screen</span>
<h2 style="margin-top:12px">Keys of the manager's desk</h2>
<table><tr><td><kbd>Enter</kbd></td><td>play next game, or open the highlighted option</td></tr>
<tr><td><kbd>↑</kbd><kbd>↓</kbd></td><td>move the highlight</td></tr>
<tr><td><kbd>Space</kbd> <kbd>T</kbd></td><td>select squad · team tactics</td></tr>
<tr><td><kbd>F3</kbd> <kbd>F4</kbd></td><td>replay a saved goal · open a saved match summary</td></tr>
<tr><td><kbd>F7</kbd> <kbd>F10</kbd></td><td>save · quit</td></tr></table>
<p class="sub">Each screen lists its keys on the bottom bar; this page adds what they do. The original's own help text
(GOAL.HLP) is shown below the keys when the player has it.</p>
<div class="row"><span class="btn primary">Close <kbd>Esc</kbd></span></div></div></div>'''
    body = '<div class="col grow"><section class="box grow"><h2>Manager\'s desk</h2></section></div>' + strip()
    return page("Help", body, [("Esc", "close")], None, crumb="help", overlay=over)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--render", metavar="CHROME", help="render each page to ../images/<name>.png")
    args = parser.parse_args(argv)
    IMAGES.mkdir(exist_ok=True)
    for name, fn in SCREENS.items():
        path = HERE / f"{name}.html"
        path.write_text(fn(), encoding="utf-8")
        if args.render:
            out = IMAGES / f"{name}.png"
            subprocess.run([args.render, "--headless", "--no-sandbox", "--hide-scrollbars", "--force-device-scale-factor=1",
                            "--window-size=1440,900", f"--screenshot={out}", path.as_uri()],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
