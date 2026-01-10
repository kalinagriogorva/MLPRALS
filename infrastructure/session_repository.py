from typing import Any, Dict
import streamlit as st


class SessionRepository:
    """
    Streamlit session adapter.
    Keeps Streamlit dependency outside domain/application.
    """

    def as_dict(self) -> Dict[str, Any]:
        # Return the live Streamlit session state (not a copy)
        return st.session_state

    def get(self, key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        st.session_state[key] = value

    def delete(self, key: str) -> None:
        if key in st.session_state:
            del st.session_state[key]

    def has(self, key: str) -> bool:
        return key in st.session_state

    def clear_many(self, keys) -> None:
        for k in keys:
            self.delete(k)
