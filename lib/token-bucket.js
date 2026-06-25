export class TokenBucket {
  constructor(rate, capacity) {
    if (!Number.isFinite(rate) || rate <= 0) throw new Error('rate must be > 0');
    if (!Number.isInteger(capacity) || capacity <= 0) throw new Error('capacity must be a positive integer');
    this.rate = rate;       // tokens per second
    this.capacity = capacity;
    this.tokens = capacity;
    this.lastRefill = Date.now();
  }

  _refill() {
    const now = Date.now();
    const elapsedSec = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsedSec * this.rate);
    this.lastRefill = now;
  }

  async take() {
    while (true) {
      this._refill();
      if (this.tokens >= 1) { this.tokens -= 1; return; }
      const deficit = 1 - this.tokens;
      const waitMs = Math.max(10, Math.ceil((deficit / this.rate) * 1000));
      await new Promise(r => setTimeout(r, waitMs));
    }
  }
}