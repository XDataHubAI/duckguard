# Distribution & Drift Detection

Test whether columns follow expected statistical distributions using KS tests and chi-square tests.

## Quick Start

```python
from duckguard import connect

data = connect("measurements.csv")

# Test for normal distribution
result = data.temperature.expect_distribution_normal()
assert result.passed

# Test for uniform distribution
result = data.random_value.expect_distribution_uniform()
assert result.passed
```

!!! note
    Distributional checks require `scipy>=1.11.0`. Install with: `pip install 'duckguard[statistics]'`

## Normal Distribution Test

Uses the Kolmogorov-Smirnov test against a fitted normal distribution:

```python
result = data.temperature.expect_distribution_normal(
    significance_level=0.05  # default
)

print(result.details["pvalue"])     # p-value from KS test
print(result.details["statistic"])  # KS statistic
print(result.details["mean"])       # Sample mean
print(result.details["std"])        # Sample std deviation
```

The test passes when `p-value > significance_level` (null hypothesis: data is normal).

## Uniform Distribution Test

```python
result = data.random_value.expect_distribution_uniform(
    significance_level=0.05
)
```

Values are scaled to `[0, 1]` before testing against the standard uniform distribution.

## KS Test (Any Distribution)

Test against any scipy distribution:

```python
# Exponential distribution
result = data.wait_times.expect_ks_test(distribution="expon")

# Normal (same as expect_distribution_normal)
result = data.values.expect_ks_test(distribution="norm")
```

## Chi-Square Test (Categorical)

Test if observed frequencies match expected frequencies:

```python
# Test if dice is fair
result = data.roll.expect_chi_square_test(
    expected_frequencies={1: 1/6, 2: 1/6, 3: 1/6, 4: 1/6, 5: 1/6, 6: 1/6}
)

# Test against uniform (no expected_frequencies = assumes uniform)
result = data.category.expect_chi_square_test()
```

Result details include observed vs expected frequency breakdown:

```python
print(result.details["observed"])   # {'A': 50, 'B': 48, 'C': 52}
print(result.details["expected"])   # {'A': 50.0, 'B': 50.0, 'C': 50.0}
print(result.details["degrees_of_freedom"])
```

## Minimum Sample Size

All distributional tests require at least **30 samples**. The check fails with a clear message if fewer are available.

## YAML Rules

```yaml
checks:
  temperature:
    - distribution_normal:
        significance_level: 0.05

  random_value:
    - distribution_uniform

  category:
    - distribution_chi_square:
        expected_frequencies:
          A: 0.33
          B: 0.33
          C: 0.34
```

## Interpreting Results

| p-value | Interpretation |
|---------|---------------|
| > 0.05 | No evidence against the hypothesized distribution (**pass**) |
| 0.01–0.05 | Weak evidence against — borderline |
| < 0.01 | Strong evidence data does NOT follow the distribution (**fail**) |

Lower `significance_level` = stricter test (fewer false positives, more false negatives).
