from typing import Dict, Any
from domain.scoring import floor_avg, normalize_level, overall_level_from_nmrs

def evaluate_assessment(
    responses: Dict[str, Dict[str, int]],
    minimum_levels: Dict[str, int],
) -> Dict[str, Any]:
    """
    Pure orchestration.
    Inputs:
      - responses: {dimension: {concept: level}}
      - minimum_levels: {dimension: min_level}
    Outputs:
      - computed scores + flags + per-dimension levels
    """

    category_levels: Dict[str, int] = {}
    category_normalized: Dict[str, float] = {}

    for dim, concept_levels in responses.items():
        lvls = list(concept_levels.values())
        Ri = floor_avg(lvls)
        category_levels[dim] = Ri
        category_normalized[dim] = normalize_level(Ri)

    nmrs = sum(category_normalized.values()) / len(category_normalized) if category_normalized else 0.0
    overall_level = overall_level_from_nmrs(nmrs)

    data_ok = category_levels.get("1. Data Readiness", 1) >= 4
    all_ok = all(lvl >= 3 for lvl in category_levels.values()) if category_levels else False
    ml_ready = data_ok and all_ok

    meets_minimums = all(
        category_levels.get(dim, 0) >= minimum_levels.get(dim, 0)
        for dim in minimum_levels.keys()
    )

    return {
        "nmrs": nmrs,
        "overall_level": overall_level,
        "ml_ready": ml_ready,
        "meets_minimums": meets_minimums,
        "category_levels": category_levels,
        "category_normalized": category_normalized,
    }
