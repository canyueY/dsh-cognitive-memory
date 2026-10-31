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

  async request(method, path, body) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
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
    }
  }

  health() { return this.request('GET', '/api/v1/health'); }
  search(body) { return this.request('POST', '/api/v1/memories/search', body); }
  get(id, includeEvidence = false) {
    const q = includeEvidence ? '?include_evidence=true' : '';
    return this.request('GET', `/api/v1/memories/${encodeURIComponent(id)}${q}`);
  }
  propose(body) { return this.request('POST', '/api/v1/memories', body); }
  update(id, body) { return this.request('PATCH', `/api/v1/memories/${encodeURIComponent(id)}`, body); }
  forget(id, hard = false) {
    const q = hard ? '?hard=true' : '';
    return this.request('DELETE', `/api/v1/memories/${encodeURIComponent(id)}${q}`);
  }
  observe(body) { return this.request('POST', '/api/v1/observations', body); }
  feedback(body) { return this.request('POST', '/api/v1/feedback', body); }
  context(body) { return this.request('POST', '/api/v1/contexts/build', body); }
  task(id) { return this.request('GET', `/api/v1/tasks/${encodeURIComponent(id)}`); }
}
