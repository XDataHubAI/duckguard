"""AI-powered data quality features for DuckGuard.

This module provides LLM-powered data quality capabilities:
- explain: Natural language data quality summaries
- suggest: AI-generated validation rules
- fix: AI-suggested data cleaning steps
- natural_rules: Plain English validation rules

Requires: pip install duckguard[llm]

Example:
    from duckguard import connect
    from duckguard.ai import explain, suggest_rules

    orders = connect("orders.csv")
    print(explain(orders))
    rules = suggest_rules(orders)
"""

from duckguard.ai.config import configure, get_config
from duckguard.ai.explainer import explain
from duckguard.ai.fixer import suggest_fixes
from duckguard.ai.natural_language import natural_rules
from duckguard.ai.rules_generator import suggest_rules

__all__ = [
    "configure",
    "get_config",
    "explain",
    "suggest_rules",
    "suggest_fixes",
    "natural_rules",
]
