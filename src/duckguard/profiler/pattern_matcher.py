"""
Enhanced pattern matching for profiling in DuckGuard 3.0.

This module provides comprehensive pattern detection with confidence scoring:
- 25+ built-in patterns (email, phone, SSN, credit card, etc.)
- Custom pattern support
- Confidence scoring based on match rate
- Pattern validation and suggestions

Example:
    >>> from duckguard.profiler.pattern_matcher import PatternMatcher
    >>> matcher = PatternMatcher()
    >>> patterns = matcher.detect_patterns(column_values)
    >>> for pattern in patterns:
    ...     print(f"{pattern['type']}: {pattern['confidence']}%")
"""

import re
from dataclasses import dataclass

import numpy as np


@dataclass
class PatternMatch:
    """Result of pattern matching."""

    pattern_type: str
    pattern_regex: str
    match_count: int
    total_count: int
    confidence: float  # 0-100
    examples: list[str]  # Sample matches


class PatternMatcher:
    """
    Detects common patterns in string data with confidence scoring.

    Provides built-in patterns for common data types and supports
    custom pattern definitions.
    """

    # Built-in patterns with names and regex
    PATTERNS = {
        # Contact information
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone_us': r'^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$',
        'phone_intl': r'^\+[1-9]\d{1,14}$',
        'url': r'^https?://[^\s]+$',

        # Identifiers
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'ssn': r'^\d{3}-\d{2}-\d{4}$',
        'credit_card': r'^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$',

        # Addresses
        'ip_address': r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$',
        'ipv6_address': r'^([0-9a-fA-F]{0,4}:){7}[0-9a-fA-F]{0,4}$',
        'mac_address': r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        'zip_code_us': r'^\d{5}(-\d{4})?$',
        'postal_code_ca': r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$',

        # Financial
        'currency_usd': r'^\$\d{1,3}(,\d{3})*(\.\d{2})?$',
        'currency_eur': r'^€\d{1,3}(,\d{3})*(\.\d{2})?$',
        'iban': r'^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$',

        # Dates and times
        'date_iso': r'^\d{4}-\d{2}-\d{2}$',
        'date_us': r'^\d{1,2}/\d{1,2}/\d{4}$',
        'time_24h': r'^([01]\d|2[0-3]):([0-5]\d)(:([0-5]\d))?$',
        'timestamp_iso': r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',

        # File paths
        'file_path_unix': r'^/[^\s]*$',
        'file_path_windows': r'^[A-Za-z]:\\[^\s]*$',

        # Codes
        'hex_color': r'^#[0-9A-Fa-f]{6}$',
        'base64': r'^[A-Za-z0-9+/]+={0,2}$',

        # Social media
        'twitter_handle': r'^@[A-Za-z0-9_]{1,15}$',
        'hashtag': r'^#[A-Za-z0-9_]+$',
    }

    MIN_CONFIDENCE = 70.0  # Minimum confidence to report pattern
    MAX_EXAMPLES = 5  # Maximum examples to return

    def detect_patterns(
        self,
        values: np.ndarray,
        min_confidence: float = 70.0,
        custom_patterns: dict[str, str] | None = None
    ) -> list[PatternMatch]:
        """
        Detect patterns in string values.

        Args:
            values: Array of string values (may contain NaN)
            min_confidence: Minimum confidence threshold (0-100)
            custom_patterns: Optional dict of {name: regex} for custom patterns

        Returns:
            List of PatternMatch objects sorted by confidence (desc)
        """
        # Remove NaN and empty strings
        valid_values = []
        for v in values:
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                val_str = str(v).strip()
                if val_str:
                    valid_values.append(val_str)

        if len(valid_values) == 0:
            return []

        # Combine built-in and custom patterns
        all_patterns = self.PATTERNS.copy()
        if custom_patterns:
            all_patterns.update(custom_patterns)

        # Test each pattern
        matches = []
        for pattern_type, pattern_regex in all_patterns.items():
            try:
                match = self._test_pattern(
                    pattern_type,
                    pattern_regex,
                    valid_values
                )

                if match and match.confidence >= min_confidence:
                    matches.append(match)

            except re.error:
                # Skip invalid regex patterns
                continue

        # Sort by confidence (descending)
        matches.sort(key=lambda m: m.confidence, reverse=True)

        return matches

    def _test_pattern(
        self,
        pattern_type: str,
        pattern_regex: str,
        values: list[str]
    ) -> PatternMatch | None:
        """
        Test a pattern against values.

        Args:
            pattern_type: Pattern name
            pattern_regex: Regular expression
            values: List of string values

        Returns:
            PatternMatch if pattern matches, None otherwise
        """
        compiled = re.compile(pattern_regex, re.IGNORECASE)

        match_count = 0
        examples = []

        for value in values:
            if compiled.match(value):
                match_count += 1

                # Collect examples
                if len(examples) < self.MAX_EXAMPLES:
                    examples.append(value)

        # Calculate confidence
        confidence = (match_count / len(values)) * 100

        if match_count > 0:
            return PatternMatch(
                pattern_type=pattern_type,
                pattern_regex=pattern_regex,
                match_count=match_count,
                total_count=len(values),
                confidence=confidence,
                examples=examples
            )

        return None

    def suggest_semantic_type(self, matches: list[PatternMatch]) -> str | None:
        """
        Suggest semantic type based on pattern matches.

        Args:
            matches: List of pattern matches

        Returns:
            Suggested semantic type name, or None
        """
        if not matches:
            return None

        # Get highest confidence match
        best_match = matches[0]

        # Map patterns to semantic types
        semantic_mapping = {
            'email': 'email_address',
            'phone_us': 'phone_number',
            'phone_intl': 'phone_number',
            'url': 'url',
            'uuid': 'identifier',
            'ssn': 'ssn',
            'credit_card': 'credit_card_number',
            'ip_address': 'ip_address',
            'ipv6_address': 'ip_address',
            'zip_code_us': 'postal_code',
            'postal_code_ca': 'postal_code',
            'date_iso': 'date',
            'date_us': 'date',
            'timestamp_iso': 'timestamp',
        }

        return semantic_mapping.get(best_match.pattern_type)

    def suggest_checks(self, matches: list[PatternMatch]) -> list[dict]:
        """
        Suggest validation checks based on detected patterns.

        Args:
            matches: List of pattern matches

        Returns:
            List of suggested check dictionaries
        """
        suggestions = []

        for match in matches:
            if match.confidence >= 90:
                # High confidence - suggest strict pattern matching
                suggestions.append({
                    'check': 'matches',
                    'pattern': match.pattern_regex,
                    'threshold': 0.95,
                    'reason': f'High confidence ({match.confidence:.1f}%) {match.pattern_type} pattern'
                })

            elif match.confidence >= 70:
                # Medium confidence - suggest lenient pattern matching
                suggestions.append({
                    'check': 'matches',
                    'pattern': match.pattern_regex,
                    'threshold': 0.80,
                    'reason': f'Moderate confidence ({match.confidence:.1f}%) {match.pattern_type} pattern'
                })

        return suggestions

    def validate_pattern(self, pattern_regex: str) -> tuple[bool, str | None]:
        """
        Validate a regex pattern.

        Args:
            pattern_regex: Regular expression to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            re.compile(pattern_regex)
            return True, None
        except re.error as e:
            return False, str(e)

    def get_pattern_category(self, pattern_type: str) -> str:
        """
        Get the category of a pattern type.

        Args:
            pattern_type: Pattern type name

        Returns:
            Category name
        """
        categories = {
            'Contact': ['email', 'phone_us', 'phone_intl', 'url'],
            'Identifier': ['uuid', 'ssn', 'credit_card'],
            'Address': ['ip_address', 'ipv6_address', 'mac_address', 'zip_code_us', 'postal_code_ca'],
            'Financial': ['currency_usd', 'currency_eur', 'iban'],
            'DateTime': ['date_iso', 'date_us', 'time_24h', 'timestamp_iso'],
            'File': ['file_path_unix', 'file_path_windows'],
            'Code': ['hex_color', 'base64'],
            'Social': ['twitter_handle', 'hashtag'],
        }

        for category, types in categories.items():
            if pattern_type in types:
                return category

        return 'Other'
