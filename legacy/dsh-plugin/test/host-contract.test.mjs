/**
 * Host-contract regression: the plugin must activate in a bare Cordis context
 * that has no `config` service and forbids undeclared ctx properties.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
process.env.DSH_TOOLS_PATH = join(here, '..', 'test-support', 'dsh-tools-stub.mjs');

const TOOLS = [
  'memory_health',
  'memory_search',
  'memory_get',
  'memory_context',
  'memory_propose',
  'memory_feedback',
  'memory_update',
  'memory_forget',
  'memory_task_status',
  'memory_observe',
];

test('apply() registers all tools without a config service', async () => {
  const { apply } = await import('../src/index.js?no-config');
  const registered = [];
  const ctx = {
    tools: {
      register(tool) {
        registered.push(tool);
        return () => {};
      },
    },
  };
  Object.defineProperty(ctx, 'config', {
    get() {
      throw new Error('cannot get property "config" without inject');
    },
  });

  const dispose = await apply(ctx);
  assert.deepEqual(registered.map((t) => t.name), TOOLS);
  dispose();
});

test('apply() survives a throwing config lookup', async () => {
  const { apply } = await import('../src/index.js?throwing-config');
  const registered = [];
  const ctx = {
    get() {
      throw new Error('cannot get property "config" without inject');
    },
    tools: {
      register(tool) {
        registered.push(tool);
        return () => {};
      },
    },
  };

  const dispose = await apply(ctx);
  assert.equal(registered.length, TOOLS.length);
  dispose();
});
