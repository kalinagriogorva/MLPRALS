from __future__ import annotations

from typing import Dict, Any, List

import streamlit as st

from infrastructure.session_repository import SessionRepository

from ui.pages.eligibility import render_eligibility_page
from ui.pages.questionnaire import render_questionnaire_page
from ui.pages.results import render_results_page


def run_app_flow(
    session: SessionRepository,
    question_bank: Dict[str, List[Dict[str, Any]]],
    minimum_levels: Dict[str, int],
) -> None:
    """
    UI-level application flow (router).
    - Gate checks (Eligibility page)
    - Questionnaire page
    - Results page
    """
    # Gate 1 + Gate 2 will st.stop() until satisfied
    render_eligibility_page(session, question_bank)


    # After gates, show main app tabs
    tabs = st.tabs(["📝 Questionnaire", "📊 Results"])

    with tabs[0]:
        q_out = render_questionnaire_page(
            session=session,
            question_bank=question_bank,
            minimum_levels=minimum_levels,
        )

        # Persist latest questionnaire output for cross-tab usage
        ss = session.as_dict()
        ss["__latest_company_name"] = q_out.get("company_name", "")
        ss["__latest_responses_raw"] = q_out.get("responses_raw", {})
        ss["__latest_missing"] = q_out.get("missing", [])

    with tabs[1]:
        ss = session.as_dict()

        # Pull the latest output (if the user opened Results tab first)
        responses_raw = ss.get("__latest_responses_raw", {})
        missing = ss.get("__latest_missing", [])

        # If not available yet, show a gentle hint
        if not responses_raw:
            st.info("Go to the **Questionnaire** tab first to load the current response set.")
            return

        render_results_page(
            responses_raw=responses_raw,
            missing=missing,
            minimum_levels=minimum_levels,
        )
