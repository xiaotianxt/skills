#!/usr/bin/env node

import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { dirname } from "node:path";
import { homedir } from "node:os";

const VERSION = "0.2.0";
const DEFAULT_CDP = "auto";
const DEFAULT_HELIUM_DATA_DIR = `${homedir()}/Library/Application Support/net.imput.helium`;
const DEFAULT_STATE =
  process.env.HELIUM_CDP_PIN_STATE ||
  `${homedir()}/.local/state/helium-cdp-pin/bindings.json`;

class UserError extends Error {}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.nextId = 1;
    this.pending = new Map();
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    this.ws.addEventListener("message", (event) => this.onMessage(event));
    this.ws.addEventListener("close", () => this.rejectAll("CDP WebSocket closed"));
    this.ws.addEventListener("error", () => this.rejectAll("CDP WebSocket error"));
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Timed out connecting to ${this.wsUrl}`)), 10_000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", () => {
        clearTimeout(timer);
        reject(new Error(`Failed to connect to ${this.wsUrl}`));
      }, { once: true });
    });
  }

  onMessage(event) {
    let text;
    if (typeof event.data === "string") {
      text = event.data;
    } else if (event.data instanceof ArrayBuffer) {
      text = Buffer.from(event.data).toString("utf8");
    } else {
      text = String(event.data);
    }

    let msg;
    try {
      msg = JSON.parse(text);
    } catch {
      return;
    }

    if (msg.id && this.pending.has(msg.id)) {
      const { resolve, reject, timer } = this.pending.get(msg.id);
      clearTimeout(timer);
      this.pending.delete(msg.id);
      if (msg.error) {
        reject(new Error(`${msg.error.message || "CDP error"} (${msg.error.code ?? "unknown"})`));
      } else {
        resolve(msg.result ?? {});
      }
    }
  }

  rejectAll(reason) {
    for (const [id, pending] of this.pending) {
      clearTimeout(pending.timer);
      pending.reject(new Error(`${reason} while waiting for request ${id}`));
    }
    this.pending.clear();
  }

  send(method, params = {}, sessionId = undefined) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("CDP WebSocket is not open");
    }
    const id = this.nextId++;
    const payload = sessionId
      ? { id, method, params, sessionId }
      : { id, method, params };
    const promise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Timed out waiting for ${method}`));
      }, 15_000);
      this.pending.set(id, { resolve, reject, timer });
    });
    this.ws.send(JSON.stringify(payload));
    return promise;
  }

  close() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
  }
}

function usage() {
  return `helium-cdp-pin ${VERSION}

Target-pinned Helium CDP helper. It attaches to an existing Helium Chromium CDP
endpoint and routes commands to one explicit page targetId.

Usage:
  helium-cdp-pin [--cdp auto|9223|ws://...] enable [--timeout <seconds>]
  helium-cdp-pin [--cdp auto|9223|ws://...] [--json] list
  helium-cdp-pin [--cdp auto|9223|ws://...] bind --label <name> (--target-id <id> | --url <url> | --url-prefix <prefix>)
  helium-cdp-pin [--cdp auto|9223|ws://...] eval (--label <name> | --target-id <id>) <js>
  helium-cdp-pin [--cdp auto|9223|ws://...] get (--label <name> | --target-id <id>) <url|title|target-id>
  helium-cdp-pin [--cdp auto|9223|ws://...] fill (--label <name> | --target-id <id>) <selector> <value>
  helium-cdp-pin [--cdp auto|9223|ws://...] click (--label <name> | --target-id <id>) <selector>
  helium-cdp-pin [--cdp auto|9223|ws://...] screenshot (--label <name> | --target-id <id>) <path>
  helium-cdp-pin [--cdp auto|9223|ws://...] snapshot (--label <name> | --target-id <id>)
  helium-cdp-pin detach --label <name>

Environment:
  HELIUM_CDP_PIN_STATE  Override binding state path.
`;
}

function parseArgs(argv) {
  const opts = {
    cdp: DEFAULT_CDP,
    json: false,
    command: null,
    args: [],
  };

  const rest = [...argv];
  while (rest.length > 0) {
    const arg = rest.shift();
    if (arg === "--help" || arg === "-h") {
      opts.command = "help";
      return opts;
    }
    if (arg === "--version" || arg === "-V") {
      opts.command = "version";
      return opts;
    }
    if (arg === "--cdp") {
      opts.cdp = needValue(rest, "--cdp");
      continue;
    }
    if (arg === "--json") {
      opts.json = true;
      continue;
    }
    if (arg.startsWith("--")) {
      throw new UserError(`Unknown option: ${arg}`);
    }
    opts.command = arg;
    opts.args = rest;
    return opts;
  }

  opts.command = "help";
  return opts;
}

function needValue(args, flag) {
  const value = args.shift();
  if (!value || value.startsWith("--")) {
    throw new UserError(`${flag} requires a value`);
  }
  return value;
}

function parseNamed(args) {
  const out = { rest: [] };
  const items = [...args];
  while (items.length > 0) {
    const arg = items.shift();
    if (arg === "--label") {
      out.label = needValue(items, "--label");
    } else if (arg === "--target-id") {
      out.targetId = needValue(items, "--target-id");
    } else if (arg === "--url") {
      out.url = needValue(items, "--url");
    } else if (arg === "--url-prefix") {
      out.urlPrefix = needValue(items, "--url-prefix");
    } else if (arg.startsWith("--")) {
      throw new UserError(`Unknown option: ${arg}`);
    } else {
      out.rest.push(arg, ...items);
      break;
    }
  }
  return out;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeHttpBase(cdp) {
  if (/^\d+$/.test(cdp)) {
    return `http://127.0.0.1:${cdp}`;
  }
  if (cdp.startsWith("http://") || cdp.startsWith("https://")) {
    return cdp.replace(/\/$/, "");
  }
  throw new UserError("--cdp must be auto, a port, an http(s) URL, or a ws(s) URL");
}

async function fetchJson(url) {
  let res;
  try {
    res = await fetch(url);
  } catch (error) {
    const cause = error.cause?.message || error.message;
    throw new UserError(
      `Could not reach Helium CDP at ${url}: ${cause}. Start Helium with CDP enabled or pass the correct --cdp port.`,
    );
  }
  if (!res.ok) {
    throw new Error(`GET ${url} failed with HTTP ${res.status}`);
  }
  return res.json();
}

async function getHttpCdpInfo(cdp) {
  const base = normalizeHttpBase(cdp);
  const version = await fetchJson(`${base}/json/version`);
  if (!version.webSocketDebuggerUrl) {
    throw new Error(`${base}/json/version did not return webSocketDebuggerUrl`);
  }
  return { base, wsUrl: version.webSocketDebuggerUrl, version };
}

async function readDevToolsActivePort(userDataDir = DEFAULT_HELIUM_DATA_DIR) {
  const path = `${userDataDir}/DevToolsActivePort`;
  try {
    const text = await readFile(path, "utf8");
    const lines = text.trim().split(/\r?\n/);
    const port = Number.parseInt(lines[0], 10);
    const wsPath = lines[1] || "/devtools/browser";
    if (!Number.isInteger(port) || port <= 0) {
      return null;
    }
    return { port, wsPath, path };
  } catch {
    return null;
  }
}

async function verifyWsEndpoint(wsUrl) {
  const client = new CdpClient(wsUrl);
  try {
    await client.connect();
    await client.send("Browser.getVersion", {});
    return true;
  } catch {
    return false;
  } finally {
    client.close();
  }
}

async function resolveAutoEndpoint() {
  const active = await readDevToolsActivePort();
  if (active) {
    const exactWs = `ws://127.0.0.1:${active.port}${active.wsPath}`;
    if (await verifyWsEndpoint(exactWs)) {
      return {
        source: "helium-devtools-active-port",
        wsUrl: exactWs,
        port: active.port,
        activePortFile: active.path,
      };
    }
  }

  for (const port of [9223, 9222, 9229]) {
    try {
      return await resolvePortEndpoint(String(port));
    } catch {
      // Try the next common local CDP port.
    }
  }

  throw new UserError(
    "No live Helium CDP endpoint found. Run `helium-cdp-pin enable` and approve the Helium remote debugging prompt.",
  );
}

async function resolvePortEndpoint(portText) {
  try {
    const info = await getHttpCdpInfo(portText);
    return { source: "http-discovery", wsUrl: info.wsUrl, base: info.base, version: info.version };
  } catch {
    const port = Number.parseInt(portText, 10);
    const directWs = `ws://127.0.0.1:${port}/devtools/browser`;
    if (await verifyWsEndpoint(directWs)) {
      return { source: "direct-websocket", wsUrl: directWs, port };
    }
    throw new UserError(`No live CDP endpoint on port ${portText}`);
  }
}

async function resolveBrowserEndpoint(cdp) {
  if (cdp === "auto") {
    return resolveAutoEndpoint();
  }
  if (/^\d+$/.test(cdp)) {
    return resolvePortEndpoint(cdp);
  }
  if (cdp.startsWith("ws://") || cdp.startsWith("wss://")) {
    if (await verifyWsEndpoint(cdp)) {
      return { source: "websocket-url", wsUrl: cdp };
    }
    throw new UserError(`Could not verify CDP WebSocket endpoint: ${cdp}`);
  }
  if (cdp.startsWith("http://") || cdp.startsWith("https://")) {
    const info = await getHttpCdpInfo(cdp);
    return { source: "http-discovery", wsUrl: info.wsUrl, base: info.base, version: info.version };
  }
  throw new UserError("--cdp must be auto, a port, an http(s) URL, or a ws(s) URL");
}

async function listTargets(cdp) {
  const endpoint = await resolveBrowserEndpoint(cdp);
  const client = new CdpClient(endpoint.wsUrl);
  await client.connect();
  try {
    const result = await client.send("Target.getTargets", {});
    const targets = result.targetInfos || [];
    return targets
      .filter((t) => t.type === "page")
      .map((t) => ({
        id: t.targetId,
        type: t.type,
        title: t.title || "",
        url: t.url || "",
        attached: Boolean(t.attached),
        browserContextId: t.browserContextId || "",
      }));
  } finally {
    client.close();
  }
}

async function listTargetsViaHttp(cdp) {
  const base = normalizeHttpBase(cdp);
  const targets = await fetchJson(`${base}/json/list`);
  return targets
    .filter((t) => t.type === "page")
    .map((t) => ({
      id: t.id,
      type: t.type,
      title: t.title || "",
      url: t.url || "",
      webSocketDebuggerUrl: t.webSocketDebuggerUrl || "",
    }));
}

async function loadState() {
  try {
    const text = await readFile(DEFAULT_STATE, "utf8");
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" ? parsed : { bindings: {} };
  } catch (error) {
    if (error.code === "ENOENT") {
      return { bindings: {} };
    }
    throw error;
  }
}

async function saveState(state) {
  await mkdir(dirname(DEFAULT_STATE), { recursive: true });
  await writeFile(DEFAULT_STATE, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

function selectTarget(targets, spec) {
  if (spec.targetId) {
    const target = targets.find((t) => t.id === spec.targetId);
    if (!target) {
      throw new UserError(`No page target with id ${spec.targetId}`);
    }
    return target;
  }

  if (spec.url) {
    const matches = targets.filter((t) => t.url === spec.url);
    return exactlyOne(matches, `url ${spec.url}`);
  }

  if (spec.urlPrefix) {
    const matches = targets.filter((t) => t.url.startsWith(spec.urlPrefix));
    return exactlyOne(matches, `url prefix ${spec.urlPrefix}`);
  }

  throw new UserError("Target selection requires --target-id, --url, or --url-prefix");
}

function exactlyOne(matches, description) {
  if (matches.length === 1) {
    return matches[0];
  }
  if (matches.length === 0) {
    throw new UserError(`No page target matched ${description}`);
  }
  const summary = matches.map((t) => `  ${t.id} ${t.url}`).join("\n");
  throw new UserError(`Multiple page targets matched ${description}; use --target-id:\n${summary}`);
}

async function resolveTarget(cdp, spec) {
  const targets = await listTargets(cdp);
  if (spec.targetId) {
    return selectTarget(targets, { targetId: spec.targetId });
  }

  if (!spec.label) {
    throw new UserError("Command requires --label or --target-id");
  }

  const state = await loadState();
  const binding = state.bindings?.[spec.label];
  if (!binding) {
    throw new UserError(`No binding for label ${spec.label}`);
  }

  const target = selectTarget(targets, { targetId: binding.targetId });
  if (binding.url && target.url !== binding.url) {
    throw new UserError(`Pinned target URL changed: expected ${binding.url}, got ${target.url}`);
  }
  if (binding.urlPrefix && !target.url.startsWith(binding.urlPrefix)) {
    throw new UserError(`Pinned target URL no longer matches ${binding.urlPrefix}: ${target.url}`);
  }
  return { ...target, binding };
}

async function withSession(cdp, targetId, fn) {
  const endpoint = await resolveBrowserEndpoint(cdp);
  const client = new CdpClient(endpoint.wsUrl);
  await client.connect();
  let sessionId;
  try {
    await client.send("Target.getTargetInfo", { targetId });
    const attached = await client.send("Target.attachToTarget", {
      targetId,
      flatten: true,
    });
    sessionId = attached.sessionId;
    if (!sessionId) {
      throw new Error("Target.attachToTarget did not return sessionId");
    }
    return await fn(client, sessionId);
  } finally {
    if (sessionId) {
      try {
        await client.send("Target.detachFromTarget", { sessionId });
      } catch {
        // The browser may already have detached the session during navigation.
      }
    }
    client.close();
  }
}

function jsString(value) {
  return JSON.stringify(value);
}

async function evaluate(cdp, target, expression) {
  return withSession(cdp, target.id, async (client, sessionId) => {
    await client.send("Runtime.enable", {}, sessionId);
    const result = await client.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    }, sessionId);
    if (result.exceptionDetails) {
      throw new UserError(formatException(result.exceptionDetails));
    }
    return remoteValue(result.result);
  });
}

function formatException(details) {
  const text = details.text || "JavaScript evaluation failed";
  const desc = details.exception?.description || details.exception?.value;
  return desc ? `${text}: ${desc}` : text;
}

function remoteValue(remote) {
  if (!remote) {
    return null;
  }
  if (Object.prototype.hasOwnProperty.call(remote, "value")) {
    return remote.value;
  }
  if (remote.unserializableValue) {
    return remote.unserializableValue;
  }
  if (remote.type === "undefined") {
    return null;
  }
  return remote.description ?? null;
}

function printValue(value, json) {
  if (json) {
    console.log(JSON.stringify(value, null, 2));
    return;
  }
  if (typeof value === "string") {
    console.log(value);
  } else {
    console.log(JSON.stringify(value, null, 2));
  }
}

async function commandList(opts) {
  const targets = await listTargets(opts.cdp);
  if (opts.json) {
    console.log(JSON.stringify(targets, null, 2));
    return;
  }
  for (const t of targets) {
    const title = t.title ? ` ${t.title}` : "";
    console.log(`${t.id}\t${t.url}${title}`);
  }
}

async function commandEnable(opts) {
  let timeoutSeconds = 60;
  const args = [...opts.args];
  while (args.length > 0) {
    const arg = args.shift();
    if (arg === "--timeout") {
      const value = needValue(args, "--timeout");
      timeoutSeconds = Number.parseInt(value, 10);
      if (!Number.isInteger(timeoutSeconds) || timeoutSeconds <= 0) {
        throw new UserError("enable --timeout must be a positive integer");
      }
    } else {
      throw new UserError(`Unknown enable option: ${arg}`);
    }
  }

  const openResult = spawnSync("/usr/bin/open", [
    "-b",
    "net.imput.helium",
    "chrome://inspect/#remote-debugging",
  ], {
    stdio: "ignore",
  });
  if (openResult.status !== 0) {
    throw new UserError("Failed to ask Helium to open chrome://inspect/#remote-debugging");
  }

  const deadline = Date.now() + timeoutSeconds * 1000;
  let lastError = "not checked yet";
  while (Date.now() < deadline) {
    try {
      const endpoint = await resolveAutoEndpoint();
      const out = {
        enabled: true,
        wsUrl: endpoint.wsUrl,
        port: endpoint.port || null,
        source: endpoint.source,
      };
      printValue(out, opts.json);
      return;
    } catch (error) {
      lastError = error.message;
      await sleep(1000);
    }
  }

  throw new UserError(
    `Timed out waiting for Helium CDP authorization after ${timeoutSeconds}s. Last check: ${lastError}`,
  );
}

async function commandBind(opts) {
  const named = parseNamed(opts.args);
  if (!named.label) {
    throw new UserError("bind requires --label <name>");
  }
  const targets = await listTargets(opts.cdp);
  const target = selectTarget(targets, named);
  const state = await loadState();
  state.bindings ??= {};
  state.bindings[named.label] = {
    targetId: target.id,
    titleAtBind: target.title,
    urlAtBind: target.url,
    url: named.url,
    urlPrefix: named.urlPrefix,
    cdp: opts.cdp,
    boundAt: new Date().toISOString(),
  };
  await saveState(state);
  const out = { label: named.label, targetId: target.id, url: target.url, title: target.title };
  printValue(out, opts.json);
}

async function commandDetach(opts) {
  const named = parseNamed(opts.args);
  if (!named.label) {
    throw new UserError("detach requires --label <name>");
  }
  const state = await loadState();
  if (state.bindings) {
    delete state.bindings[named.label];
  }
  if (Object.keys(state.bindings || {}).length === 0) {
    await rm(DEFAULT_STATE, { force: true });
  } else {
    await saveState(state);
  }
  printValue({ detached: named.label }, opts.json);
}

async function commandEval(opts) {
  const named = parseNamed(opts.args);
  const expression = named.rest.join(" ");
  if (!expression) {
    throw new UserError("eval requires a JavaScript expression");
  }
  const target = await resolveTarget(opts.cdp, named);
  const value = await evaluate(opts.cdp, target, expression);
  printValue(value, opts.json);
}

async function commandGet(opts) {
  const named = parseNamed(opts.args);
  const field = named.rest[0];
  if (!field) {
    throw new UserError("get requires url, title, or target-id");
  }
  const target = await resolveTarget(opts.cdp, named);
  if (field === "url") {
    printValue(target.url, opts.json);
  } else if (field === "title") {
    printValue(target.title, opts.json);
  } else if (field === "target-id") {
    printValue(target.id, opts.json);
  } else {
    throw new UserError(`Unknown get field: ${field}`);
  }
}

async function commandFill(opts) {
  const named = parseNamed(opts.args);
  const [selector, ...valueParts] = named.rest;
  if (!selector || valueParts.length === 0) {
    throw new UserError("fill requires <selector> <value>");
  }
  const value = valueParts.join(" ");
  const target = await resolveTarget(opts.cdp, named);
  const expression = `(() => {
    const selector = ${jsString(selector)};
    const value = ${jsString(value)};
    const el = document.querySelector(selector);
    if (!el) throw new Error("No element matches " + selector);
    el.scrollIntoView?.({ block: "center", inline: "center" });
    el.focus?.();
    if (el.isContentEditable) {
      el.textContent = value;
    } else if ("value" in el) {
      const proto = Object.getPrototypeOf(el);
      const desc = proto ? Object.getOwnPropertyDescriptor(proto, "value") : null;
      if (desc && typeof desc.set === "function") desc.set.call(el, value);
      else el.value = value;
    } else {
      throw new Error("Element is not fillable: " + selector);
    }
    try {
      el.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
    } catch {
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return { selector, tag: el.tagName, value: "value" in el ? el.value : el.textContent };
  })()`;
  const result = await evaluate(opts.cdp, target, expression);
  printValue(result, opts.json);
}

async function commandClick(opts) {
  const named = parseNamed(opts.args);
  const selector = named.rest[0];
  if (!selector) {
    throw new UserError("click requires <selector>");
  }
  const target = await resolveTarget(opts.cdp, named);
  const expression = `(() => {
    const selector = ${jsString(selector)};
    const el = document.querySelector(selector);
    if (!el) throw new Error("No element matches " + selector);
    el.scrollIntoView?.({ block: "center", inline: "center" });
    el.focus?.();
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup"]) {
      el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
    }
    el.click();
    return { selector, tag: el.tagName, text: (el.innerText || el.textContent || "").trim().slice(0, 120) };
  })()`;
  const result = await evaluate(opts.cdp, target, expression);
  printValue(result, opts.json);
}

async function commandScreenshot(opts) {
  const named = parseNamed(opts.args);
  const path = named.rest[0];
  if (!path) {
    throw new UserError("screenshot requires <path>");
  }
  const target = await resolveTarget(opts.cdp, named);
  const result = await withSession(opts.cdp, target.id, async (client, sessionId) => {
    await client.send("Page.enable", {}, sessionId);
    return client.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: true,
      fromSurface: true,
    }, sessionId);
  });
  if (!result.data) {
    throw new Error("Page.captureScreenshot returned no data");
  }
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, Buffer.from(result.data, "base64"));
  printValue({ path, bytes: Buffer.byteLength(result.data, "base64") }, opts.json);
}

async function commandSnapshot(opts) {
  const named = parseNamed(opts.args);
  const target = await resolveTarget(opts.cdp, named);
  const expression = `(() => {
    function cssPath(el) {
      if (el.id) return "#" + CSS.escape(el.id);
      const parts = [];
      let node = el;
      while (node && node.nodeType === 1 && parts.length < 5) {
        let part = node.localName;
        if (node.classList && node.classList.length) part += "." + Array.from(node.classList).slice(0, 2).map(CSS.escape).join(".");
        const parent = node.parentElement;
        if (parent) {
          const same = Array.from(parent.children).filter((child) => child.localName === node.localName);
          if (same.length > 1) part += ":nth-of-type(" + (same.indexOf(node) + 1) + ")";
        }
        parts.unshift(part);
        node = parent;
      }
      return parts.join(" > ");
    }
    const nodes = Array.from(document.querySelectorAll(
      'a[href],button,input,textarea,select,[role="button"],[onclick],[tabindex]:not([tabindex="-1"])'
    )).slice(0, 200);
    return nodes.map((el, index) => {
      const rect = el.getBoundingClientRect();
      return {
        ref: "@e" + (index + 1),
        selector: cssPath(el),
        tag: el.tagName,
        type: el.getAttribute("type") || "",
        name: el.getAttribute("name") || "",
        text: (el.innerText || el.value || el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 160),
        href: el.href || "",
        visible: rect.width > 0 && rect.height > 0,
      };
    });
  })()`;
  const result = await evaluate(opts.cdp, target, expression);
  if (opts.json) {
    printValue(result, true);
    return;
  }
  for (const item of result) {
    const bits = [item.ref, item.selector, item.tag];
    if (item.type) bits.push(`type=${item.type}`);
    if (item.text) bits.push(JSON.stringify(item.text));
    console.log(bits.join(" "));
  }
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  switch (opts.command) {
    case "help":
      console.log(usage());
      return;
    case "version":
      console.log(VERSION);
      return;
    case "list":
      return commandList(opts);
    case "enable":
      return commandEnable(opts);
    case "bind":
      return commandBind(opts);
    case "detach":
      return commandDetach(opts);
    case "eval":
      return commandEval(opts);
    case "get":
      return commandGet(opts);
    case "fill":
      return commandFill(opts);
    case "click":
      return commandClick(opts);
    case "screenshot":
      return commandScreenshot(opts);
    case "snapshot":
      return commandSnapshot(opts);
    default:
      throw new UserError(`Unknown command: ${opts.command}\n\n${usage()}`);
  }
}

main().catch((error) => {
  const prefix = error instanceof UserError ? "error" : "fatal";
  console.error(`${prefix}: ${error.message}`);
  process.exit(1);
});
