# GitHub Actions

Run DuckGuard checks in CI/CD to catch data quality issues before merge.

## Quick Start

```yaml
# .github/workflows/data-quality.yml
name: Data Quality

on:
  push:
    paths: ['data/**', 'duckguard.yaml', 'contracts/**']
  pull_request:
    paths: ['data/**', 'duckguard.yaml', 'contracts/**']

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install DuckGuard
        run: pip install duckguard

      - name: Run quality checks
        run: duckguard check data/orders.csv --config duckguard.yaml
```

The CLI exits with code 1 on failure, which fails the workflow.

## YAML Rule Checks

```yaml
      - name: Run YAML rules
        run: duckguard check data/orders.csv --config duckguard.yaml

      - name: Run quick checks
        run: duckguard check data/orders.csv --not-null order_id --unique email
```

## Contract Validation

```yaml
      - name: Validate contracts
        run: |
          duckguard contract validate data/orders.csv \
            --contract contracts/orders.contract.yaml
```

## pytest Tests

```yaml
      - name: Run data quality tests
        run: pytest tests/test_data_quality.py -v --junitxml=results.xml

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: results.xml
```

## Quality Reports

Generate and upload HTML reports as artifacts:

```yaml
      - name: Generate quality report
        run: |
          duckguard report data/orders.csv \
            --config duckguard.yaml \
            --output report.html \
            --title "Orders Quality Report"

      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: quality-report
          path: report.html
```

## Quality Gate with Score

Fail the build if quality drops below a threshold:

```yaml
      - name: Quality gate
        run: |
          python -c "
          from duckguard import connect
          data = connect('data/orders.csv')
          score = data.score()
          print(f'Quality: {score.overall:.0f}/100 ({score.grade})')
          if score.overall < 80:
              raise SystemExit(f'Quality {score.overall:.0f} below 80 threshold')
          "
```

## Contract Diff on PR

Check for breaking changes when contracts are modified:

```yaml
      - name: Check contract changes
        if: github.event_name == 'pull_request'
        run: |
          git show HEAD~1:contracts/orders.contract.yaml > /tmp/old.yaml 2>/dev/null || exit 0
          duckguard contract diff /tmp/old.yaml contracts/orders.contract.yaml
```

## Full Pipeline Example

```yaml
name: Data Quality Pipeline

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install duckguard

      - name: Profile data
        run: duckguard profile data/orders.csv

      - name: Run checks
        run: duckguard check data/orders.csv --config duckguard.yaml

      - name: Validate contract
        run: |
          duckguard contract validate data/orders.csv \
            --contract contracts/orders.contract.yaml

      - name: Generate report
        if: always()
        run: duckguard report data/orders.csv --output report.html

      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: quality-report
          path: report.html
```

## Scheduled Checks

Run quality checks on a schedule (not just on push):

```yaml
on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8am UTC
```
