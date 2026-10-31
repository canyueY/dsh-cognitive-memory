/** Minimal stand-in for @deepseek-ai/dsh-tools used by host-contract tests. */
export function defineTool(spec) {
  if (!spec?.name) throw new Error('defineTool: name is required');
  return {
    ...spec,
    async execute(args = {}) {
      if (typeof spec.execute !== 'function') throw new Error(`${spec.name}: no execute`);
      return spec.execute(args);
    },
  };
}
