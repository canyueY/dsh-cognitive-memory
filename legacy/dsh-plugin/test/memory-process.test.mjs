/**
 * Regression: a service.json left by a previous DSH process must not be
 * adopted by the next one (it points at a dead port).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { MemoryProcessHost } from '../src/memory-process.js';

test('start() drops stale service.json before spawning', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'mem-proc-'));
  try {
    const root = join(dir, 'service');
    await mkdir(join(root, 'src', 'mnemosyne'), { recursive: true });
    // Fail fast; we only care that the stale file was removed before spawn.
    await writeFile(join(root, 'src', 'mnemosyne', 'main.py'), 'raise SystemExit(1)\n');

    const data = join(dir, 'data');
    await mkdir(join(data, 'runtime'), { recursive: true });
    const stale = join(data, 'runtime', 'service.json');
    await writeFile(stale, JSON.stringify({ host: '127.0.0.1', port: 1 }));

    const host = new MemoryProcessHost({
      serviceRoot: root,
      dataDir: data,
      python: process.execPath,
      token: 'test-token',
    });
    await assert.rejects(host.start({ timeoutMs: 400 }));
    assert.equal(existsSync(stale), false, 'stale service.json should be removed');
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
