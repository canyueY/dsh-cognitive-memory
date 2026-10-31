# @mnemosyne/client

Minimal TypeScript client for Mnemosyne Node (`/api/v1`).

```ts
import { MnemosyneClient } from "@mnemosyne/client";

const client = new MnemosyneClient({
  baseUrl: "http://127.0.0.1:8765",
  token: process.env.DSH_MEMORY_TOKEN!,
});

await client.health();
await client.observe({ source_kind: "system", content: "hello", producer: "ts" });
```

Agent-scoped calls: pass `agentId` + `agentToken` (sent as `X-Agent-*` headers).

**GA note:** Python SDK remains the primary reference; this package is a thin parity subset.
