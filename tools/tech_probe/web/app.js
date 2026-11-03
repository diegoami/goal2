// [designed: T158] The web candidate's prototype: S06 manager's desk, S16 choose your captain, S17 kick-off.
// Keys and mouse as the approved design (docs/design/ui-2026-11/README.md); markup as its mockups. Throwaway.
"use strict";
let D = null;
const S = { screen: "desk", cursor: 0, pick: 0, notice: "", t0: performance.now() };
const page = document.getElementById("page");
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function fit() {
  const s = Math.min(innerWidth / 1440, innerHeight / 900);
  page.style.transform = `scale(${s})`;
  page.style.left = `${(innerWidth - 1440 * s) / 2}px`;
  page.style.top = `${(innerHeight - 900 * s) / 2}px`;
}
addEventListener("resize", fit);

const rc = (line, code) => `<span class="rc ${line}">${esc(code)}</span>`;
const kv = (pairs) => `<dl class="kv">${pairs.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`;
const bars = (rows) => `<div class="bars">${rows.map(([n, v, w]) =>
  `<span>${esc(n)}</span><span class="bar"><i style="width:${Math.round(v * 11.1)}%"></i></span>` +
  (w ? `<span class="word">${esc(w)}</span>` : `<span class="muted">${v}</span>`)).join("")}</div>`;
const keys = (items, primary) => `<footer class="keys">${items.map(([k, label]) =>
  `<span class="kk">${k.map((x) => `<kbd>${esc(x)}</kbd>`).join("")} ${esc(label)}</span>`).join("")}` +
  (S.notice ? `<span class="kk notice" role="status">${esc(S.notice)}</span>` : "") +
  `<span class="btn primary" id="enter" role="button" tabindex="-1">${esc(primary)} <kbd>Enter</kbd></span></footer>`;

function desk() {
  const menu = D.menu.map(([label, sub, key], i) =>
    `<div class="item${i === S.cursor ? " on" : ""}" role="menuitem" aria-selected="${i === S.cursor}" data-i="${i}">${esc(label)}` +
    (sub ? `<span class="sub" style="margin-left:14px">${esc(sub)}</span>` : "") +
    `<span class="k">${key ? `<kbd>${esc(key)}</kbd>` : ""}</span></div>`).join("");
  const squad = D.squad.map(([l, c, n], i) => (i === 11 ? '<li class="sep"></li>' : "") + `<li>${rc(l, c)} ${esc(n)}</li>`).join("");
  return `<header class="top"><span class="brand">GOAL2</span><span class="who">manager's desk</span>
    <span class="comp" style="margin-left:auto"><b>2028</b> European Championship · <b>QUALIFYING</b></span></header>
    <main><div class="col" style="width:420px">
    <section class="box"><h2>Manager</h2>${kv([["name", "K Ees"], ["rating", "unknown"]])}</section>
    <section class="box"><h2>Team</h2><div class="big">Holland</div>${kv([["world", 14], ["Europe", 3]])}</section>
    <section class="box"><h2>Next opponents</h2><div class="big sel">Norway</div>${kv([["world", 32], ["Europe", 18], ["match", "friendly · away"]])}</section>
    <section class="box"><h2>Managers</h2><div>1 · K Ees <span class="muted">(Holland)</span></div></section></div>
    <div class="col grow"><div class="menu" role="menu" aria-label="Manager's desk">${menu}</div>
    <p class="sub" style="margin:0">Use ↑↓ to find an option, Enter to select it. Your own matches are watched: play
    next game leads to the match menu, the captain and the pitch.</p></div>
    <section class="box strip"><h2>Holland</h2><ul class="list">${squad}</ul></section></main>` +
    keys([[["F1"], "help"], [["F3"], "load goal"], [["F4"], "load summary"], [["F7"], "save"], [["F10"], "quit"],
          [["T"], "team tactics"], [["↑", "↓"], "choose"]], D.menu_hint[S.cursor]);
}

function captain() {
  const c = D.eleven[S.pick];
  const eleven = D.eleven.map((p, i) =>
    `<li class="${i === S.pick ? "on" : ""}" role="option" aria-selected="${i === S.pick}" data-i="${i}">${rc(p.line, p.code)} ${esc(p.name)}</li>`).join("");
  const h3 = (t) => `<h3 style="margin:0 0 8px;color:var(--frame);font-size:16px">${t}</h3>`;
  return `<header class="top"><span class="brand">GOAL2</span><span class="who">Norway v Holland · captain</span></header>
  <main><div class="col grow">
  <section class="box" style="display:flex;align-items:center;gap:20px;border-color:var(--select)">
   <span class="big sel" style="white-space:nowrap">Choose your captain to kick off</span>
   <span class="sub">The match starts as soon as a captain is chosen. The highlight starts on the computer's pick. Enter: the
   highlighted player · C: computer select · no key: the computer's pick stands after the original's wait.</span></section>
  <div style="display:flex;gap:18px" class="grow">
   <section class="box grow col" style="gap:12px">
    <div style="display:flex;align-items:baseline;gap:16px">${rc(c.line, c.code)}<h1>${esc(c.name)}</h1>
      <span class="sub">${esc(c.facts)}</span><span style="margin-left:auto;color:var(--good)">ready to play</span></div>
    <div class="sub">position <b style="color:var(--text)">${esc(c.position)}</b> · club position <b style="color:var(--text)">${esc(c.position)}</b> · cards <b style="color:var(--text)">none</b></div>
    <div style="display:flex;gap:24px;min-height:0">
     <div class="grow">${h3("SKILLS")}${bars(c.skills)}</div>
     <div style="width:380px" class="col"><div>${h3("TACTICS")}${kv(c.tactics)}</div>
      <div>${h3("CHARACTERISTICS")}${bars(c.characteristics.map(([n, v, w]) => [n, v + 1, w]))}</div></div></div>
   </section>
   <section class="box" style="width:300px"><h2>Holland's eleven</h2><ul class="list" role="listbox" aria-label="Holland's eleven">${eleven}</ul></section>
  </div></div></main>` + keys([[["↑", "↓"], "player"], [["C"], "computer select"], [["Esc"], "desk (prototype only)"]], "Captain: kick off");
}

function kickoff() {
  const players = (side, cls) => side.map(([x, y, c]) => `<div class="p ${cls}" style="left:${x}%;top:${y}%">${esc(c)}</div>`).join("");
  return `<header class="top"><span class="brand">GOAL2</span><span class="who">watching · Norway v Holland</span></header>
  <main><div class="col grow"><section class="box" style="display:flex;align-items:center;gap:30px;padding:10px 18px">
   <div class="score"><span style="color:var(--home)">Norway</span><span class="s">0</span><span class="s">0</span><span>Holland</span></div>
   <span class="big" style="font-size:32px">1′</span><span class="sub">FRIENDLY</span>
   <div style="margin-left:auto;text-align:right">${D.commentary.map((c) => `<div>${esc(c.slice(3))}</div>`).join("")}</div></section>
  <div style="display:flex;gap:18px" class="grow"><div><div class="pitch" style="width:1000px;height:560px">
   <div class="line" style="left:50%;top:0;bottom:0;border-width:0 0 0 2px"></div>
   <div class="line" style="left:0;top:25%;width:15%;height:50%;border-left:0"></div>
   <div class="line" style="right:0;top:25%;width:15%;height:50%;border-right:0"></div>
   <div class="line" style="left:calc(50% - 60px);top:calc(50% - 60px);width:120px;height:120px;border-radius:50% !important"></div>
   ${players(D.away, "v")}${players(D.home, "h")}<div class="ball" id="ball" style="left:51%;top:50%"></div></div></div>
  <section class="box grow"><h2>Commentary</h2><ul class="list" style="font-size:16px">${D.commentary.map((c) => `<li>${esc(c)}</li>`).join("")}
   <li>1′ ${esc(D.eleven[S.pick].name)} captains Holland</li></ul>
   <p class="sub" style="margin:14px 0 0">Speed »»»»» · marks: positions · <span class="tag">your side: white</span></p></section></div></div></main>` +
   keys([[["↑", "↓"], "display"], [["←", "→"], "speed"], [["R"], "result"], [["Space"], "commentary"], [["F9"], "sound"]], "Bench (Esc: desk in the prototype)");
}

function render() {
  page.innerHTML = { desk, captain, kickoff }[S.screen]();
  document.title = { desk: "Manager's desk", captain: "Captain", kickoff: "Pitch" }[S.screen];
}

function animate() {
  const ball = document.getElementById("ball");
  if (ball) {
    const t = (performance.now() - S.t0) / 1000;
    ball.style.left = `${50 + 9 * Math.cos(t * 1.3)}%`;
    ball.style.top = `${50 + 16 * Math.sin(t * 1.3)}%`;
  }
  requestAnimationFrame(animate);
}

function go(screen) { S.screen = screen; S.notice = ""; if (screen === "captain") S.pick = D.pick; render(); }
function activate() {
  if (S.cursor === D.play) go("captain");
  else { S.notice = `${D.menu_hint[S.cursor]}: not in the prototype`; render(); }
}

addEventListener("keydown", (e) => {
  const k = e.key;
  if (S.screen === "desk") {
    if (k === "ArrowDown") S.cursor = (S.cursor + 1) % D.menu.length;
    else if (k === "ArrowUp") S.cursor = (S.cursor + D.menu.length - 1) % D.menu.length;
    else if (k === "Enter") return activate();
    else if (k === " ") S.notice = "Select squad: not in the prototype";
    else if (/^F(1|3|4|7|10)$/.test(k) || k === "t" || k === "T") S.notice = `${k}: not in the prototype`;
    else return;
  } else if (S.screen === "captain") {
    if (k === "ArrowDown") S.pick = (S.pick + 1) % 11;
    else if (k === "ArrowUp") S.pick = (S.pick + 10) % 11;
    else if (k === "Enter") return go("kickoff");
    else if (k === "c" || k === "C") { S.pick = D.pick; return go("kickoff"); }
    else if (k === "Escape") return go("desk");
    else return;
  } else if (k === "Escape" || k === "Enter") return go("desk");
  else return;
  e.preventDefault();
  render();
});

page.addEventListener("click", (e) => {
  const item = e.target.closest("[data-i]");
  if (e.target.closest("#enter")) {
    if (S.screen === "desk") return activate();
    return go(S.screen === "captain" ? "kickoff" : "desk");
  }
  if (!item) return;
  const i = Number(item.dataset.i);
  if (S.screen === "desk") { S.cursor = i; return activate(); }
  if (S.screen === "captain") { S.pick = i; render(); }
});

fetch("/data.json").then((r) => r.json()).then((d) => {
  D = d;
  S.pick = d.pick;
  const q = new URLSearchParams(location.search);
  if (q.get("screen")) go(q.get("screen")); else render();
  fit();
  requestAnimationFrame(() => requestAnimationFrame(() => fetch("/ready", { method: "POST" }).catch(() => {})));
  animate();
});
