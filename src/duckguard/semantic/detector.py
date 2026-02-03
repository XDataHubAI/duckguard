"""Semantic type detector for DuckGuard.

Automatically identifies the semantic meaning of data columns based on:
- Column names (e.g., "email", "phone_number")
- Data patterns (e.g., regex matching)
- Value distributions
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SemanticType(Enum):
    """Semantic types that can be detected."""

    # Identity types
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UUID = "uuid"
    ID = "id"

    # Contact information
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    IP_ADDRESS = "ip_address"

    # Personal information (PII)
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    PERSON_NAME = "person_name"
    ADDRESS = "address"

    # Location
    COUNTRY = "country"
    COUNTRY_CODE = "country_code"
    STATE = "state"
    CITY = "city"
    ZIPCODE = "zipcode"
    LATITUDE = "latitude"
    LONGITUDE = "longitude"

    # Date/Time
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    TIMESTAMP = "timestamp"
    YEAR = "year"
    MONTH = "month"
    DAY = "day"

    # Numeric
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    QUANTITY = "quantity"
    AGE = "age"
    COUNT = "count"

    # Categorical
    BOOLEAN = "boolean"
    ENUM = "enum"
    STATUS = "status"
    CATEGORY = "category"
    GENDER = "gender"

    # Text
    TEXT = "text"
    DESCRIPTION = "description"
    TITLE = "title"
    SLUG = "slug"
    CODE = "code"
    IDENTIFIER = "identifier"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class SemanticTypeResult:
    """Result of semantic type detection.

    Attributes:
        semantic_type: The detected semantic type
        confidence: Confidence score (0-1)
        reasons: Reasons for the detection
        is_pii: Whether this is personally identifiable information
        suggested_validations: List of suggested validation rules
        metadata: Additional detection metadata
    """

    semantic_type: SemanticType
    confidence: float
    reasons: list[str] = field(default_factory=list)
    is_pii: bool = False
    suggested_validations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# Column name patterns for detection
NAME_PATTERNS: dict[SemanticType, list[str]] = {
    SemanticType.EMAIL: [
        r"e?mail", r"email_?addr(ess)?", r"user_?email", r"contact_?email"
    ],
    SemanticType.PHONE: [
        r"phone", r"tel(ephone)?", r"mobile", r"cell", r"fax",
        r"phone_?(num(ber)?)?", r"contact_?phone"
    ],
    SemanticType.URL: [
        r"url", r"link", r"href", r"website", r"web_?addr(ess)?", r"uri"
    ],
    SemanticType.UUID: [
        r"uuid", r"guid", r".*_uuid$", r".*_guid$"
    ],
    SemanticType.PRIMARY_KEY: [
        r"^id$", r".*_id$", r"pk", r"primary_?key"
    ],
    SemanticType.FOREIGN_KEY: [
        r"fk_.*", r".*_fk$", r"ref_.*", r".*_ref$"
    ],
    SemanticType.SSN: [
        r"ssn", r"social_?security", r"tax_?id", r"sin"
    ],
    SemanticType.CREDIT_CARD: [
        r"cc_?(num(ber)?)?", r"card_?(num(ber)?)?", r"credit_?card",
        r"pan", r"payment_?card"
    ],
    SemanticType.PERSON_NAME: [
        r"name", r"first_?name", r"last_?name", r"full_?name",
        r"given_?name", r"surname", r"family_?name"
    ],
    SemanticType.ADDRESS: [
        r"addr(ess)?", r"street", r"address_?line", r"street_?addr(ess)?"
    ],
    SemanticType.COUNTRY: [
        r"country", r"nation", r"country_?name"
    ],
    SemanticType.COUNTRY_CODE: [
        r"country_?code", r"iso_?country", r"cc"
    ],
    SemanticType.STATE: [
        r"state", r"province", r"region", r"state_?code"
    ],
    SemanticType.CITY: [
        r"city", r"town", r"municipality"
    ],
    SemanticType.ZIPCODE: [
        r"zip", r"zip_?code", r"postal", r"postal_?code", r"postcode"
    ],
    SemanticType.LATITUDE: [
        r"lat(itude)?", r"geo_?lat"
    ],
    SemanticType.LONGITUDE: [
        r"lon(g)?(itude)?", r"lng", r"geo_?lon(g)?"
    ],
    SemanticType.DATE: [
        r"date", r".*_date$", r".*_dt$", r"dob", r"birth_?date"
    ],
    SemanticType.DATETIME: [
        r"datetime", r".*_datetime$", r"timestamp"
    ],
    SemanticType.TIME: [
        r"^time$", r".*_time$"
    ],
    SemanticType.TIMESTAMP: [
        r"timestamp", r".*_ts$", r"created_?at", r"updated_?at",
        r"modified_?at", r"deleted_?at"
    ],
    SemanticType.YEAR: [
        r"year", r"yr"
    ],
    SemanticType.MONTH: [
        r"month", r"mo"
    ],
    SemanticType.CURRENCY: [
        r"amount", r"price", r"cost", r"total", r"subtotal",
        r"revenue", r"salary", r"fee", r"charge", r"balance",
        r"payment", r".*_amt$", r".*_amount$"
    ],
    SemanticType.PERCENTAGE: [
        r"percent(age)?", r"rate", r"ratio", r"pct", r".*_pct$"
    ],
    SemanticType.QUANTITY: [
        r"qty", r"quantity", r"count", r"num(ber)?", r".*_qty$"
    ],
    SemanticType.AGE: [
        r"age", r"years_?old"
    ],
    SemanticType.BOOLEAN: [
        r"is_.*", r"has_.*", r"can_.*", r"should_.*", r"enabled",
        r"disabled", r"active", r"flag", r".*_flag$"
    ],
    SemanticType.STATUS: [
        r"status", r"state", r"stage", r"phase"
    ],
    SemanticType.CATEGORY: [
        r"type", r"category", r"kind", r"class", r"group", r".*_type$"
    ],
    SemanticType.GENDER: [
        r"gender", r"sex"
    ],
    SemanticType.DESCRIPTION: [
        r"desc(ription)?", r"summary", r"notes?", r"comment", r"remarks?"
    ],
    SemanticType.TITLE: [
        r"title", r"subject", r"heading", r"headline"
    ],
    SemanticType.SLUG: [
        r"slug", r"permalink", r"url_?key"
    ],
    SemanticType.IP_ADDRESS: [
        r"ip", r"ip_?addr(ess)?", r"client_?ip", r"remote_?ip"
    ],
    SemanticType.CODE: [
        r"code", r".*_code$"
    ],
    SemanticType.IDENTIFIER: [
        r".*_id$", r".*_key$", r".*_code$", r".*_num(ber)?$", r".*_no$"
    ],
}

# Value patterns for detection
VALUE_PATTERNS: dict[SemanticType, str] = {
    SemanticType.EMAIL: r"^[\w\.\-\+]+@[\w\.\-]+\.[a-zA-Z]{2,}$",
    SemanticType.PHONE: r"^\+?[\d\s\-\(\)\.]{10,}$",
    SemanticType.URL: r"^https?://[\w\.\-]+(/[\w\.\-\?=&%/]*)?$",
    SemanticType.UUID: r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    SemanticType.SSN: r"^\d{3}-\d{2}-\d{4}$",
    SemanticType.CREDIT_CARD: r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$",
    SemanticType.IP_ADDRESS: r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
    SemanticType.ZIPCODE: r"^\d{5}(-\d{4})?$",
    SemanticType.DATE: r"^\d{4}-\d{2}-\d{2}$",
    SemanticType.DATETIME: r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
    SemanticType.TIME: r"^\d{2}:\d{2}(:\d{2})?$",
    SemanticType.COUNTRY_CODE: r"^[A-Z]{2,3}$",
    SemanticType.SLUG: r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    SemanticType.LATITUDE: r"^-?([1-8]?\d(\.\d+)?|90(\.0+)?)$",
    SemanticType.LONGITUDE: r"^-?(1[0-7]\d(\.\d+)?|180(\.0+)?|\d{1,2}(\.\d+)?)$",
    # Identifier pattern: PREFIX-NUMBER, ABC123, etc. (uppercase or mixed case with numbers)
    SemanticType.IDENTIFIER: r"^[A-Z][A-Z0-9]*[-_]?\d+$|^[A-Z]{2,}[-_][A-Z0-9]+$",
}

# Patterns that must be matched case-sensitively (not using IGNORECASE)
CASE_SENSITIVE_PATTERNS = {
    SemanticType.SLUG,  # Slugs must be lowercase
    SemanticType.IDENTIFIER,  # Identifiers are typically uppercase
    SemanticType.COUNTRY_CODE,  # Country codes are uppercase
}

# PII types that should be flagged
PII_TYPES = {
    SemanticType.EMAIL,
    SemanticType.PHONE,
    SemanticType.SSN,
    SemanticType.CREDIT_CARD,
    SemanticType.PERSON_NAME,
    SemanticType.ADDRESS,
}

# Suggested validations per type
TYPE_VALIDATIONS: dict[SemanticType, list[str]] = {
    SemanticType.EMAIL: ["pattern: email", "unique"],
    SemanticType.PHONE: ["pattern: phone"],
    SemanticType.URL: ["pattern: url"],
    SemanticType.UUID: ["pattern: uuid", "unique"],
    SemanticType.PRIMARY_KEY: ["not_null", "unique"],
    SemanticType.FOREIGN_KEY: ["not_null"],
    SemanticType.SSN: ["pattern: ssn"],
    SemanticType.CREDIT_CARD: ["pattern: credit_card"],
    SemanticType.IP_ADDRESS: ["pattern: ip_address"],
    SemanticType.ZIPCODE: ["pattern: zipcode"],
    SemanticType.DATE: ["pattern: date_iso"],
    SemanticType.DATETIME: ["pattern: datetime_iso"],
    SemanticType.CURRENCY: ["non_negative"],
    SemanticType.PERCENTAGE: ["range: [0, 100]"],
    SemanticType.QUANTITY: ["non_negative"],
    SemanticType.AGE: ["range: [0, 150]"],
    SemanticType.LATITUDE: ["range: [-90, 90]"],
    SemanticType.LONGITUDE: ["range: [-180, 180]"],
    SemanticType.BOOLEAN: ["allowed_values: [true, false]"],
    SemanticType.COUNTRY_CODE: ["pattern: country_code"],
    SemanticType.IDENTIFIER: ["not_null"],
}


def detect_type(
    dataset_or_name,
    column_name: str | None = None,
    sample_values: list[Any] | None = None,
    unique_percent: float | None = None,
    null_percent: float | None = None,
) -> SemanticType | None:
    """Detect the semantic type of a column.

    Can be called two ways:
    1. detect_type(dataset, "column_name") - high-level API
    2. detect_type("column_name", sample_values=[...]) - low-level API

    Args:
        dataset_or_name: Either a Dataset object or column name string
        column_name: Column name (when first arg is Dataset)
        sample_values: Sample values from the column (low-level API)
        unique_percent: Percentage of unique values (low-level API)
        null_percent: Percentage of null values (low-level API)

    Returns:
        SemanticType enum value (or None if unknown)
    """
    detector = SemanticTypeDetector()

    # High-level API: detect_type(dataset, "column_name")
    if hasattr(dataset_or_name, 'columns') and column_name is not None:
        dataset = dataset_or_name
        col = dataset[column_name]
        try:
            sample = col.get_distinct_values(limit=100)
        except Exception:
            sample = []

        result = detector.detect(
            column_name,
            sample,
            col.unique_percent,
            col.null_percent,
        )
        return result.semantic_type

    # Low-level API: detect_type("column_name", sample_values=[...])
    result = detector.detect(
        str(dataset_or_name),
        sample_values or [],
        unique_percent,
        null_percent,
    )
    return result.semantic_type


def detect_types_for_dataset(dataset) -> dict[str, SemanticType | None]:
    """Detect semantic types for all columns in a dataset.

    Args:
        dataset: Dataset to analyze

    Returns:
        Dict mapping column names to SemanticType (or None if unknown)
    """
    detector = SemanticTypeDetector()
    results = {}

    for col_name in dataset.columns:
        col = dataset[col_name]
        try:
            sample = col.get_distinct_values(limit=100)
        except Exception:
            sample = []

        result = detector.detect(
            col_name,
            sample,
            col.unique_percent,
            col.null_percent,
        )
        results[col_name] = result.semantic_type

    return results


class SemanticTypeDetector:
    """Detects semantic types for data columns."""

    def __init__(self):
        self.name_patterns = NAME_PATTERNS
        self.value_patterns = VALUE_PATTERNS

    def detect(
        self,
        column_name: str,
        sample_values: list[Any] | None = None,
        unique_percent: float | None = None,
        null_percent: float | None = None,
    ) -> SemanticTypeResult:
        """Detect semantic type for a column."""
        reasons = []
        candidates: dict[SemanticType, float] = {}

        # 1. Check column name patterns
        name_lower = column_name.lower().replace("-", "_")
        for sem_type, patterns in self.name_patterns.items():
            for pattern in patterns:
                if re.match(pattern, name_lower, re.IGNORECASE):
                    candidates[sem_type] = candidates.get(sem_type, 0) + 0.4
                    reasons.append(f"Column name matches '{sem_type.value}' pattern")
                    break

        # 2. Check value patterns
        if sample_values:
            string_values = [str(v) for v in sample_values if v is not None]
            if string_values:
                for sem_type, pattern in self.value_patterns.items():
                    # Use case-sensitive matching for certain patterns
                    flags = 0 if sem_type in CASE_SENSITIVE_PATTERNS else re.IGNORECASE
                    match_count = sum(
                        1 for v in string_values[:50]
                        if re.match(pattern, v, flags)
                    )
                    match_rate = match_count / min(len(string_values), 50)

                    if match_rate >= 0.8:
                        candidates[sem_type] = candidates.get(sem_type, 0) + 0.5
                        reasons.append(
                            f"{match_rate:.0%} of values match {sem_type.value} pattern"
                        )
                    elif match_rate >= 0.5:
                        candidates[sem_type] = candidates.get(sem_type, 0) + 0.3
                        reasons.append(
                            f"{match_rate:.0%} of values match {sem_type.value} pattern"
                        )

        # 3. Check uniqueness for ID/key detection
        if unique_percent is not None:
            if unique_percent == 100 and null_percent == 0:
                # Likely a primary key
                if SemanticType.PRIMARY_KEY not in candidates:
                    candidates[SemanticType.PRIMARY_KEY] = 0.3
                else:
                    candidates[SemanticType.PRIMARY_KEY] += 0.2
                reasons.append("100% unique with no nulls suggests primary key")

        # 4. Check for enum/categorical
        if sample_values and unique_percent is not None:
            unique_count = len(set(sample_values))
            if unique_count <= 20 and unique_percent < 5:
                candidates[SemanticType.ENUM] = candidates.get(SemanticType.ENUM, 0) + 0.3
                reasons.append(f"Low cardinality ({unique_count} values) suggests enum")

        # 5. Check for boolean
        if sample_values:
            values_set = set(str(v).lower() for v in sample_values if v is not None)
            bool_values = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
            if values_set.issubset(bool_values) and len(values_set) <= 2:
                candidates[SemanticType.BOOLEAN] = candidates.get(SemanticType.BOOLEAN, 0) + 0.5
                reasons.append("Values are boolean-like")

        # Determine best match
        if not candidates:
            return SemanticTypeResult(
                semantic_type=SemanticType.UNKNOWN,
                confidence=0.0,
                reasons=["No semantic type detected"],
            )

        # Get highest confidence type
        best_type = max(candidates, key=lambda t: candidates[t])
        confidence = min(candidates[best_type], 1.0)

        # Check if PII
        is_pii = best_type in PII_TYPES

        # Get suggested validations
        validations = TYPE_VALIDATIONS.get(best_type, [])

        return SemanticTypeResult(
            semantic_type=best_type,
            confidence=confidence,
            reasons=reasons,
            is_pii=is_pii,
            suggested_validations=validations,
            metadata={
                "column_name": column_name,
                "all_candidates": {t.value: s for t, s in candidates.items()},
            },
        )
