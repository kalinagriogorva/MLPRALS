from __future__ import annotations

from typing import Dict, Any, List

from infrastructure.session_repository import SessionRepository
from ui.layout import apply_layout, close_layout
from ui.pages.app_flow import run_app_flow


def run_ui(
    question_bank: Dict[str, List[Dict[str, Any]]],
    minimum_levels: Dict[str, int],
) -> None:
    """
    Single entrypoint for the UI.
    app.py will eventually call this and become tiny.
    """
    session = SessionRepository()

    apply_layout()

    try:
        run_app_flow(
            session=session,
            question_bank=question_bank,
            minimum_levels=minimum_levels,
        )
    finally:
        close_layout()
