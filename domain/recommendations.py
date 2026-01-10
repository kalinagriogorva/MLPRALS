from typing import Dict, List, Any
from domain.scoring import level_label

def action_hint(category: str, concept: str, from_level: int, to_level: int) -> str:
    generic = {
        1: "Move from ad-hoc/manual to basic documented and digital practice.",
        2: "Standardize: define ownership, rules, and a repeatable routine.",
        3: "Automate and integrate into daily workflows (dashboards, checks, stable integrations).",
        4: "Scale and embed into governance: monitoring, feedback loops, continuous improvement.",
    }

    if category.startswith("1.") and concept in ["Data Consistency & Quality", "Data Integration", "Historical Data"]:
        generic[2] = "Define data standards and validation rules; standardize identifiers, formats, and required fields."
        generic[3] = "Add automated checks (outliers/missing), centralize datasets, and stabilize integrations."

    if category.startswith("6.") and concept in ["Access Control & Authentication", "Cybersecurity Measures", "Data Protection & Privacy"]:
        generic[2] = "Implement RBAC basics and enforce MFA; document and communicate security procedures."
        generic[3] = "Add logging/audit trails, monitoring, routine vulnerability checks, and an incident response playbook."

    if category.startswith("4.") and concept in ["Process Standardization", "Performance Monitoring", "Data-Driven Decisions"]:
        generic[2] = "Write short SOPs and define KPIs; review them on a fixed cadence."
        generic[3] = "Embed dashboards/alerts into daily work; assign owners and escalation routines."

    return generic.get(from_level, f"Improve from Level {from_level} toward Level {to_level} with structured steps.")

def advanced_recommendations(
    responses: Dict[str, Dict[str, int]],
    category_levels: Dict[str, int],
    minimums: Dict[str, int],
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}

    for cat, concepts in responses.items():
        Ri = category_levels[cat]
        target = minimums.get(cat, 3)
        gap = target - Ri

        if gap <= 0:
            out[cat] = {
                "status": f"✅ Meets minimum (current {level_label(Ri)} ≥ minimum {level_label(target)}).",
                "progress": 1.0,
                "items": [
                    "Stability should be maintained (avoid introducing new instability).",
                    "Monitoring and documentation can be strengthened to preserve consistency.",
                ],
            }
            continue

        weakest_sorted = sorted(concepts.items(), key=lambda x: x[1])
        weakest_names = [c for c, _ in weakest_sorted[:2]]

        items: List[str] = []
        items.append(f"**Gap to minimum:** current {level_label(Ri)} → minimum {level_label(target)} (needs +{gap}).")
        items.append(f"**Priority concepts:** {', '.join(weakest_names)} (largest contributors to the gap).")

        for concept, lvl in weakest_sorted:
            if lvl >= target:
                continue
            steps = []
            for step_from in range(lvl, target):
                step_to = step_from + 1
                steps.append(f"{step_from} → {step_to}: {action_hint(cat, concept, step_from, step_to)}")
            items.append(f"**{concept} (currently Level {lvl})**\n- " + "\n- ".join(steps))

        out[cat] = {
            "status": f"⚠️ Below minimum (current {level_label(Ri)} < minimum {level_label(target)}).",
            "progress": max(0.0, min(1.0, Ri / target)) if target > 0 else 0.0,
            "items": items,
        }

    return out
