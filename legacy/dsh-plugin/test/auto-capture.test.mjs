/**
 * Auto-capture contract: session/event writes the user message and the final
 * assistant answer, without asking the model to call memory_observe, and
 * without persisting hidden reasoning.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
process.env.DSH_TOOLS_PATH = join(here, '..', 'test-support', 'dsh-tools-stub.mjs');

function startServer() {
  const received = [];
  const server = http.createServer((req, res) => {
    let raw = '';
    req.on('data', (chunk) => { raw += chunk; });
    req.on('end', () => {
      received.push({ url: req.url, body: raw ? JSON.parse(raw) : null });
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end('{}');
    });
  });
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => resolve({ server, received, port: server.address().port }));
  });
}

test('auto-capture writes user + final assistant, not reasoning', async () => {
  const { apply } = await import('../src/index.js?auto-capture');
  const { server, received, port } = await startServer();
  const listeners = new Map();
  const ctx = {
    get(name) {
      if (name !== 'config') return null;
      return {
        'dsh-mnemosyne': {
          base_url: `http://127.0.0.1:${port}`,
          token: 'test-token',
          auto_capture: true,
        },
      };
    },
    on(event, handler) {
      listeners.set(event, handler);
      return () => listeners.delete(event);
    },
    tools: {
      register() { return () => {}; },
    },
  };
  const dispose = await apply(ctx);
  try {
    const emit = (event) => listeners.get('session/event')({ id: 'session-test' }, event);
    emit({
      type: 'user/message', seq: 1, time: Date.now(),
      data: { role: 'user', content: '我最近很喜欢听夜航星。' },
    });
    emit({
      type: 'assistant/message', seq: 5, time: Date.now(),
      data: {
        message: {
          role: 'assistant',
          content: [
            { type: 'reasoning', text: 'hidden chain of thought' },
            { type: 'text', text: '那首夜航星很好听。' },
          ],
        },
      },
    });
    emit({ type: 'turn/end', seq: 6, time: Date.now(), data: { turn: 1 } });

    const deadline = Date.now() + 3000;
    while (received.length < 2 && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    assert.equal(received.length, 2);
    const contents = received.map((r) => r.body.content);
    assert.deepEqual(contents, ['我最近很喜欢听夜航星。', '那首夜航星很好听。']);
    assert.ok(!JSON.stringify(received).includes('hidden chain of thought'));
    assert.equal(received[0].body.idempotency_key, 'dsh:session-test:1');
    assert.equal(received[1].body.idempotency_key, 'dsh:session-test:5');
  } finally {
    dispose();
    await new Promise((resolve) => server.close(resolve));
  }
});
