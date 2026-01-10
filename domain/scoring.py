import math
from typing import List


def floor_avg(levels: List[int]) -> int:
    return int(math.floor(sum(levels) / len(levels)))


def normalize_level(level: int) -> float:
    # Converts 1–5 → 0–1
    return (level - 1) / 4.0


def overall_level_from_nmrs(nmrs: float) -> int:
    return 1 + int(math.floor(4 * nmrs + 1e-9))


def readiness_badge(level: int) -> str:
    return {
        1: "Very low",
        2: "Low",
        3: "Medium",
        4: "High",
        5: "Very high",
    }[level]


def level_label(level: int) -> str:
    return f"Level {level} – {readiness_badge(level)}"


def suggest_level(a: bool, b: bool, c: bool) -> int:
    score = sum([a, b, c])

    if score == 0:
        return 1
    if score == 1:
        return 2
    if score == 2:
        return 3
    return 4


def maybe_level_5(real_time: bool, base: int) -> int:
    return 5 if real_time and base >= 4 else base


def compute_suggested_level(a: bool, b: bool, c: bool, rt: bool) -> int:
    base = suggest_level(a, b, c)
    return maybe_level_5(rt, base)
