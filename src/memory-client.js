/**
 * REST client for mnemosyne service (127.0.0.1).
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

export class MemoryClient {
  /**
   * @param {{ baseUrl: string, token: string, timeoutMs?: number }} opts
   */
  constructor(opts) {
    this.baseUrl = String(opts.baseUrl || '').replace(/\/$/, '');
    this.token = String(opts.token || '');
    this.timeoutMs = Number(opts.timeoutMs || 15000);
  }

  /**
   * @param {string} method
   * @param {string} path
   * @param {unknown} [body]
   * @param {{ signal?: AbortSignal }} [opts]
   */
  async request(method, path, body, opts = {}) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    const outer = opts.signal;
    const onOuterAbort = () => ctrl.abort(outer?.reason);
    if (outer) {
      if (outer.aborted) ctrl.abort(outer.reason);
      else outer.addEventListener('abort', onOuterAbort, { once: true });
    }
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.token}`,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: ctrl.signal,
      });
      const text = await res.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
      if (!res.ok) {
        const err = new Error(data?.message || `HTTP ${res.status}`);
        err.status = res.status;
        err.data = data;
        throw err;
      }
      return data;
    } finally {
      clearTimeout(timer);
      if (outer) outer.removeEventListener('abort', onOuterAbort);
    }
  }

  health(opts) { return this.request('GET', '/api/v1/health', undefined, opts); }
  search(body, opts) { return this.request('POST', '/api/v1/memories/search', body, opts); }
  get(id, includeEvidence = false, opts) {
    const q = includeEvidence ? '?include_evidence=true' : '';
    return this.request('GET', `/api/v1/memories/${encodeURIComponent(id)}${q}`, undefined, opts);
  }
  propose(body, opts) { return this.request('POST', '/api/v1/memories', body, opts); }
  update(id, body, opts) { return this.request('PATCH', `/api/v1/memories/${encodeURIComponent(id)}`, body, opts); }
  forget(id, hard = false, opts) {
    const q = hard ? '?hard=true' : '';
    return this.request('DELETE', `/api/v1/memories/${encodeURIComponent(id)}${q}`, undefined, opts);
  }
  observe(body, opts) { return this.request('POST', '/api/v1/observations', body, opts); }
  feedback(body, opts) { return this.request('POST', '/api/v1/feedback', body, opts); }
  context(body, opts) { return this.request('POST', '/api/v1/contexts/build', body, opts); }
  task(id, opts) { return this.request('GET', `/api/v1/tasks/${encodeURIComponent(id)}`, undefined, opts); }
}
