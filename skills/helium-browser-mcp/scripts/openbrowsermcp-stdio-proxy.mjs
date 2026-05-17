#!/usr/bin/env node
import fs from 'node:fs';

const endpoint = process.env.OPENBROWSERMCP_MCP_URL || 'http://127.0.0.1:3500/mcp';
const tokenPath = process.env.OPENBROWSERMCP_SETTINGS || `${process.env.HOME}/openbrowsermcp/settings.json`;
const logPath = process.env.OPENBROWSERMCP_PROXY_LOG || '';

let sessionId = null;
let input = Buffer.alloc(0);
let chain = Promise.resolve();
let framing = null;

function log(message) {
  if (!logPath) return;
  fs.appendFileSync(logPath, `${new Date().toISOString()} ${message}\n`);
}

function readToken() {
  const settings = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
  if (typeof settings.token !== 'string' || settings.token.length === 0) {
    throw new Error(`missing token in ${tokenPath}`);
  }
  return settings.token;
}

function writeMessage(message) {
  const body = JSON.stringify(message);
  if (framing === 'ndjson') {
    process.stdout.write(`${body}\n`);
    return;
  }
  process.stdout.write(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`);
}

function parseSseOrJson(text) {
  const trimmed = text.trim();
  if (!trimmed) return null;

  const dataLines = [];
  for (const line of trimmed.split(/\r?\n/)) {
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length > 0) {
    return JSON.parse(dataLines.join('\n'));
  }
  return JSON.parse(trimmed);
}

async function forward(message) {
  log(`forward ${message.method || '<response>'} id=${Object.prototype.hasOwnProperty.call(message, 'id') ? message.id : '<none>'}`);
  const token = readToken();
  const headers = {
    'content-type': 'application/json',
    accept: 'application/json, text/event-stream',
    authorization: `Bearer ${token}`,
  };
  if (sessionId) headers['mcp-session-id'] = sessionId;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers,
    body: JSON.stringify(message),
  });

  const nextSessionId = response.headers.get('mcp-session-id');
  if (nextSessionId) sessionId = nextSessionId;

  const text = await response.text();
  log(`response status=${response.status} bytes=${Buffer.byteLength(text)} session=${sessionId ? 'yes' : 'no'}`);
  if (!response.ok) {
    throw new Error(`OpenBrowserMCP HTTP ${response.status}: ${text}`);
  }

  const body = parseSseOrJson(text);
  if (body) writeMessage(body);
}

function jsonRpcError(id, error) {
  writeMessage({
    jsonrpc: '2.0',
    id,
    error: {
      code: -32000,
      message: error instanceof Error ? error.message : String(error),
    },
  });
}

function handle(message) {
  chain = chain.then(async () => {
    try {
      await forward(message);
    } catch (error) {
      if (Object.prototype.hasOwnProperty.call(message, 'id')) {
        jsonRpcError(message.id, error);
      } else {
        console.error(error instanceof Error ? error.message : String(error));
      }
    }
  });
}

function drain() {
  if (framing === null && input.length > 0) {
    const first = input.subarray(0, 1).toString('utf8');
    framing = first === '{' ? 'ndjson' : 'headers';
    log(`framing=${framing}`);
  }

  if (framing === 'ndjson') {
    while (true) {
      const lineEnd = input.indexOf('\n');
      if (lineEnd === -1) return;

      const line = input.subarray(0, lineEnd).toString('utf8').trim();
      input = input.subarray(lineEnd + 1);
      if (!line) continue;

      try {
        handle(JSON.parse(line));
      } catch (error) {
        console.error(error instanceof Error ? error.message : String(error));
      }
    }
  }

  while (true) {
    let headerEnd = input.indexOf('\r\n\r\n');
    let separatorLength = 4;
    if (headerEnd === -1) {
      headerEnd = input.indexOf('\n\n');
      separatorLength = 2;
    }
    if (headerEnd === -1) return;

    const header = input.subarray(0, headerEnd).toString('latin1');
    const match = header.match(/content-length:\s*(\d+)/i);
    if (!match) {
      console.error('missing Content-Length header');
      process.exit(1);
    }

    const length = Number(match[1]);
    const bodyStart = headerEnd + separatorLength;
    const bodyEnd = bodyStart + length;
    if (input.length < bodyEnd) return;

    const body = input.subarray(bodyStart, bodyEnd).toString('utf8');
    input = input.subarray(bodyEnd);

    try {
      handle(JSON.parse(body));
    } catch (error) {
      console.error(error instanceof Error ? error.message : String(error));
    }
  }
}

process.stdin.on('data', (chunk) => {
  log(`stdin bytes=${chunk.length}`);
  if (process.env.OPENBROWSERMCP_PROXY_PREVIEW === '1') {
    log(`stdin preview=${JSON.stringify(chunk.subarray(0, 200).toString('utf8'))}`);
  }
  input = Buffer.concat([input, chunk]);
  drain();
});

process.stdin.on('end', () => {
  chain.finally(() => process.exit(0));
});
