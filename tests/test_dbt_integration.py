"""Tests for dbt integration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from duckguard.integrations import dbt
from duckguard.rules.schema import (
    Check,
    CheckType,
    ColumnRules,
    RuleSet,
    TableRules,
)


@pytest.fixture
def sample_ruleset():
    """Create a sample ruleset for testing."""
    return RuleSet(
        name="orders",
        description="Order validation rules",
        table=TableRules(
            checks=[
                Check(type=CheckType.ROW_COUNT, value=100, operator=">="),
            ]
        ),
        columns={
            "order_id": ColumnRules(
                name="order_id",
                description="Unique order identifier",
                checks=[
                    Check(type=CheckType.NOT_NULL),
                    Check(type=CheckType.UNIQUE),
                ],
            ),
            "amount": ColumnRules(
                name="amount",
                description="Order amount",
                checks=[
                    Check(type=CheckType.NOT_NULL),
                    Check(type=CheckType.BETWEEN, value=[0, 10000]),
                    Check(type=CheckType.POSITIVE),
                ],
            ),
            "status": ColumnRules(
                name="status",
                description="Order status",
                checks=[
                    Check(type=CheckType.ALLOWED_VALUES, value=["pending", "shipped", "delivered"]),
                ],
            ),
            "email": ColumnRules(
                name="email",
                description="Customer email",
                checks=[
                    Check(type=CheckType.PATTERN, value=r"^[\w.-]+@[\w.-]+\.\w+$"),
                ],
            ),
        },
    )


class TestRulesToDbtTests:
    """Tests for converting rules to dbt tests."""

    def test_basic_conversion(self, sample_ruleset):
        """Test basic conversion of rules to dbt tests."""
        result = dbt.rules_to_dbt_tests(sample_ruleset)

        assert "models" in result
        assert len(result["models"]) == 1

        model = result["models"][0]
        assert model["name"] == "orders"
        assert model["description"] == "Order validation rules"
        assert "columns" in model

    def test_not_null_conversion(self, sample_ruleset):
        """Test NOT_NULL check conversion."""
        result = dbt.rules_to_dbt_tests(sample_ruleset)
        columns = {c["name"]: c for c in result["models"][0]["columns"]}

        order_id_tests = columns["order_id"]["tests"]
        assert "not_null" in order_id_tests

    def test_unique_conversion(self, sample_ruleset):
        """Test UNIQUE check conversion."""
        result = dbt.rules_to_dbt_tests(sample_ruleset)
        columns = {c["name"]: c for c in result["models"][0]["columns"]}

        order_id_tests = columns["order_id"]["tests"]
        assert "unique" in order_id_tests

    def test_accepted_values_conversion(self, sample_ruleset):
        """Test ALLOWED_VALUES check conversion."""
        result = dbt.rules_to_dbt_tests(sample_ruleset)
        columns = {c["name"]: c for c in result["models"][0]["columns"]}

        status_tests = columns["status"]["tests"]
        assert any(
            isinstance(t, dict) and "accepted_values" in t
            for t in status_tests
        )

        # Check values are preserved
        accepted_test = next(
            t for t in status_tests
            if isinstance(t, dict) and "accepted_values" in t
        )
        assert accepted_test["accepted_values"]["values"] == ["pending", "shipped", "delivered"]

    def test_between_conversion(self, sample_ruleset):
        """Test BETWEEN check conversion."""
        result = dbt.rules_to_dbt_tests(sample_ruleset)
        columns = {c["name"]: c for c in result["models"][0]["columns"]}

        amount_tests = columns["amount"]["tests"]
        # Should have dbt_utils.expression_is_true for range check
        range_test = [
            t for t in amount_tests
            if isinstance(t, dict) and "dbt_utils.expression_is_true" in t
        ]
        assert len(range_test) > 0


class TestExportToSchema:
    """Tests for exporting rules to schema.yml."""

    def test_export_creates_file(self, sample_ruleset):
        """Test that export creates a schema.yml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "models" / "schema.yml"
            result_path = dbt.export_to_schema(sample_ruleset, output_path)

            assert result_path.exists()
            assert result_path == output_path

    def test_export_valid_yaml(self, sample_ruleset):
        """Test that exported file is valid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schema.yml"
            dbt.export_to_schema(sample_ruleset, output_path)

            with open(output_path) as f:
                content = yaml.safe_load(f)

            assert "models" in content
            assert len(content["models"]) == 1

    def test_export_merge_existing(self, sample_ruleset):
        """Test merging with existing schema.yml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schema.yml"

            # Create existing file
            existing = {
                "models": [
                    {
                        "name": "orders",
                        "columns": [
                            {"name": "customer_id", "tests": ["not_null"]},
                        ],
                    }
                ]
            }
            with open(output_path, "w") as f:
                yaml.dump(existing, f)

            # Export and merge
            dbt.export_to_schema(sample_ruleset, output_path, merge=True)

            with open(output_path) as f:
                content = yaml.safe_load(f)

            # Should have merged columns
            columns = {c["name"]: c for c in content["models"][0]["columns"]}
            assert "customer_id" in columns  # Existing column preserved
            assert "order_id" in columns  # New column added


class TestGenerateSingularTests:
    """Tests for generating dbt singular tests."""

    def test_generate_singular_tests(self):
        """Test generating singular test files."""
        ruleset = RuleSet(
            name="test_table",
            table=TableRules(),
            columns={
                "email": ColumnRules(
                    name="email",
                    checks=[
                        Check(type=CheckType.NULL_PERCENT, value=5, operator="<="),
                    ],
                ),
                "user_id": ColumnRules(
                    name="user_id",
                    checks=[
                        Check(type=CheckType.UNIQUE_PERCENT, value=95, operator=">="),
                    ],
                ),
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            created_files = dbt.generate_singular_tests(ruleset, tmpdir)

            assert len(created_files) == 2
            assert all(f.exists() for f in created_files)
            assert any("null_percent" in str(f) for f in created_files)
            assert any("unique_percent" in str(f) for f in created_files)


class TestImportFromDbt:
    """Tests for importing dbt tests as DuckGuard rules."""

    def test_import_basic_schema(self):
        """Test importing a basic dbt schema.yml."""
        schema = {
            "models": [
                {
                    "name": "orders",
                    "description": "Order model",
                    "columns": [
                        {
                            "name": "order_id",
                            "tests": ["not_null", "unique"],
                        },
                        {
                            "name": "status",
                            "tests": [
                                {"accepted_values": {"values": ["pending", "complete"]}}
                            ],
                        },
                    ],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(schema, f)
            schema_path = f.name

        try:
            ruleset = dbt.import_from_dbt(schema_path)

            assert ruleset.name == "orders"
            assert "order_id" in ruleset.columns
            assert "status" in ruleset.columns

            # Check order_id has not_null and unique
            order_id_checks = [c.type for c in ruleset.columns["order_id"].checks]
            assert CheckType.NOT_NULL in order_id_checks
            assert CheckType.UNIQUE in order_id_checks

            # Check status has allowed_values
            status_checks = ruleset.columns["status"].checks
            assert any(c.type == CheckType.ALLOWED_VALUES for c in status_checks)
        finally:
            Path(schema_path).unlink()

    def test_import_empty_schema(self):
        """Test importing empty schema raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({}, f)
            schema_path = f.name

        try:
            with pytest.raises(ValueError, match="No models found"):
                dbt.import_from_dbt(schema_path)
        finally:
            Path(schema_path).unlink()
