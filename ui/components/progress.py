import streamlit as st

def render_progress(
    completed: int | None = None,
    total: int | None = None,
    *,
    percent: int | None = None,
    label_left: str | None = None,
    label_right: str | None = None,
    show_percent_label: bool = True,
) -> None:
    """
    Reusable purple progress bar.
    Use either:
      - completed + total
    OR
      - percent (0-100)

    Labels are optional.
    """
    if percent is None:
        total = max(int(total or 0), 0)
        completed = max(min(int(completed or 0), total), 0)
        percent = 0 if total == 0 else round((completed / total) * 100)
    else:
        percent = max(0, min(100, int(percent)))

    # Label row
    if label_left or label_right:
        left, right = st.columns([3, 1])
        with left:
            if label_left:
                st.markdown(f"**{label_left}**")
        with right:
            if label_right:
                st.markdown(f"<div class='mlprals-progress-pct'>{label_right}</div>", unsafe_allow_html=True)
            elif show_percent_label:
                st.markdown(f"<div class='mlprals-progress-pct'>{percent}%</div>", unsafe_allow_html=True)
    else:
        if show_percent_label:
            st.markdown(f"<div class='mlprals-progress-pct'>{percent}%</div>", unsafe_allow_html=True)

    # Bar
    st.markdown(
        f"""
        <div class="mlprals-progress-wrap" role="progressbar" aria-valuenow="{percent}" aria-valuemin="0" aria-valuemax="100">
          <div class="mlprals-progress-track">
            <div class="mlprals-progress-fill" style="width:{percent}%"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
