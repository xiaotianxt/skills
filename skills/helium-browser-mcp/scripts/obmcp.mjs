#!/usr/bin/env node
import fs from 'node:fs';

const endpoint = 'http://127.0.0.1:3500/mcp';
const tokenPath = `${process.env.HOME}/openbrowsermcp/settings.json`;

function usage() {
  console.error('usage: obmcp.mjs <tool-name> [json-arguments]');
  console.error('example: obmcp.mjs tabs_context \'{"all":true}\'');
  process.exit(2);
}

const toolName = process.argv[2];
if (!toolName) usage();

let args = {};
if (process.argv[3]) {
  try {
    args = JSON.parse(process.argv[3]);
  } catch (err) {
    console.error(`invalid JSON arguments: ${err.message}`);
    process.exit(2);
  }
}

const token = JSON.parse(fs.readFileSync(tokenPath, 'utf8')).token;
if (!token) {
  console.error(`missing token in ${tokenPath}`);
  process.exit(1);
}

const baseHeaders = {
  'content-type': 'application/json',
  accept: 'application/json, text/event-stream',
  authorization: `Bearer ${token}`,
};

function parseSseOrJson(text) {
  const line = text.split('\n').find((value) => value.startsWith('data: '));
  return line ? JSON.parse(line.slice(6)) : JSON.parse(text);
}

async function rpc(sessionId, id, method, params) {
  const headers = sessionId
    ? { ...baseHeaders, 'mcp-session-id': sessionId }
    : baseHeaders;
  const response = await fetch(endpoint, {
    method: 'POST',
    headers,
    body: JSON.stringify({ jsonrpc: '2.0', id, method, params }),
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${text}`);
  }
  return {
    sessionId: response.headers.get('mcp-session-id'),
    body: parseSseOrJson(text),
  };
}

const init = await rpc(null, 1, 'initialize', {
  protocolVersion: '2024-11-05',
  capabilities: {},
  clientInfo: { name: 'codex-obmcp-helper', version: '0' },
});

const sessionId = init.sessionId;
if (!sessionId) {
  throw new Error('OpenBrowserMCP did not return an MCP session id');
}

const result = await rpc(sessionId, 2, 'tools/call', {
  name: toolName,
  arguments: args,
});

const body = result.body;
const content = body.result?.content;
if (Array.isArray(content)) {
  for (const item of content) {
    if (item?.type === 'text') console.log(item.text);
    else console.log(JSON.stringify(item));
  }
} else {
  console.log(JSON.stringify(body, null, 2));
}
