// A model named for a review (CLAUDE.md "Choosing models", the owner, 2026-10-11).
// harness.json's keys stay as short names; any other name of the form `provider/model`, with an
// optional `@variant`, is taken as the OpenCode model id the user chose. Its family, for the
// reviewer-family rule, is read from the model's own name. harness.json's blocked list is refused
// ("Choosing models" rule 3); Alibaba runs only when named, which this is.

// The one classifier of model ids (Sol's round-1 R2 on PR 149: switch.mjs kept a second one, and
// codex/chatgpt ids fell through here). switch.mjs and review.mjs both use it.
const FAMILIES = [
  [/^deepseek/, 'deepseek'],
  [/^longcat/, 'longcat'],
  [/^hy\d/, 'hunyuan'],
  [/^muse/, 'meta'],
  [/^glm/, 'glm'],
  [/^gemini|^gemma/, 'google'],
  [/^llama/, 'meta'],
  [/^kimi/, 'kimi'],
  [/^grok/, 'xai'],
  [/^(mistral|devstral|codestral|magistral)/, 'mistral'],
  [/^nemotron/, 'nvidia'],
  [/^mimo/, 'mimo'],
  [/^minimax/, 'minimax'],
  [/^(gpt|o\d|codex|chatgpt)/, 'openai'],
  [/^qwen/, 'qwen'],
  [/^(claude|opus|sonnet|haiku)/, 'claude'],
];

// Other spellings of a family, as harness.json entries or labels may carry them: the family rule
// compares canonical names only (Sol's R2 on PR 149: switch.mjs stored "anthropic", the session is
// "claude").
const ALIASES = { anthropic: 'claude', zhipu: 'glm', 'z-ai': 'glm', zai: 'glm', moonshot: 'kimi', moonshotai: 'kimi',
  xiaomi: 'mimo', alibaba: 'qwen', 'x-ai': 'xai', 'meta-llama': 'meta' };
export const canonicalFamily = (f) => { const k = String(f ?? '').trim().toLowerCase(); return ALIASES[k] ?? k; };

// The family of a model id, read from its last segment only, so that one model reached through two
// routes ("google/gemini-2.5-pro", "openrouter/google/gemini-2.5-pro") is one family (Sol's R1 on
// PR 114): a known prefix, else the segment's leading word ("acme-widget-1" -> acme), never the
// provider or route.
export function knownFamilyOfId(id) {
  const base = String(id).split('/').pop().toLowerCase();
  return FAMILIES.find(([re]) => re.test(base))?.[1] ?? null;
}
export function familyOfId(id) {
  const base = String(id).split('/').pop().toLowerCase();
  return knownFamilyOfId(id) ?? (base.match(/^[a-z]+/)?.[0] || base);
}

// The one blocked check (harness.json's `blocked`: a family or a piece of an id, case-insensitive):
// the entry `b` that blocks a model of these families or this id, or null.
export function blockedHit(blocked, { id, families = [] }) {
  const fams = families.map(canonicalFamily);
  return (blocked ?? []).map(String).find((b) => fams.includes(canonicalFamily(b))
    || (id && String(id).toLowerCase().includes(b.toLowerCase()))) ?? null;
}

// harness.json's entry for `name`, else the model `name` spells, else null. Throws on a model in
// `blocked` (harness.json's list: a family name or a piece of an id, case-insensitive).
export function namedModel(name, models, blocked = []) {
  const known = models[name];
  const m = known ? null : /^([\w.-]+\/[^@\s]+)(?:@([\w.-]+))?$/.exec(name);
  if (!known && !m) return null;
  const id = known ? known.id : m[1];
  const entry = known ?? { id, family: familyOfId(id), ...(m[2] ? { variant: m[2] } : {}) };
  const hit = blockedHit(blocked, { id, families: familiesOfModel(entry) });
  if (hit) throw new Error(`${name}: blocked in harness.json ("${hit}"; switch-model.mjs --unblock ${hit} lifts it).`);
  return entry;
}

// The family of a name as review.mjs meets it (a harness.json key, a model id, or a bare family
// from a `model:` label), canonical.
export function familyOfName(name, models) {
  return familiesOfName(name, models)[0];
}

// Every family a name stands for: a harness.json key is its stored family and its id's (Sol's
// round-1 R3 on PR 149: a forced `family` hid an implementer's), an id its own, a bare word itself.
export function familiesOfName(name, models) {
  // a bare name is also the family it spells, even when a harness.json key shares it (Sol's
  // round-2 R1: a key named `claude` holding an OpenAI model replaced the family claude)
  if (models[name]) return [...new Set([...familiesOfModel(models[name]), ...(name.includes('/') ? [] : [canonicalFamily(name)])])];
  return [canonicalFamily(name.includes('/') ? familyOfId(name.replace(/@.*$/, '')) : name)];
}

// Every family a reviewer entry belongs to: its stored family and the one its id spells, both
// canonical, so that no stored `family` (an alias, or one forced with --force) carries a model past
// the family rule (Sol's R2 on PR 149).
export function familiesOfModel(entry) {
  return [...new Set([familyOfId(entry.id), canonicalFamily(entry.family)].filter(Boolean))];
}

export function selfTest() {
  const failures = [];
  const ok = (what, cond) => { if (!cond) failures.push(what); };
  const models = { luna: { id: 'openai/gpt-5.6-luna', family: 'openai' } };
  ok('a harness.json key is its entry', namedModel('luna', models) === models.luna);
  const sol = namedModel('openai/gpt-6.1-sol@low', models);
  ok('a named id keeps its id', sol?.id === 'openai/gpt-6.1-sol');
  ok('a named id keeps its variant', sol?.variant === 'low');
  ok('a named id without variant has none', !('variant' in namedModel('minimax/MiniMax-M3', models)));
  ok('MiniMax family', namedModel('minimax/MiniMax-M3', models).family === 'minimax');
  ok('family from the last segment', namedModel('openrouter/xiaomi/mimo-v2.6-pro', models).family === 'mimo');
  ok('GLM on Alibaba is glm', namedModel('alibaba-token-plan/glm-5.3', models).family === 'glm');
  ok('an unknown model is its leading word', namedModel('acme/widget-1', models).family === 'widget');
  ok('one model on two routes is one family (Sol R1, PR 114)',
    namedModel('google/gemini-2.5-pro', models).family === namedModel('openrouter/google/gemini-2.5-pro', models).family);
  ok('an unknown model on two routes is one family',
    namedModel('acme/widget-1', models).family === namedModel('openrouter/acme/widget-1', models).family);
  ok('a bare unknown word is not a model', namedModel('sonnet-ish', models) === null);
  let threw = false;
  try { namedModel('opencode-go/deepseek-v4-pro', models, ['deepseek']); } catch { threw = true; }
  ok('a blocked family is refused', threw);
  ok('an unblocked model passes', namedModel('opencode-go/deepseek-v4-pro', models).family === 'deepseek');
  let threwId = false;
  try { namedModel('luna', models, ['gpt-5.6']); } catch { threwId = true; }
  ok('a blocked id fragment is refused', threwId);
  ok('label with an id maps to its family', familyOfName('openai/gpt-6.1-sol@low', models) === 'openai');
  ok('label with a key maps to its family', familyOfName('luna', models) === 'openai');
  ok('a bare family stays itself', familyOfName('minimax', models) === 'minimax');
  ok('anthropic is claude', familyOfName('anthropic', models) === 'claude'
    && familyOfName('x', { x: { id: 'anthropic/claude-sonnet-4-5', family: 'anthropic' } }) === 'claude');
  const forced = familiesOfModel({ id: 'openai/gpt-5.6-luna', family: 'other' });
  ok('a forced family keeps the id\'s family too', forced.includes('openai') && forced.includes('other'));
  ok('a Claude id is claude', familiesOfModel({ id: 'anthropic/claude-sonnet-4-5', family: 'anthropic' }).join() === 'claude');
  return failures;
}
