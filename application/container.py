from __future__ import annotations

from typing import Dict, List, Any

from data.question_bank import QUESTION_BANK
from config.thresholds import MINIMUM_LEVELS


def get_question_bank() -> Dict[str, List[Dict[str, Any]]]:
    # Returned as-is (static data)
    return QUESTION_BANK


def get_minimum_levels() -> Dict[str, int]:
    # Returned as-is (static config)
    return MINIMUM_LEVELS
