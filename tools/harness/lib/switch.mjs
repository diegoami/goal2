// Switching the defaults in harness.json, kept free of OpenCode and git so it can be tested directly;
// switch-model.mjs runs the checks that need OpenCode. The roster is the owner's to change (the
// owner, 2026-10-11), through this script and the /switch-model skill:
// [designed: T24] Codex defaults are separate (defaultsByClient.codex), session or native OpenAI IDs.
// The legacy Claude branch remains:
// - implementer.default: a Claude Code model alias (sonnet, opus, haiku, fable) or any model id the
//   session's provider serves, on which the `implementer` subagent is spawned (Opus spawns Sonnet;
//   under Z.AI `sonnet` is GLM-5.3 Flash); or `session`, the main session implementing directly
//   where the provider cannot spawn one. Either runs through the session's Anthropic environment,
//   so its family is the session's (lib/common.mjs sessionFamily).
// - reviewer.default: a harness.json key, the OpenCode model that reviews unless the user names
//   another; never the session's family.
// - blocked: families or id fragments that never run (--block / --unblock).

import { canonicalFamily, familiesOfModel, familyOfId, knownFamilyOfId, blockedHit } from './named.mjs';

export const ROLES = ['implementer', 'reviewer'];
export const IMPLEMENTER_ALIASES = ['sonnet', 'opus', 'haiku', 'fable'];
export const IMPLEMENTER_CHOICES = ['session', ...IMPLEMENTER_ALIASES];

// [designed: T24] A Codex default never overwrites Claude's existing alias/default.
export const implementerDefault = (config, client = 'claude') => client === 'codex'
  ? config.implementer?.defaultsByClient?.codex ?? 'session'
  : config.implementer?.default ?? 'session';

// A model's family, from its id: the family rule (L3) compares these, by named.mjs's one classifier
// (the vendor, not the route: "opencode-go/gpt-6-luna" and "openai/gpt-6-luna" are both openai).
// knownFamilyOf is null for an unknown vendor: only then may --family name it.
export const knownFamilyOf = (id) => knownFamilyOfId(id);
export const familyOf = (id) => familyOfId(id);

// Heavy models run at `low`, or `medium` at most; light ones at `high` (L54, #83). Heavy: Sol, GLM-5.3
// (not Flash), DeepSeek V4 Pro, MiMo V2.6 Pro, Opus, wherever they are served from (DeepSeek is
// blacklisted since 2026-10-09, but still recognised).
// Exactly the models the rule names (Sol's R2 on PR 94): another GLM or DeepSeek release is not heavy.
// A dated suffix is the same model, not a release: deepseek-v4-pro-0813 (the only Alibaba id with
// the night discount) is the named DeepSeek V4 Pro.
// Qwen 3.8 Max is the heavy model of Alibaba's Token Plan (the owner, 2026-10-05).
// MiniMax-M3 is the heavy model of the MiniMax Token Plan (the owner, 2026-10-06); its ladder
// is none/thinking, not the effort ladder, so its entry pins `thinking` itself.
const HEAVY = [/(^|\/)gpt-[\d.]+-sol(-fast)?$/, /(^|\/)glm-5\.3$/, /(^|\/)deepseek-v4-pro(-\d+)?$/, /(^|\/)mimo-v2\.6-pro$/, /(^|\/)qwen3\.8-max$/, /(^|\/)minimax-m3$/, /(^|\/)claude-opus/, /(^|\/)opus$/];
// the id's model part, past its provider (Sol's round-2 R3 on PR 149: lost with the second classifier)
const modelPart = (id) => String(id).split('/').slice(1).join('/').toLowerCase();
export const isHeavy = (id) => HEAVY.some((re) => re.test(modelPart(id)));
const EFFORTS = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'];

// The effort a switch writes when --variant is not given, from the efforts OpenCode offers for the
// model (`offered`, from `opencode models --verbose`; null when unknown): a light model `high`; a
// heavy one `low`, else `medium`, else its lowest effort (DeepSeek V4 Pro offers only high and max).
// A model whose variants are not the effort ladder keeps its own (MiniMax-M3 offers none/thinking,
// so it gets `thinking`); one that offers none at all (MiniMax-M2.7) gets no variant. A light model
// that offers no plain `high` gets the nearest below it (Qwen 3.8 Flash: `medium`).
export function defaultVariant(id, offered) {
  if (!offered) return isHeavy(id) ? 'low' : 'high';
  // Ranked, not in the order OpenCode lists them (Sol's R1 on PR 94).
  const usable = EFFORTS.filter((v) => offered.includes(v) && v !== 'none' && v !== 'max');
  if (!usable.length) {
    const own = offered.filter((v) => v !== 'none');
    return own.length ? own[0] : undefined;
  }
  if (isHeavy(id)) return ['low', 'medium'].find((v) => usable.includes(v)) ?? usable[0];
  const belowHigh = usable.filter((v) => EFFORTS.indexOf(v) < EFFORTS.indexOf('high'));
  return usable.includes('high') ? 'high' : belowHigh.at(-1) ?? usable.at(-1);
}

// The harness.json name for an id: the existing entry's, else the id's model part.
export function nameOf(config, id) {
  const found = Object.entries(config.models ?? {}).find(([, m]) => m.id === id);
  return found ? found[0] : String(id).split('/').slice(1).join('/').toLowerCase().replace(/[^a-z0-9.-]+/g, '-');
}

/**
 * The new harness.json for making `id` the default reviewer: the entry is added or updated,
 * reviewer.default becomes its name, and every other model stays for an explicit --reviewer. A
 * model of the session's family (`sessionFamily`, the implementer's) or on the blocked list is
 * refused. A `family` that contradicts a known vendor in the id is refused too, so --family can
 * never carry a model past the family rule (Luna's R1 on PR 17).
 * Returns { config, name, entry, before, after } or throws with the reason.
 */
export function planSwitch(config, { role = 'reviewer', id, variant, name, family, force = false, sessionFamily = 'claude', client = 'claude' }) {
  if (!ROLES.includes(role)) throw new Error(`--role must be one of ${ROLES.join(', ')}; got ${role}`);
  if (!['codex', 'claude'].includes(client)) throw new Error('Refused: unknown implementation client; set HARNESS_CLIENT=codex or claude.');
  if (role === 'implementer') return planImplementer(config, id, sessionFamily, client);
  // `variant` has no default: a model that offers no variants (MiniMax-M2.7) must switch without
  // one, not inherit 'high' (Luna's round-2 R1, PR 115). Callers pass defaultVariant's answer.
  if (!/^[\w.-]+\/[\w./-]+$/.test(String(id ?? ''))) throw new Error(`--model must be a provider/model id, e.g. openai/gpt-5.6-luna; got ${id}`);
  if (variant === 'max') throw new Error('Effort max is never used: it was slower with no gain (L27). Use high.');
  const n = name ?? nameOf(config, id);
  const existing = config.models?.[n];
  if (existing && existing.id !== id) throw new Error(`The name ${n} already holds ${existing.id}; pass --name for ${id}.`);
  const known = knownFamilyOf(id);
  if (family && known && family !== known && !force) {
    throw new Error(`Refused: --family ${family} contradicts ${id}, whose vendor is ${known}; the family rule compares vendors. Drop --family, or pass --force.`);
  }
  const entry = { id, ...(variant !== undefined && variant !== null ? { variant } : {}), family: family ?? existing?.family ?? familyOf(id), ...(existing?.note ? { note: existing.note } : {}) };
  const blocked = blockedBy(config, entry);
  if (blocked) throw new Error(`Refused: ${blocked}.`);
  const own = String(sessionFamily ?? '').toLowerCase();
  const same = [...familiesOfModel(entry), known].filter(Boolean).some((f) => canonicalFamily(f) === canonicalFamily(own));
  if (same) throw new Error(`Refused: ${id} is of the session's family (${own}), which implements; the reviewer is never the implementer's family. Set HARNESS_SESSION_FAMILY if the session runs elsewhere.`);
  const next = structuredClone(config);
  next.models = { ...next.models, [n]: entry };
  next.reviewer = { ...next.reviewer, default: n };
  return { config: next, name: n, entry, before: describeReviewer(config), after: describeReviewer(next) };
}

// The implementer's default: the implementer subagent on a Claude Code alias or a model id the
// session's provider serves, or `session` (the main session implements directly). A model id is
// taken as given: the next run shows whether the provider honours it.
function planImplementer(config, choice, sessionFamily, client) {
  const c = String(choice ?? '').trim();
  const lower = c.toLowerCase();
  if (!IMPLEMENTER_CHOICES.includes(lower) && !/^[\w.:-]+$/.test(c)) {
    throw new Error(`--model for the implementer is session, one of ${IMPLEMENTER_ALIASES.join(', ')}, or a model id the session's provider serves; got ${choice}`);
  }
  const value = IMPLEMENTER_CHOICES.includes(lower) ? lower : c;
  // [designed: T24] Native Codex model IDs, not Claude aliases or OpenCode routes.
  if (client === 'codex' && (canonicalFamily(sessionFamily) !== 'openai'
      || (value !== 'session' && knownFamilyOfId(value) !== 'openai'))) {
    throw new Error(`Refused: Codex implements with session or a native OpenAI model ID; got ${value} (family ${sessionFamily}).`);
  }
  // the blocked list holds for the implementer too (Sol's R3 on PR 149): a model id by its own
  // family and name; an alias or `session` by the session's family, whose endpoint serves it
  // (Sol's round-1 R1: a DeepSeek endpoint's `sonnet` was accepted)
  // every implementer choice runs on the session's endpoint (Sol's round-2 R2: a model id skipped
  // this), and a model id is also checked by its own family and name
  if (!sessionFamily) throw new Error(`Refused: ${value} runs on the session's endpoint, whose family cannot be told; set HARNESS_SESSION_FAMILY.`);
  const onSession = blockedBy(config, { family: canonicalFamily(sessionFamily) });
  if (onSession) throw new Error(`Refused: ${value} runs on the session's endpoint, and ${onSession}.`);
  if (!IMPLEMENTER_CHOICES.includes(lower)) {
    const blocked = blockedBy(config, { id: value, family: familyOfId(value) });
    if (blocked) throw new Error(`Refused: ${blocked}.`);
  }
  const next = structuredClone(config);
  next.implementer = client === 'codex'
    ? { ...next.implementer, defaultsByClient: { ...next.implementer?.defaultsByClient, codex: value } }
    : { ...next.implementer, default: value };
  return { config: next, name: value, entry: { id: value }, before: describeImplementer(config, client), after: describeImplementer(next, client) };
}

// harness.json's blocked list (named.mjs blockedHit): the reason, or null. An entry is checked by
// every family it stands for and its id.
export function blockedBy(config, entry) {
  const families = entry.id ? familiesOfModel(entry) : [entry.family].filter(Boolean);
  const b = blockedHit(config.blocked, { id: entry.id, families });
  return b ? `${entry.id ?? entry.family} is blocked in harness.json ("${b}"; --unblock ${b} lifts it)` : null;
}

// --block / --unblock: the new harness.json, or throws when nothing changes.
export function planBlock(config, { block, unblock }) {
  const list = [...(config.blocked ?? [])];
  const has = (x) => list.some((b) => b.toLowerCase() === x.toLowerCase());
  if (block) {
    if (has(block)) throw new Error(`${block} is already blocked.`);
    list.push(block);
  }
  if (unblock) {
    if (!has(unblock)) throw new Error(`${unblock} is not blocked (blocked: ${list.join(', ') || 'nothing'}).`);
    list.splice(list.findIndex((b) => b.toLowerCase() === unblock.toLowerCase()), 1);
  }
  const next = { ...structuredClone(config), blocked: list };
  const hit = next.reviewer?.default && next.models?.[next.reviewer.default] ? blockedBy(next, next.models[next.reviewer.default]) : null;
  if (hit) throw new Error(`Refused: the default reviewer would be blocked (${hit}); switch the reviewer first.`);
  return { config: next, before: `blocked: ${(config.blocked ?? []).join(', ') || 'nothing'}`, after: `blocked: ${list.join(', ') || 'nothing'}` };
}

const describeReviewer = (c) => {
  const d = c.reviewer?.default;
  const e = c.models?.[d];
  return d ? `reviewer: ${d} (${e?.id ?? '?'}, ${e?.variant ?? 'no variant'}, family ${e?.family ?? '?'})` : 'reviewer: (none)';
};
const describeImplementer = (c, client = 'claude') => {
  const d = implementerDefault(c, client);
  const route = client === 'codex' ? 'native Codex, family openai' : "the session's family, through its endpoint";
  return `implementer: ${d === 'session' ? 'the main session, directly' : `the implementer subagent on ${d}`} (${route})`;
};

// What runs now: the session's family, both defaults, the blocked list, then the other models
// registered for an explicit --reviewer.
export function showRoles(config, { sessionFamily = null, client = 'claude' } = {}) {
  const d = config.reviewer?.default;
  const others = Object.entries(config.models ?? {}).filter(([m]) => m !== d).map(([m, x]) => `${m} = ${x.id}`);
  return [
    `session: client ${client ?? 'unknown'}, family ${sessionFamily ?? 'unknown (check HARNESS_CLIENT / HARNESS_SESSION_FAMILY)'}`,
    describeImplementer(config, client), describeReviewer(config),
    ...(config.models?.[d] && familiesOfModel(config.models[d]).includes(canonicalFamily(sessionFamily))
      ? ['default reviewer is of the implementer family; ask the owner for another --reviewer after the PR exists'] : []),
    `blocked: ${(config.blocked ?? []).join(', ') || 'nothing'}`,
    ...(others.length ? [`also registered, for --reviewer: ${others.join(', ')}`] : []),
  ].join('\n');
}
