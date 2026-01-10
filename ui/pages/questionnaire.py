from __future__ import annotations

from typing import Dict, Any, Optional, List

import streamlit as st

from ui.components.progress import render_progress
from infrastructure.session_repository import SessionRepository
from infrastructure.csv_repository import build_export_df_partial
from utils.keys import (
    get_qkey,
    get_override_key,
    get_override_level_key,
    get_help_key,
    get_none_key,
)
from domain.scoring import compute_suggested_level, readiness_badge, level_label


def _to_bool(x: Any) -> bool:
    """Normalize session values into a real bool (handles True/False, 1/0, 'true'/'false')."""
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    if isinstance(x, (int, float)):
        try:
            return bool(int(x))
        except Exception:
            return False
    s = str(x).strip().lower()
    return s in {"true", "1", "yes", "y", "on"}


def _rehydrate_checkboxes_from_level(ss: dict, dim: str, concept: str, level: int) -> None:
    """
    Fallback UI-only mapping:
    if a final level exists but no checkbox states exist, generate a consistent pattern.
    """
    # Reset all
    ss[get_help_key(dim, concept, "a")] = False
    ss[get_help_key(dim, concept, "b")] = False
    ss[get_help_key(dim, concept, "c")] = False
    ss[get_help_key(dim, concept, "rt")] = False
    ss[get_none_key(dim, concept)] = False

    if level == 1:
        ss[get_none_key(dim, concept)] = True
        return

    ss[get_help_key(dim, concept, "a")] = True
    if level >= 3:
        ss[get_help_key(dim, concept, "b")] = True
    if level >= 4:
        ss[get_help_key(dim, concept, "c")] = True
    if level >= 5:
        ss[get_help_key(dim, concept, "rt")] = True


def render_questionnaire_page(
    session: SessionRepository,
    question_bank: Dict[str, List[Dict[str, Any]]],
    minimum_levels: Dict[str, int],
) -> Dict[str, Any]:
    ss = session.as_dict()

    # One-time rerun after import so widgets rebuild cleanly
    if ss.pop("force_questionnaire_reload", False):
        st.rerun()

    # =========================
    # Company info
    # =========================
    st.header("Questionnaire")

    with st.container(border=False):
        st.subheader("Company information")
        default_company = ss.get("company_name_loaded", "")
        company_name = st.text_input("Company name", value=default_company)
        ss["company_name_loaded"] = company_name

    st.divider()

    # =========================
    # Reset helper
    # =========================
    def reset_all_state() -> None:
        for dim, questions in question_bank.items():
            for q in questions:
                concept = q["concept"]
                keys_to_clear = [
                    get_qkey(dim, concept),
                    get_override_key(dim, concept),
                    get_override_level_key(dim, concept),
                    get_help_key(dim, concept, "a"),
                    get_help_key(dim, concept, "b"),
                    get_help_key(dim, concept, "c"),
                    get_help_key(dim, concept, "rt"),
                    get_none_key(dim, concept),
                ]
                for k in keys_to_clear:
                    if k in ss:
                        del ss[k]

        for k in ["company_name_loaded", "auto_loaded_signature", "answers_uploader", "force_questionnaire_reload"]:
            if k in ss:
                del ss[k]

    with st.container(border=True):
        st.subheader("Reset answers (optional)")
        st.caption("Clears all answers, overrides, and imported state for the current session.")
        if st.button("Reset all answers", key="reset_all_btn"):
            reset_all_state()
            st.success("All answers cleared.")
            st.rerun()

    st.divider()

    # =========================
    # Progress bar
    # =========================
    total_questions = sum(len(v) for v in question_bank.values())

    def is_valid_answer(dim: str, concept: str) -> bool:
        key = get_qkey(dim, concept)
        val = ss.get(key, None)
        return isinstance(val, int) and val in [1, 2, 3, 4, 5]

    completed = sum(
        1
        for dim, questions in question_bank.items()
        for q in questions
        if is_valid_answer(dim, q["concept"])
    )

    render_progress(
        completed=completed,
        total=total_questions,
        label_left=f"Progress: {completed}/{total_questions} answered",
        label_right=None,
    )

    st.divider()

    # =========================
    # Export (ALWAYS available — even partial)
    # =========================
    st.subheader("Export answers (available anytime)")
    st.caption(
        "Download your current progress at any point. Unanswered questions are exported as blank.\n"
        "You can later import this file again (partial import supported)."
    )

    export_anytime_df = build_export_df_partial(
        question_bank=question_bank,
        minimum_levels=minimum_levels,
        session_state=ss,
        company=company_name,
        qkey_builder=get_qkey,
        help_key_builder=get_help_key,
        none_key_builder=get_none_key,
        override_key_builder=get_override_key,
        override_level_key_builder=get_override_level_key,
    )

    st.download_button(
        "Download answers as CSV",
        data=export_anytime_df.to_csv(index=False).encode("utf-8"),
        file_name=f"mlprals_answers_{company_name or 'company'}.csv",
        mime="text/csv",
    )

    with st.expander("Preview export (first 20 rows)"):
        st.dataframe(export_anytime_df.head(20), use_container_width=True, hide_index=True)

    st.divider()

    # =========================
    # Questions section
    # =========================
    st.subheader("Questions")
    st.info(
        "Checklist selection determines a level.\n"
        "- If nothing is selected, the answer is invalid.\n"
        "- If **None of the above** is selected, the result is **Level 1**.\n"
        "- Otherwise, the result is calculated automatically (Level 2–5)."
    )

    responses_raw: Dict[str, Dict[str, Optional[int]]] = {}
    missing: List[str] = []

    for dim, questions in question_bank.items():
        with st.expander(dim, expanded=False):
            responses_raw[dim] = {}

            for q in questions:
                concept = q["concept"]
                prompt = q["question"]
                levels = q["levels"]
                checks = q["checks"]

                qkey = get_qkey(dim, concept)
                override_key = get_override_key(dim, concept)
                override_level_key = get_override_level_key(dim, concept)

                st.markdown(f"### {concept}")

                head_l, head_r = st.columns([10, 2])
                with head_l:
                    st.write(prompt)
                with head_r:
                    with st.popover("👁 Level guide", use_container_width=True):
                        st.markdown("**Level definitions:**")
                        for lvl in [1, 2, 3, 4, 5]:
                            st.markdown(f"- **Level {lvl}:** {levels[lvl]}")

                st.markdown("**Checklist:**")
                c1, c2 = st.columns([2, 1])

                # ---- Normalize checkbox state in session BEFORE rendering widgets ----
                a_key = get_help_key(dim, concept, "a")
                b_key = get_help_key(dim, concept, "b")
                c_key = get_help_key(dim, concept, "c")
                rt_key = get_help_key(dim, concept, "rt")
                none_key = get_none_key(dim, concept)

                # Force any non-bool into real bools
                if a_key in ss:
                    ss[a_key] = _to_bool(ss[a_key])
                if b_key in ss:
                    ss[b_key] = _to_bool(ss[b_key])
                if c_key in ss:
                    ss[c_key] = _to_bool(ss[c_key])
                if rt_key in ss:
                    ss[rt_key] = _to_bool(ss[rt_key])
                if none_key in ss:
                    ss[none_key] = _to_bool(ss[none_key])

                # ✅ Rehydrate ONLY if no checkbox state exists (fallback for old CSVs)
                existing_level = ss.get(qkey, None)
                has_any_checkbox = (
                    _to_bool(ss.get(a_key))
                    or _to_bool(ss.get(b_key))
                    or _to_bool(ss.get(c_key))
                    or _to_bool(ss.get(rt_key))
                    or _to_bool(ss.get(none_key))
                )

                if isinstance(existing_level, int) and existing_level in [1, 2, 3, 4, 5] and not has_any_checkbox:
                    _rehydrate_checkboxes_from_level(ss, dim, concept, int(existing_level))

                with c1:
                    a = st.checkbox(checks["a"], key=a_key)
                    b = st.checkbox(checks["b"], key=b_key)
                    c = st.checkbox(checks["c"], key=c_key)
                    rt = st.checkbox(checks["rt"], key=rt_key)
                    none = st.checkbox("None of the above", key=none_key)

                    if none and (a or b or c or rt):
                        st.warning("Invalid selection: choose either checklist items OR **None of the above** (not both).")

                any_selected = bool(none or a or b or c or rt)
                contradictory = bool(none and (a or b or c or rt))
                is_overriding = bool(ss.get(override_key, False))

                # Automatic scoring when not overriding
                if not is_overriding:
                    if none and not (a or b or c or rt):
                        ss[qkey] = 1
                    elif (a or b or c or rt) and not none:
                        ss[qkey] = compute_suggested_level(a, b, c, rt)
                    else:
                        if qkey in ss:
                            del ss[qkey]

                with c2:
                    st.markdown("**Current level:**")
                    current_val = ss.get(qkey, None)
                    if isinstance(current_val, int) and current_val in [1, 2, 3, 4, 5]:
                        st.metric("Level", f"{current_val} ({readiness_badge(current_val)})")
                    else:
                        st.metric("Level", "—")

                    if st.button("Change this level", key=f"enable_override::{dim}::{concept}", use_container_width=True):
                        ss[override_key] = True
                        cur = ss.get(qkey, None)
                        ss[override_level_key] = int(cur if isinstance(cur, int) and cur in [1, 2, 3, 4, 5] else 2)

                # Manual override UI
                if ss.get(override_key, False):
                    chosen = st.radio(
                        "Override level (use when automatic level is not correct):",
                        options=[1, 2, 3, 4, 5],
                        key=override_level_key,
                        horizontal=True,
                    )
                    ss[qkey] = int(chosen)

                    if st.button("Use automatic level again", key=f"disable_override::{dim}::{concept}"):
                        ss[override_key] = False
                        if override_level_key in ss:
                            del ss[override_level_key]
                        st.rerun()

                final_level = ss.get(qkey, None)

                if (
                    isinstance(final_level, int)
                    and final_level in [1, 2, 3, 4, 5]
                    and (is_overriding or (any_selected and not contradictory))
                ):
                    st.success(f"Selected: {level_label(final_level)}")
                    responses_raw[dim][concept] = int(final_level)
                else:
                    responses_raw[dim][concept] = None
                    if not any_selected:
                        st.warning("Selection required: choose at least one checkbox (or **None of the above**).")
                    elif contradictory:
                        st.warning("Selection required: resolve the contradictory selection.")
                    else:
                        st.warning("Selection required: choose at least one checkbox (or **None of the above**).")

                st.divider()

    for dim, concepts in responses_raw.items():
        for concept, val in concepts.items():
            if val is None:
                missing.append(f"{dim} → {concept}")

    return {
        "company_name": company_name,
        "responses_raw": responses_raw,
        "missing": missing,
    }
