import base64
from pathlib import Path
import streamlit as st

from config.ui_config import APP_TITLE, APP_LAYOUT, LOGO_PATH

def _img_to_base64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")

def apply_layout():
    st.set_page_config(page_title=APP_TITLE, layout=APP_LAYOUT)

    css_path = Path("ui/styles.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

    logo_b64 = _img_to_base64(LOGO_PATH)
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="Logo" />'
        if logo_b64
        else '<div style="color:white;font-weight:800;padding:18px;">LOGO</div>'
    )

    st.markdown(
        f"""
        <div class="mlprals-header">
          <div class="mlprals-header-inner">
            <div class="mlprals-logo">{logo_html}</div>
            <div class="mlprals-title">
              <h1>MLPRALS Readiness Assessment</h1>
              <p>Assessment for SMEs to evaluate readiness for Machine Learning (ML) adoption.</p>
            </div>
          </div>
        </div>
        <div class="mlprals-content">
        """,
        unsafe_allow_html=True,
    )

def close_layout():
    st.markdown("</div>", unsafe_allow_html=True)
