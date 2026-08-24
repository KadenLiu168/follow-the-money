# Scoring

## Deterministic scoring contract (v1)

All score components are on a closed `0..100` scale. The initial significance
weights are 30/20/20/20/10 for Fundamental Magnitude, Surprise, Systemic
Breadth, Repricing Magnitude, and Persistence.

### Missing-data policy

- The full denominator is preserved; an unknown component contributes zero.
- Component coverage = sum of configured weights whose whole component is
  known, divided by the total significance weight.
- At least 60% coverage is required for every rankable event; weights are never
  silently reallocated.
- Fundamental Magnitude is known only when both `scope` and
  `fundamental_depth` are non-`unknown`; Persistence only when both
  `reversibility` and `structural_horizon` are non-`unknown`.

### Categorical maps (v1, fixed)

| Feature | Map |
| --- | --- |
| `scope` | single_entity 25, sector 50, single_market 75, cross_market 100, unknown 0 |
| `fundamental_depth` | headline 25, operating_or_policy 50, balance_sheet_or_liquidity 75, systemic 100, unknown 0 |
| `reversibility` | high 25, medium 50, low 75, effectively_irreversible 100, unknown 0 |
| `structural_horizon` | intraday 0, days 25, weeks 50, months 75, years_plus 100, unknown 0 |

When known, Fundamental Magnitude and Persistence are the arithmetic means
of their two mapped inputs.

### Event Surprise

The maximum absolute normalized surprise among available values attached to
the Event's `key_fact_ids`; unknown key-fact surprises are ignored when
another is available; no available value makes the whole component unknown.

Bins (shared with Repricing Magnitude on observable reaction z):

| Range | Score |
| --- | --- |
| `< 0.5` | 0 |
| `< 1` | 25 |
| `< 2` | 50 |
| `< 3` | 75 |
| `>= 3` | 100 |

### Systemic Breadth and Repricing Magnitude

- Systemic Breadth = affected asset groups / 9 * 100; an affected group
  requires its single validated non-`unclear` mapping. The component is known
  only when at least one mapping is non-`unclear`.
- Repricing Magnitude uses the maximum observable absolute current-excluded
  reaction z among the deterministic proxies for mapped groups; unknown when
  no mapped proxy is observable.

### Nine asset groups and reaction proxies

| Group | Proxies |
| --- | --- |
| `cn_hk_equities` | CSI 300, Hang Seng |
| `us_equities` | S&P 500 |
| `us_rates` | US 2-year yield, US 10-year yield |
| `china_rates` | China 10-year yield |
| `usd_fx` | DXY, USD/CNH |
| `industrial_commodities` | Copper |
| `energy` | WTI |
| `precious_metals` | Gold |
| `crypto` | BTC |

### Surprise scales (v1)

Normalized surprise = raw surprise / configured positive scale. V1 defines
only these exact percentage-point scales: US all-items SA CPI MoM `0.1`, US
core PCE price index MoM `0.1`, US PPI final demand SA MoM `0.1`. Every
other series identity/frequency/adjustment is `unknown` until a versioned
scale is added.

### Event Relevance

Weights 40/25/20/15 over freshness, China/Hong Kong open relevance, US
next-session relevance, and unresolved next-24-hour catalyst.

- Freshness age = `evidence_cutoff_at - fully_known_at` (never the economic
  effective/reference time). Bins: `<=6h:100`, `<=12h:75`, `<=24h:50`,
  `<=48h:25`, older: 0.
- `cn_hk_exposure` / `us_next_session_exposure` map `direct|indirect|none|
  unknown` to `100|50|0|0` (script-owned).
- `catalyst_calendar_ids` non-empty maps to 100, empty to 0.

### Base Priority

`0.70 * significance + 0.30 * event_relevance`, before confidence/coverage
gates and redundancy deductions. The Decimal result is retained without
introducing presentation tiers or format state.

## Decimal contract

Every v1 calculation runs inside a fresh local Decimal context (precision 50,
`ROUND_HALF_EVEN`, `Emin=-999999`, `Emax=999999`, `clamp=0`, with
`InvalidOperation`/`DivisionByZero`/`Overflow`/`FloatOperation` trapped),
independent of the ambient context. Normative operation order: mean =
stable-order sum/n; sample variance = sum((x-mean)^2)/(n-1); std and
annualization use `Decimal.sqrt()`; z = (current-mean)/std; weighted scores
multiply then sum in configuration order.

## Deterministic ranking

1. Compute base priority; fail closed on confidence outside the closed
   high/medium/low/unresolved set. Among valid inputs, reject only unresolved
   confidence or below-60%-coverage inputs. Resolved high, medium, and low
   confidence values are otherwise rankable.
2. Stable-sort eligible Events by base priority desc, `fully_known_at` desc,
   Event ID asc.
3. Within the frozen order, the first member of each script-derived
   non-singleton story family is unpenalized; each later member receives 15
   points unless its unordered pair with the frozen first member carries
   validated `distinct_material_development`.
4. `final_priority = max(0, base - penalty)`; the exact first-to-later
   canonical pair exempts that later member. A pair between later members is
   not transitive.
5. Re-sort by final priority desc, `fully_known_at` desc, Event ID asc, and
   return every eligible Event with base and final priorities plus deterministic
   ineligibility reasons. Ranking has no thresholds, tiers, formats, count
   limits, or sparse-output state.

## Market state

The v1 dashboard roles are S&P 500, CSI 300, Hang Seng, VIX, US 2y, US 10y,
China 10y, DXY, USD/CNH, copper, WTI, gold, and BTC. Votes map z to
supportive/neutral/adverse with `+/-0.5` boundaries; breadth uses `+/-0.20`.
Risk Appetite requires 2/4 votes, Rates 1/3, Liquidity 1/2, Growth 1/2,
Inflation 1/4. Regime is `unknown` unless Risk Appetite is known and >= 4/5
dimensions are known; `risk_off` when RA=-1 and sum<=-2; `risk_on` when
RA=+1 and sum>=2; otherwise `neutral`. The regime is informational and never
changes scoring, confidence, or ranking.
