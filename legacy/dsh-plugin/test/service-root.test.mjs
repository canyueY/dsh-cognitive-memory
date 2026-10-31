/**
 * Zero-config: bundled ../service must resolve without env vars.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolveServiceRoot } from '../src/memory-process.js';

const here = dirname(fileURLToPath(import.meta.url));
const bundled = resolve(here, '..', 'service');

test('resolveServiceRoot finds bundled service/ without env', () => {
  const prevNew = process.env.DSH_MNEMOSYNE_ROOT;
  const prevOld = process.env.DSH_COGNITIVE_MEMORY_ROOT;
  delete process.env.DSH_MNEMOSYNE_ROOT;
  delete process.env.DSH_COGNITIVE_MEMORY_ROOT;
  try {
    const root = resolveServiceRoot();
    assert.equal(resolve(root), bundled);
  } finally {
    if (prevNew === undefined) delete process.env.DSH_MNEMOSYNE_ROOT;
    else process.env.DSH_MNEMOSYNE_ROOT = prevNew;
    if (prevOld === undefined) delete process.env.DSH_COGNITIVE_MEMORY_ROOT;
    else process.env.DSH_COGNITIVE_MEMORY_ROOT = prevOld;
  }
});
