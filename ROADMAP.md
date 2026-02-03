# DuckGuard Roadmap

## v3.2 — AI-Powered Quality (Target: March 2026)

### AI Features
- [ ] `duckguard explain <file>` — AI summarizes data quality issues in plain English
- [ ] `duckguard suggest <file>` — AI generates validation rules from data patterns
- [ ] `duckguard fix <file>` — AI suggests data cleaning steps
- [ ] Natural language rule definition ("ensure no nulls in customer_id")
- [ ] AI-powered anomaly explanation (why is this anomalous?)

### Core Improvements
- [ ] Streaming validation for large files (process in chunks)
- [ ] Parallel check execution (run independent checks concurrently)
- [ ] Progress bars for long-running validations
- [ ] `duckguard watch` — file watcher mode for continuous validation

### Integrations
- [ ] Dagster asset checks
- [ ] Prefect flow integration
- [ ] Spark connector
- [ ] dbt-core 1.8+ native integration

### Documentation
- [x] MkDocs Material documentation site
- [ ] Video tutorials (YouTube)
- [ ] Interactive playground (Pyodide/WASM)

---

## v4.0 — Enterprise (Target: Q3 2026)

### Data Observability
- [ ] Validation history dashboard
- [ ] Quality trend visualization
- [ ] Automated alerting on quality degradation
- [ ] SLA monitoring and tracking

### Governance
- [ ] Data lineage tracking
- [ ] Column-level data catalog
- [ ] Access control for validation rules
- [ ] Audit trail for rule changes

### Scale
- [ ] Distributed validation (Ray/Dask backend)
- [ ] Native cloud warehouse validation (push-down queries)
- [ ] Real-time streaming validation (Kafka, Kinesis)
- [ ] Multi-tenant SaaS offering

---

## Community Goals

- [ ] 1,000 GitHub stars
- [ ] 10,000 monthly PyPI downloads
- [ ] 50+ community contributors
- [ ] Discord community with 500+ members
- [ ] Conference talks (PyCon, Data Council, dbt Coalesce)
