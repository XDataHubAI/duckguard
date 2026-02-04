# Competitive Analysis (Feb 2026)

## Market Snapshot

| Tool | Stars | Forks | First Release | Approach |
|------|------:|------:|:-------------|----------|
| Great Expectations | 11,113 | 1,672 | 2018 | Python API, heavy OOP |
| Pandera | 4,190 | 370 | 2019 | DataFrame schemas (pandas/polars) |
| Soda Core | 2,281 | 254 | 2021 | YAML + SQL checks |
| **DuckGuard** | **2** | **0** | **Jan 2026** | **Pytest-like API + DuckDB** |

## Where We Win

### vs Great Expectations
- **DX**: 3 lines vs 50+ lines to start
- **Speed**: 10x faster (DuckDB vs pandas)
- **Memory**: 20x less (200MB vs 4GB for 1GB CSV)
- **API**: `orders.total_amount.between(0, 10000)` vs `expect_column_values_to_be_between(column="amount", min_value=0, max_value=10000)`
- **Batteries**: PII detection, anomaly detection, drift, reconciliation built in (GE has none)
- **Learning curve**: Minutes vs days

GE's weakness: massive complexity. Their own users complain about it. v1 rewrite broke everything.

### vs Soda Core
- **DX**: Python API vs YAML-first
- **Flexibility**: Code > YAML for complex validation logic
- **Built-in**: Anomaly detection (7 methods), PII, data contracts, quality scoring — Soda charges for these via Soda Cloud
- **Speed**: DuckDB vs pandas
- **Free**: All features open, no SaaS upsell

Soda's weakness: core OSS is limited, premium features behind paywall. YAML-only limits expressiveness.

### vs Pandera
- **Scope**: Full validation platform vs DataFrame schema validation
- **Engine**: DuckDB (handles any file/DB) vs pandas/polars only
- **Features**: Anomaly detection, drift, reconciliation, PII, freshness — Pandera has none
- **Speed**: Better on large files (DuckDB streaming vs in-memory DataFrames)

Pandera's weakness: tied to DataFrame libraries. Can't validate files, databases, or cloud storage directly.

## Where We're Weak (Honest Assessment)

1. **No community yet** — 0 real users, 0 blog mentions, 0 Stack Overflow answers
2. **No proof at scale** — benchmarks are from our own tests, not independent validation
3. ~~**Elastic License** — resolved: switched to Apache 2.0~~
4. **Single maintainer** — bus factor = 1
5. **No hosted/managed offering** — competitors have SaaS (GE Cloud, Soda Cloud)
6. **No documentation site** — just a README (FIXING THIS NOW)
7. **No AI features yet** — the `llm` dependency is declared but unused

## Strategic Positioning

Don't compete on features (we already have more). Compete on:

1. **Developer experience** — the "3 lines of code" story
2. **Speed** — reproducible benchmarks that people can run themselves
3. **Simplicity** — "data quality for people who just want to validate data"

Target persona: Data engineer who's annoyed by Great Expectations and hasn't committed to Soda yet.

## Launch Timing

- GE had major breaking changes in v1 → frustrated users
- Soda is pushing users toward paid Soda Cloud
- DuckDB ecosystem is growing fast (DuckDB itself is very popular)
- "AI-native" tools are getting attention

This is a good window.
