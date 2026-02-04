"""
DuckGuard + Hugging Face Datasets Integration

Profile and validate any HF dataset in 3 lines.
Requires: pip install duckguard datasets

Usage:
    python examples/huggingface_integration.py
"""

from datasets import load_dataset
from duckguard import connect, AutoProfiler, SemanticAnalyzer, detect_anomalies


def validate_hf_dataset(dataset_name: str, split: str = "train", max_rows: int = 50_000):
    """Load a HF dataset and run DuckGuard quality analysis."""
    print(f"\n{'='*60}")
    print(f"Dataset: {dataset_name} ({split})")
    print(f"{'='*60}")

    # Load from HF and convert to pandas → DuckGuard
    ds = load_dataset(dataset_name, split=split)
    if len(ds) > max_rows:
        ds = ds.select(range(max_rows))
        print(f"  (sampled {max_rows:,} rows)")

    df = ds.to_pandas()
    data = connect(df)

    print(f"\nRows: {data.row_count:,}")
    print(f"Columns: {data.columns}")

    # Quality score
    score = data.score()
    print(f"\n📊 Quality: {score.grade} ({score.overall:.1f}/100)")
    print(f"   Completeness: {score.completeness:.1f}%")
    print(f"   Uniqueness:   {score.uniqueness:.1f}%")

    # Profile
    profile = AutoProfiler().profile(data)
    print(f"\n🔍 Column Profile:")
    for col in profile.columns:
        print(f"   {col.name:<30} {col.dtype:<10} nulls={col.null_percent:.1f}%  grade={col.quality_grade}")

    # PII detection
    analysis = SemanticAnalyzer().analyze(data)
    if analysis.pii_columns:
        print(f"\n🔒 PII found in: {analysis.pii_columns}")
    else:
        print(f"\n🔒 No PII detected")

    # Suggested rules
    print(f"\n📋 Suggested rules: {len(profile.suggested_rules)}")
    for rule in profile.suggested_rules[:5]:
        print(f"   • {rule}")
    if len(profile.suggested_rules) > 5:
        print(f"   ... and {len(profile.suggested_rules) - 5} more")

    return data, profile


if __name__ == "__main__":
    # Example 1: Classic ML dataset
    print("\n" + "🤗 DuckGuard + Hugging Face Datasets".center(60))

    # Titanic (small, well-known)
    validate_hf_dataset("phihung/titanic", split="train")

    # You can run on any HF dataset:
    # validate_hf_dataset("scikit-learn/iris", split="train")
    # validate_hf_dataset("mozilla-foundation/common_voice_11_0", split="train[:1000]")
    # validate_hf_dataset("imdb", split="train")

    print("\n\n✅ Done! Install: pip install duckguard datasets")
    print("📚 Docs: https://xdatahubai.github.io/duckguard/")
