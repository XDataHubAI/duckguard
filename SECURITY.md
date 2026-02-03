# Security Policy

## Supported Versions

| Version | Supported          |
|---------|:------------------:|
| 3.1.x   | :white_check_mark: |
| 3.0.x   | :white_check_mark: |
| 2.x     | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in DuckGuard, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email: **security@xdatahub.ai**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and provide a fix within 7 days for critical issues.

## Security Design

DuckGuard includes multi-layer SQL injection prevention for user-provided SQL:

1. **QueryValidator** — Validates conditions in conditional checks
2. **QuerySecurityValidator** — Enhanced validation for query-based checks
3. **ExpressionParser** — Whitelisted operators for multi-column expressions
4. **READ-ONLY enforcement** — All SQL operations are read-only
5. **Query timeout** — 30-second limit on custom queries
6. **Result limits** — 10,000 row maximum on query results

For details, see the [Security Audit Report](docs/security_audit_report.md).

## Dependencies

DuckGuard's core has 7 dependencies. We monitor for known vulnerabilities via GitHub's Dependabot.
