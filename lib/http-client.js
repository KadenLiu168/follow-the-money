export function createHttpClient({ userAgent, bucket }) {
  if (!userAgent) throw new Error('userAgent required');
  if (!bucket) throw new Error('bucket required');

  async function fetchWithBackoff(url, opts = {}, attempt = 0) {
    try {
      await bucket.take();
      // Caller-supplied headers must NOT override the required User-Agent.
      // Strip any UA from opts.headers before merging.
      const safeHeaders = { ...(opts.headers || {}) };
      delete safeHeaders['User-Agent'];
      delete safeHeaders['user-agent'];
      const res = await globalThis.fetch(url, {
        ...opts,
        headers: { ...safeHeaders, 'User-Agent': userAgent },
      });
      if (res.status === 429 && attempt < 2) {
        const wait = Number(res.headers.get('Retry-After') || 1) * 1000;
        await new Promise((r) => setTimeout(r, wait));
        return fetchWithBackoff(url, opts, attempt + 1);
      }
      return res;
    } catch (err) {
      if (attempt < 2) {
        const wait = 2 ** attempt * 500;
        await new Promise((r) => setTimeout(r, wait));
        return fetchWithBackoff(url, opts, attempt + 1);
      }
      throw new Error(`Failed after 3 retries: ${err.message}`);
    }
  }

  return { fetch: fetchWithBackoff };
}
