"""Data Contracts for DuckGuard.

Data contracts define the expected schema, quality SLAs, and ownership
for data sources. They enable producer-consumer agreements and
breaking change detection.

Example:
    from duckguard.contracts import load_contract, validate_contract

    contract = load_contract("contracts/orders.contract.yaml")
    result = validate_contract(contract, "data/orders.csv")

    if not result.passed:
        print(f"Contract violations: {result.violations}")
"""

from duckguard.contracts.diff import SchemaDiff, diff_contracts
from duckguard.contracts.generator import generate_contract
from duckguard.contracts.loader import contract_to_yaml, load_contract, load_contract_from_string
from duckguard.contracts.schema import (
    ContractMetadata,
    DataContract,
    FieldType,
    QualitySLA,
    SchemaField,
)
from duckguard.contracts.validator import ContractValidationResult, validate_contract

__all__ = [
    # Schema
    "DataContract",
    "SchemaField",
    "FieldType",
    "QualitySLA",
    "ContractMetadata",
    # Loading
    "load_contract",
    "load_contract_from_string",
    "contract_to_yaml",
    # Validation
    "validate_contract",
    "ContractValidationResult",
    # Generation
    "generate_contract",
    # Diff
    "diff_contracts",
    "SchemaDiff",
]
