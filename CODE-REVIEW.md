# Code Review Notes (Feb 3, 2026)

## Architecture Assessment
- **Engine**: Clean singleton pattern, DuckDB-based. Good.
- **Dataset/Column**: Nice fluent API via `__getattr__`. Pythonic.
- **Result types**: Well-structured ValidationResult with row-level errors.
- **Test coverage**: Good test organization, ~10K LOC across 28 test files.
- **Code quality**: Consistent style, good docstrings, no TODO/FIXME items.

## Issues Found

### P2: SQL Injection in Column Methods
**Files:** `src/duckguard/core/column.py`
**Methods:** `matches()`, `isin()`, `_get_failed_rows_pattern()`, `_get_failed_rows_isin()`
**Issue:** User-provided strings (regex patterns, enum values) are directly interpolated into SQL without escaping.
**Example:**
```python
# This would break:
orders.status.isin(["it's complicated"])
# Generates: ... NOT IN ('it's complicated') — SQL error

# This is worse:
orders.email.matches("'; DROP TABLE orders;--")
```
**Fix:** Use DuckDB parameterized queries or escape single quotes.
**Note:** The conditional/query-based checks DO have proper SQL injection prevention (QueryValidator, QuerySecurityValidator). This is only in the core column methods.
**Severity:** Medium — data quality tools typically receive developer-written code, not user input. But still should fix for correctness.

### P3: No `__version__` accessible without full import
**File:** `src/duckguard/__init__.py`  
**Issue:** Version is defined in `__init__.py` but requires importing all dependencies (duckdb, etc). Can't check version without duckdb installed.
**Fix:** Add version to a separate `_version.py` file or use importlib.metadata.

### P3: Singleton engine not thread-safe
**File:** `src/duckguard/core/engine.py`
**Issue:** `DuckGuardEngine.get_instance()` is not thread-safe. Two threads could create separate instances.
**Fix:** Add threading lock around instance creation.
**Note:** DuckDB connections are also not thread-safe, so this may be by design.

### P4: Print statements in kafka connector
**File:** `src/duckguard/connectors/kafka.py` line 304
**Issue:** `print()` used instead of proper logging.
**Fix:** Use `logging.getLogger(__name__)`.

## Improvements to Make

### High Priority (Week 1)
- [x] Fix SQL escaping in column.py methods (matches, isin, _get_failed_rows_*)
- [x] Fix SQL escaping in conditional checks (isin_when, matches_when)
- [x] Add `py.typed` marker file for PEP 561 typing support
- [ ] Verify all examples work on clean install (blocked: need pip/venv)

### Medium Priority (Week 2-3)
- [ ] Add `logging` module usage throughout (replace any print())
- [ ] Add thread safety note in docs or fix singleton
- [ ] Add more comprehensive error messages for connection failures
- [ ] Add type stubs or verify mypy passes

### Nice to Have
- [ ] Add `__all__` exports to subpackage `__init__.py` files
- [ ] Add more Colab examples for specific use cases
- [ ] Add contributing examples with good first issues
