#!/usr/bin/env node
import fs from 'node:fs';

const DEFAULT_PORT = 3500;
const tokenPath = `${process.env.HOME}/.bro/settings.json`;

function usage(exitCode = 2) {
  const text = [
    'usage: bro-call.mjs <tool-name> [json-arguments] [--json] [--port PORT]',
    '       bro-call.mjs --list [--json] [--port PORT]',
    '       bro-call.mjs --status [--port PORT]',
    '',
    'examples:',
    '  bro-call.mjs browsers_context',
    '  bro-call.mjs tabs_context \'{"all":true}\'',
    '  bro-call.mjs browser.extract \'{"url":"https://example.com"}\' --json',
  ].join('\n');
  console.error(text);
  process.exit(exitCode);
}

let port = DEFAULT_PORT;
let jsonOutput = false;
let listTools = false;
let statusOnly = false;
const positionals = [];

for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === '--help' || arg === '-h') usage(0);
  if (arg === '--json') {
    jsonOutput = true;
    continue;
  }
  if (arg === '--list') {
    listTools = true;
    continue;
  }
  if (arg === '--status') {
    statusOnly = true;
    continue;
  }
  if (arg === '--port') {
    const next = process.argv[i + 1];
    if (!next) usage();
    port = Number.parseInt(next, 10);
    i += 1;
    continue;
  }
  positionals.push(arg);
}

if (!Number.isInteger(port) || port <= 0 || port > 65535) {
  console.error(`invalid port: ${port}`);
  process.exit(2);
}

const endpoint = `http://127.0.0.1:${port}/mcp`;

async function printStatus() {
  const response = await fetch(`http://127.0.0.1:${port}/status`);
  const text = await response.text();
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`);
  console.log(JSON.stringify(JSON.parse(text), null, 2));
}

function readToken() {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
  } catch (error) {
    throw new Error(
      `failed to read ${tokenPath}: ${error.message}. Run bro doctor or bro serve to initialize bro local state.`
    );
  }
  if (!parsed.token || typeof parsed.token !== 'string') {
    throw new Error(`missing token in ${tokenPath}`);
  }
  return parsed.token;
}

function parseArgs(raw) {
  if (!raw) return {};
  try {
    const value = JSON.parse(raw);
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      throw new Error('arguments must be a JSON object');
    }
    return value;
  } catch (error) {
    throw new Error(`invalid JSON arguments: ${error.message}`);
  }
}

function parseSseOrJson(text) {
  const payloads = [];
  for (const line of text.split('\n')) {
    if (!line.startsWith('data: ')) continue;
    const payload = line.slice(6).trim();
    if (payload) payloads.push(payload);
  }
  if (payloads.length > 0) return JSON.parse(payloads[payloads.length - 1]);
  return JSON.parse(text);
}

async function rpc(token, sessionId, id, method, params) {
  const headers = {
    'content-type': 'application/json',
    accept: 'application/json, text/event-stream',
    authorization: `Bearer ${token}`,
  };
  if (sessionId) headers['mcp-session-id'] = sessionId;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers,
    body: JSON.stringify({ jsonrpc: '2.0', id, method, params }),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`);
  return {
    sessionId: response.headers.get('mcp-session-id'),
    body: parseSseOrJson(text),
  };
}

function printResult(body) {
  if (jsonOutput) {
    console.log(JSON.stringify(body, null, 2));
    return;
  }

  const result = body.result;
  const structured = result?.structuredContent ?? result?.structured_content;
  let printed = false;

  if (structured !== undefined) {
    console.log(JSON.stringify(structured, null, 2));
    printed = true;
  }

  const content = result?.content;
  if (Array.isArray(content)) {
    for (const item of content) {
      if (item?.type === 'text') console.log(item.text);
      else console.log(JSON.stringify(item));
      printed = true;
    }
  }

  if (!printed) console.log(JSON.stringify(body, null, 2));
}

async function main() {
  if (statusOnly) {
    if (positionals.length > 0 || listTools) usage();
    await printStatus();
    return;
  }

  const toolName = positionals[0];
  if (!listTools && !toolName) usage();
  if (positionals.length > (listTools ? 0 : 2)) usage();

  const token = readToken();
  const init = await rpc(token, null, 1, 'initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'codex-bro-helper', version: '0' },
  });
  const sessionId = init.sessionId;
  if (!sessionId) throw new Error('bro did not return an MCP session id');

  const call = listTools
    ? await rpc(token, sessionId, 2, 'tools/list', {})
    : await rpc(token, sessionId, 2, 'tools/call', {
        name: toolName,
        arguments: parseArgs(positionals[1]),
      });

  printResult(call.body);
  const result = call.body.result;
  if (result?.isError === true || result?.is_error === true) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
