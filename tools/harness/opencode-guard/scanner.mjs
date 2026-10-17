// [confirmed: OpenCode v1.18.32 packages/opencode/src/tool/shell.ts; rework1 source hashes]
// Copyright (c) 2025 opencode; MIT notice retained in LICENSE.opencode.
// Adapt its FILES/path operand selection, retaining best-effort static-path semantics, not an OS jail.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { Parser, Language } from 'web-tree-sitter';
const require = createRequire(import.meta.url);
const CWD = new Set(["cd", "chdir", "popd", "pushd", "push-location", "set-location"])
const FILES = new Set([
  ...CWD,
  "rm",
  "cp",
  "mv",
  "mkdir",
  "touch",
  "chmod",
  "chown",
  "cat",
  // Leave PowerShell aliases out for now. Common ones like cat/cp/mv/rm/mkdir
  // already hit the entries above, and alias normalization should happen in one
  // place later so we do not risk double-prompting.
  "get-content",
  "set-content",
  "add-content",
  "copy-item",
  "move-item",
  "remove-item",
  "new-item",
  "rename-item",
])
const CMD_FILES = new Set([
  "copy",
  "del",
  "dir",
  "erase",
  "md",
  "mkdir",
  "move",
  "rd",
  "ren",
  "rename",
  "rmdir",
  "type",
])
const FLAGS = new Set(["-destination", "-literalpath", "-path"])
const SWITCHES = new Set(["-confirm", "-debug", "-force", "-nonewline", "-recurse", "-verbose", "-whatif"])

function parts(node) {
  const out = []
  for (let i = 0; i < node.childCount; i++) {
    const child = node.child(i)
    if (!child) continue
    if (child.type === "command_elements") {
      for (let j = 0; j < child.childCount; j++) {
        const item = child.child(j)
        if (!item || item.type === "command_argument_sep" || item.type === "redirection") continue
        out.push({ type: item.type, text: item.text })
      }
      continue
    }
    if (
      child.type !== "command_name" &&
      child.type !== "command_name_expr" &&
      child.type !== "word" &&
      child.type !== "string" &&
      child.type !== "raw_string" &&
      child.type !== "concatenation"
    ) {
      continue
    }
    out.push({ type: child.type, text: child.text })
  }
  return out
}

function unquote(text) {
  if (text.length < 2) return text
  const first = text[0]
  const last = text[text.length - 1]
  if ((first === '"' || first === "'") && first === last) return text.slice(1, -1)
  return text
}

function home(text) {
  if (text === "~") return os.homedir()
  if (text.startsWith("~/") || text.startsWith("~\\")) return path.join(os.homedir(), text.slice(2))
  return text
}

function envValue(key) {
  if (process.platform !== "win32") return process.env[key]
  const name = Object.keys(process.env).find((item) => item.toLowerCase() === key.toLowerCase())
  return name ? process.env[name] : undefined
}

function auto(key, cwd, shell) {
  const name = key.toUpperCase()
  if (name === "HOME") return os.homedir()
  if (name === "PWD") return cwd
  if (name === "PSHOME") return path.dirname(shell)
}

function expand(text, cwd, shell) {
  const out = unquote(text)
    .replace(/\$\{env:([^}]+)\}/gi, (_, key) => envValue(key) || "")
    .replace(/\$env:([A-Za-z_][A-Za-z0-9_]*)/gi, (_, key) => envValue(key) || "")
    .replace(/\$(HOME|PWD|PSHOME)(?=$|[\\/])/gi, (_, key) => auto(key, cwd, shell) || "")
  return home(out)
}

function provider(text) {
  const match = text.match(/^([A-Za-z]+)::(.*)$/)
  if (match) {
    if (match[1].toLowerCase() !== "filesystem") return
    return match[2]
  }
  const prefix = text.match(/^([A-Za-z]+):(.*)$/)
  if (!prefix) return text
  if (prefix[1].length === 1) return text
  return
}

function dynamic(text, ps) {
  if (text.startsWith("(") || text.startsWith("@(")) return true
  if (text.includes("$(") || text.includes("${") || text.includes("`")) return true
  if (ps) return /\$(?!env:)/i.test(text)
  return text.includes("$")
}

function prefix(text) {
  const match = /[?*[]/.exec(text)
  if (!match) return text
  if (match.index === 0) return
  return text.slice(0, match.index)
}

function pathArgs(list, ps, cmd = false) {
  if (!ps) {
    return list
      .slice(1)
      .filter(
        (item) =>
          !item.text.startsWith("-") &&
          !(cmd && item.text.startsWith("/")) &&
          !(list[0]?.text === "chmod" && item.text.startsWith("+")),
      )
      .map((item) => item.text)
  }

  const out = []
  let want = false
  for (const item of list.slice(1)) {
    if (want) {
      out.push(item.text)
      want = false
      continue
    }
    if (item.type === "command_parameter") {
      const flag = item.text.toLowerCase()
      if (SWITCHES.has(flag)) continue
      want = FLAGS.has(flag)
      continue
    }
    out.push(item.text)
  }
  return out
}


let ready;
async function parsers() {
  return ready ||= (async () => {
    await Parser.init();
    const root = name => path.dirname(require.resolve(name + '/package.json'));
    const bash = new Parser();
    bash.setLanguage(await Language.load(path.join(root('tree-sitter-bash'), 'tree-sitter-bash.wasm')));
    const ps = new Parser();
    ps.setLanguage(await Language.load(path.join(root('tree-sitter-powershell'), 'tree-sitter-powershell.wasm')));
    return { bash, ps };
  })();
}
export function contains(root, file) {
  const relative = path.relative(root, file);
  return relative === '' || (relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative));
}
// [confirmed: native2.0.28 util/wildcard.ts; source hashes] Same ordered-rule matching semantics.
export function matches(input, pattern) {
  const normalized = input.replaceAll('\\', '/');
  let escaped = pattern.replaceAll('\\', '/').replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '.*').replace(/\?/g, '.');
  if (escaped.endsWith(' .*')) escaped = escaped.slice(0, -3) + '( .*)?';
  return new RegExp('^' + escaped + '$', process.platform === 'win32' ? 'si' : 's').test(normalized);
}
export function externalEffect(directory, rules) {
  const resource = path.join(directory, '*').replaceAll('\\', '/');
  return rules.findLast(rule => rule.action === 'external_directory' && matches(resource, rule.resource))?.effect || 'ask';
}
export async function operandDirectories(command, cwd, roots, shell = process.platform === 'win32' ? 'powershell.exe' : '/bin/bash') {
  if (typeof command !== 'string' || typeof cwd !== 'string' || !path.isAbsolute(cwd)) throw Error('malformed shell scan input');
  const ps = /(?:powershell|pwsh)(?:\.exe)?$/i.test(shell);
  const cmd = /(?:^|[\\/])cmd\.exe$/i.test(shell);
  const parser = await parsers();
  const tree = (ps ? parser.ps : parser.bash).parse(command);
  if (!tree || tree.rootNode.hasError) {
    tree?.delete();
    throw Error('unsupported shell grammar');
  }
  const directories = new Set();
  try {
    for (const node of tree.rootNode.descendantsOfType('command')) {
      const list = parts(node);
      const name = ps || cmd ? list[0]?.text.toLowerCase() : list[0]?.text;
      if (!FILES.has(name) && !(cmd && CMD_FILES.has(name))) continue;
      for (const arg of pathArgs(list, ps, cmd)) {
        const text = ps ? expand(arg, cwd, shell) : home(unquote(arg));
        const file = text && prefix(text);
        if (!file || dynamic(file, ps)) continue;
        const next = ps ? provider(file) : file;
        if (!next) continue;
        const absolute = path.resolve(cwd, next);
        if (roots.some(root => contains(root, absolute))) continue;
        const isDirectory = await fs.stat(absolute).then(stat => stat.isDirectory()).catch(error => {
          if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return false;
          throw error;
        });
        directories.add(isDirectory ? absolute : path.dirname(absolute));
      }
    }
    return [...directories];
  } finally { tree.delete(); }
}
