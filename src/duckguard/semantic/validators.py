"""Semantic type validators for DuckGuard.

Provides validation functions specific to each semantic type.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from duckguard.semantic.detector import SemanticType


@dataclass
class Validator:
    """A validation function for a semantic type.

    Attributes:
        name: Validator name
        description: Human-readable description
        validate: Validation function (value -> bool)
        pattern: Optional regex pattern
        error_message: Message template for failures
    """

    name: str
    description: str
    validate: Callable[[Any], bool]
    pattern: str | None = None
    error_message: str = "Value failed validation"


def _make_pattern_validator(pattern: str, flags: int = 0) -> Callable[[Any], bool]:
    """Create a validator from a regex pattern."""
    compiled = re.compile(pattern, flags)
    return lambda v: bool(compiled.match(str(v))) if v is not None else True


def _luhn_check(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = [int(d) for d in re.sub(r"\D", "", str(card_number))]
    if len(digits) < 13:
        return False

    # Luhn algorithm
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0


# Validators by semantic type
VALIDATORS: dict[SemanticType, list[Validator]] = {
    SemanticType.EMAIL: [
        Validator(
            name="email_format",
            description="Valid email format",
            validate=_make_pattern_validator(
                r"^[\w\.\-\+]+@[\w\.\-]+\.[a-zA-Z]{2,}$"
            ),
            pattern=r"^[\w\.\-\+]+@[\w\.\-]+\.[a-zA-Z]{2,}$",
            error_message="Invalid email format",
        ),
    ],
    SemanticType.PHONE: [
        Validator(
            name="phone_format",
            description="Valid phone number format",
            validate=_make_pattern_validator(r"^\+?[\d\s\-\(\)\.]{10,}$"),
            pattern=r"^\+?[\d\s\-\(\)\.]{10,}$",
            error_message="Invalid phone number format",
        ),
    ],
    SemanticType.URL: [
        Validator(
            name="url_format",
            description="Valid URL format",
            validate=_make_pattern_validator(
                r"^https?://[\w\.\-]+(/[\w\.\-\?=&%/]*)?$"
            ),
            pattern=r"^https?://[\w\.\-]+(/[\w\.\-\?=&%/]*)?$",
            error_message="Invalid URL format",
        ),
    ],
    SemanticType.UUID: [
        Validator(
            name="uuid_format",
            description="Valid UUID format",
            validate=_make_pattern_validator(
                r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
            ),
            pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            error_message="Invalid UUID format",
        ),
    ],
    SemanticType.SSN: [
        Validator(
            name="ssn_format",
            description="Valid SSN format (XXX-XX-XXXX)",
            validate=_make_pattern_validator(r"^\d{3}-\d{2}-\d{4}$"),
            pattern=r"^\d{3}-\d{2}-\d{4}$",
            error_message="Invalid SSN format",
        ),
    ],
    SemanticType.CREDIT_CARD: [
        Validator(
            name="credit_card_format",
            description="Valid credit card format",
            validate=_make_pattern_validator(
                r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$"
            ),
            pattern=r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$",
            error_message="Invalid credit card format",
        ),
        Validator(
            name="credit_card_luhn",
            description="Valid credit card number (Luhn check)",
            validate=_luhn_check,
            error_message="Credit card number fails Luhn check",
        ),
    ],
    SemanticType.IP_ADDRESS: [
        Validator(
            name="ipv4_format",
            description="Valid IPv4 address",
            validate=lambda v: _validate_ipv4(v),
            pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
            error_message="Invalid IPv4 address",
        ),
    ],
    SemanticType.ZIPCODE: [
        Validator(
            name="us_zipcode",
            description="Valid US ZIP code",
            validate=_make_pattern_validator(r"^\d{5}(-\d{4})?$"),
            pattern=r"^\d{5}(-\d{4})?$",
            error_message="Invalid US ZIP code format",
        ),
    ],
    SemanticType.DATE: [
        Validator(
            name="iso_date",
            description="Valid ISO date (YYYY-MM-DD)",
            validate=lambda v: _validate_date(v),
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            error_message="Invalid date format (expected YYYY-MM-DD)",
        ),
    ],
    SemanticType.DATETIME: [
        Validator(
            name="iso_datetime",
            description="Valid ISO datetime",
            validate=_make_pattern_validator(
                r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
            ),
            pattern=r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
            error_message="Invalid datetime format",
        ),
    ],
    SemanticType.TIME: [
        Validator(
            name="time_format",
            description="Valid time format (HH:MM:SS)",
            validate=_make_pattern_validator(r"^\d{2}:\d{2}(:\d{2})?$"),
            pattern=r"^\d{2}:\d{2}(:\d{2})?$",
            error_message="Invalid time format",
        ),
    ],
    SemanticType.COUNTRY_CODE: [
        Validator(
            name="iso_country_code",
            description="Valid ISO country code",
            validate=_make_pattern_validator(r"^[A-Z]{2,3}$"),
            pattern=r"^[A-Z]{2,3}$",
            error_message="Invalid country code (expected 2-3 letter ISO code)",
        ),
    ],
    SemanticType.LATITUDE: [
        Validator(
            name="latitude_range",
            description="Valid latitude (-90 to 90)",
            validate=lambda v: _validate_range(v, -90, 90),
            error_message="Latitude must be between -90 and 90",
        ),
    ],
    SemanticType.LONGITUDE: [
        Validator(
            name="longitude_range",
            description="Valid longitude (-180 to 180)",
            validate=lambda v: _validate_range(v, -180, 180),
            error_message="Longitude must be between -180 and 180",
        ),
    ],
    SemanticType.PERCENTAGE: [
        Validator(
            name="percentage_range",
            description="Valid percentage (0-100)",
            validate=lambda v: _validate_range(v, 0, 100),
            error_message="Percentage must be between 0 and 100",
        ),
    ],
    SemanticType.AGE: [
        Validator(
            name="age_range",
            description="Valid age (0-150)",
            validate=lambda v: _validate_range(v, 0, 150),
            error_message="Age must be between 0 and 150",
        ),
    ],
    SemanticType.CURRENCY: [
        Validator(
            name="non_negative",
            description="Non-negative currency amount",
            validate=lambda v: v is None or float(v) >= 0,
            error_message="Currency amount cannot be negative",
        ),
    ],
    SemanticType.SLUG: [
        Validator(
            name="slug_format",
            description="Valid URL slug",
            validate=_make_pattern_validator(r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
            pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
            error_message="Invalid slug format",
        ),
    ],
}


def _validate_ipv4(value: Any) -> bool:
    """Validate IPv4 address."""
    if value is None:
        return True
    try:
        parts = str(value).split(".")
        if len(parts) != 4:
            return False
        return all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, AttributeError):
        return False


def _validate_date(value: Any) -> bool:
    """Validate ISO date format and values."""
    if value is None:
        return True
    try:
        from datetime import datetime
        datetime.strptime(str(value), "%Y-%m-%d")
        return True
    except (ValueError, AttributeError):
        return False


def _validate_range(value: Any, min_val: float, max_val: float) -> bool:
    """Validate numeric range."""
    if value is None:
        return True
    try:
        num = float(value)
        return min_val <= num <= max_val
    except (ValueError, TypeError):
        return False


def get_validator_for_type(semantic_type: SemanticType) -> list[Validator]:
    """Get validators for a semantic type.

    Args:
        semantic_type: The semantic type

    Returns:
        List of validators for that type
    """
    return VALIDATORS.get(semantic_type, [])


def validate_value(value: Any, semantic_type: SemanticType) -> tuple[bool, list[str]]:
    """Validate a value against its semantic type.

    Args:
        value: Value to validate
        semantic_type: Expected semantic type

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    validators = get_validator_for_type(semantic_type)
    errors = []

    for validator in validators:
        try:
            if not validator.validate(value):
                errors.append(validator.error_message)
        except Exception as e:
            errors.append(f"Validation error: {e}")

    return len(errors) == 0, errors


def validate_column_values(
    values: list[Any],
    semantic_type: SemanticType
) -> tuple[int, int, list[tuple[Any, str]]]:
    """Validate a list of values against a semantic type.

    Args:
        values: Values to validate
        semantic_type: Expected semantic type

    Returns:
        Tuple of (valid_count, invalid_count, list of (invalid_value, error) tuples)
    """
    validators = get_validator_for_type(semantic_type)
    if not validators:
        return len(values), 0, []

    valid_count = 0
    invalid_count = 0
    invalid_samples: list[tuple[Any, str]] = []

    for value in values:
        if value is None:
            valid_count += 1
            continue

        is_valid = True
        error_msg = ""

        for validator in validators:
            try:
                if not validator.validate(value):
                    is_valid = False
                    error_msg = validator.error_message
                    break
            except Exception as e:
                is_valid = False
                error_msg = str(e)
                break

        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            if len(invalid_samples) < 10:  # Keep first 10 samples
                invalid_samples.append((value, error_msg))

    return valid_count, invalid_count, invalid_samples
