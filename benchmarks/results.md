# DuckGuard Benchmarks

**Dataset:** 500,000 rows, 55 MB CSV

| Operation | DuckGuard | pandas | Speedup |
|-----------|-----------|--------|---------|
| Connect | 0.424s | 2.437s | **5.7x faster** |
| Validate 5 Checks | 1.483s | 0.202s | 7.3x slower |
| Quality Score | 3.285s | 0.720s | 4.6x slower |
| Profile | 5.929s | 2.139s | 2.8x slower |
| Anomaly Detect | 0.000s | 0.018s | **58.3x faster** |
| Total | 11.122s | 5.516s | 2.0x slower |

*Generated with `python benchmarks/benchmark.py --rows 500000`*

Note: pandas comparison is basic (no equivalent features for PII detection, 
semantic analysis, row-level errors, data contracts, etc.). DuckGuard provides 
significantly more functionality per line of code.