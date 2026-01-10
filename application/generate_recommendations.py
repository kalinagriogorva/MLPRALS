from typing import Dict, Any
from domain.recommendations import advanced_recommendations

def generate_recommendations(
    responses: Dict[str, Dict[str, int]],
    category_levels: Dict[str, int],
    minimum_levels: Dict[str, int],
) -> Dict[str, Dict[str, Any]]:
    """
    Application wrapper for the recommendation engine.
    Keeps UI free from domain details.
    """
    return advanced_recommendations(responses, category_levels, minimum_levels)
