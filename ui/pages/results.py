from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from application.evaluate_assessment import evaluate_assessment
from application.generate_recommendations import generate_recommendations
from domain.scoring import readiness_badge, level_label
from ui.components.progress import render_progress


def _cast_responses(responses_raw: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """
    Converts {dim: {concept: Optional[int]}} -> {dim: {concept: int}}
    Assumes caller already validated that no None exists.
    """
    out: Dict[str, Dict[str, int]] = {}
    for dim, concepts in responses_raw.items():
        out[dim] = {}
        for concept, val in concepts.items():
            out[dim][concept] = int(val)
    return out


def _dim_sort_key(d: str) -> str:
    # "1. Data Readiness" sorts before "2. ..."
    return d.split(" ", 1)[0]


def render_results_page(
    responses_raw: Dict[str, Dict[str, Any]],
    missing: List[str],
    minimum_levels: Dict[str, int],
) -> None:
    st.header("Results")

    # -----------------------------
    # Block results if missing items exist
    # -----------------------------
    if missing:
        st.error("Results are not available yet — some questions are still unanswered or invalid.")
        with st.expander("Show missing items"):
            for m in missing:
                st.write(f"- {m}")
        st.info("Go back to the questionnaire and complete the missing items.")
        return

    responses = _cast_responses(responses_raw)

    # -----------------------------
    # Compute results (use-cases)
    # -----------------------------
    eval_out = evaluate_assessment(responses=responses, minimum_levels=minimum_levels)
    category_levels: Dict[str, int] = eval_out["category_levels"]

    recs = generate_recommendations(
        responses=responses,
        category_levels=category_levels,
        minimum_levels=minimum_levels,
    )

    # -----------------------------
    # Top-level metrics
    # -----------------------------
    c1, c2, c3, c4 = st.columns(4)
    overall_level = int(eval_out["overall_level"])
    nmrs = float(eval_out["nmrs"])
    ml_ready = bool(eval_out["ml_ready"])
    meets_minimums = bool(eval_out["meets_minimums"])

    c1.metric("Overall level", f"{overall_level} ({readiness_badge(overall_level)})")
    c2.metric("NMRS score (0–1)", f"{nmrs:.3f}")
    c3.metric("ML-ready (rule)", "YES ✅" if ml_ready else "NO ❌")
    c4.metric("Meets minimum levels", "YES ✅" if meets_minimums else "NO ❌")

    st.divider()

    # -----------------------------
    # Quick interpretation
    # -----------------------------
    if ml_ready and meets_minimums:
        st.success("✅ Your organization meets the framework readiness thresholds and passes the ML-ready rule.")
    elif meets_minimums and not ml_ready:
        st.warning(
            "⚠️ You meet the minimum levels, but the ML-ready rule is not fully satisfied "
            "(usually due to Data Readiness needing Level 4+)."
        )
    else:
        st.error("❌ You are below the minimum readiness levels in one or more dimensions.")

    st.divider()

    # -----------------------------
    # Dimension summary
    # -----------------------------
    st.subheader("Dimension summary")

    rows: List[Dict[str, Any]] = []
    for dim, lvl in category_levels.items():
        min_lvl = minimum_levels.get(dim, 3)
        ok = lvl >= min_lvl
        rows.append(
            {
                "Dimension": dim,
                "Level": lvl,
                "Label": readiness_badge(lvl),
                "Minimum": min_lvl,
                "Meets minimum?": "✅" if ok else "❌",
            }
        )

    rows = sorted(rows, key=lambda r: _dim_sort_key(r["Dimension"]))
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.divider()

    # -----------------------------
    # Recommendations
    # -----------------------------
    st.subheader("Recommendations (how to close gaps)")
    st.caption(
        "These are dimension-specific improvement steps. Focus first on dimensions that are below minimum "
        "and within those, the lowest concepts."
    )

    for dim in sorted(recs.keys(), key=_dim_sort_key):
        block = recs[dim]
        status = str(block.get("status", ""))
        progress_0_1 = float(block.get("progress", 0.0))
        items = block.get("items", [])

        current_lvl = category_levels.get(dim, 1)
        min_lvl = minimum_levels.get(dim, 3)

        with st.expander(f"{dim} — {level_label(current_lvl)} (min {min_lvl})", expanded=False):

            # 1) Status message FULL width (not inside columns)
           # Status full width
            if status:
                if "✅" in status:
                    st.success(status)
                elif "⚠️" in status:
                    st.warning(status)
                else:
                    st.info(status)

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            left, right = st.columns([3, 2], vertical_alignment="top")

            with left:
                for item in items:
                    st.markdown(item)

            with right:
                pct = round(max(0.0, min(1.0, progress_0_1)) * 100)

                st.markdown(
                    "<div style='display:flex; justify-content:center; align-items:center; height:100%;'>",
                    unsafe_allow_html=True,
                )
                render_progress(percent=pct)
                st.markdown("</div>", unsafe_allow_html=True)

            st.divider()

