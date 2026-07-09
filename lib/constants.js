// Shared domain constants — single source of truth for cross-file literals.
//
// Scope: ONLY constants that are (a) used in more than one file, or
// (b) carry clear domain meaning worth naming. Conventional unit conversions
// (e.g. `* 1000` seconds→ms, `24*60*60*1000` days→ms) are intentionally NOT
// centralized here — extracting them only adds noise.
//
// This module is for compile-time constants, NOT hot-tunable config.
// Data-source config belongs in lib/config/ (see load-default-sources.js).

// SEC EDGAR's 13F informationTable <value> is expressed in thousands of USD.
// Multiply by this to store dollar amounts consistently across the pipeline.
export const THOUSANDS_MULTIPLIER = 1000;

// Conservative client-side throttle for SEC EDGAR public endpoints:
// 10 requests/sec with a burst capacity of 10. Frozen so callers cannot
// mutate the shared default.
export const DEFAULT_RATE_LIMIT = Object.freeze({ rate: 10, capacity: 10 });
