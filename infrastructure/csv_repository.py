from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

def build_export_df_partial(
    *,
    question_bank: Dict[str, List[Dict[str, Any]]],
    minimum_levels: Dict[str, int],
    session_state: Dict[str, Any],
    company: str,
    qkey_builder,
    help_key_builder,
    none_key_builder,
    override_key_builder,
    override_level_key_builder,
) -> pd.DataFrame:
    """
    Export EVERYTHING that is answered:
    - Global fields repeated per row (company + eligibility/sector)
    - Checkbox states (a/b/c/rt/none)
    - Override flags
    - Final computed/selected level (what matters for scoring)
    """

    # Global fields (repeat on each row)
    global_fields = {
    "Company": company or session_state.get("company_name_loaded", "") or "",

    "Employees": session_state.get("elig_employees", ""),
    "Turnover (€mill)": session_state.get("elig_turnover_m", ""),
    "Balance sheet (€mill)": session_state.get("elig_balance_m", ""),

    "Eligibility confirmed": bool(session_state.get("eligibility_confirmed", False)),
    "Is SME": session_state.get("is_sme", ""),
    "Allow continue non-SME": bool(session_state.get("allow_continue_non_sme", False)),
    "Sector confirmed": bool(session_state.get("sector_confirmed", False)),
    "Is logistics": session_state.get("is_logistics", ""),
    "Allow continue non-logistics": bool(session_state.get("allow_continue_non_logistics", False)),
    }


    rows = []

    for dim, questions in question_bank.items():
        # Dimension level only if all final levels are present
        final_levels: List[Optional[int]] = []
        for q in questions:
            concept = q["concept"]
            qkey = qkey_builder(dim, concept)
            val = session_state.get(qkey, None)
            lvl = int(val) if isinstance(val, int) and val in [1, 2, 3, 4, 5] else None
            final_levels.append(lvl)

        dim_level = ""
        if all(v is not None for v in final_levels) and final_levels:
            dim_level = int(sum(final_levels) // len(final_levels))

        for q in questions:
            concept = q["concept"]

            # Final level stored in session
            qkey = qkey_builder(dim, concept)
            final_val = session_state.get(qkey, None)
            final_level = int(final_val) if isinstance(final_val, int) and final_val in [1, 2, 3, 4, 5] else ""

            # Checkbox states
            a = bool(session_state.get(help_key_builder(dim, concept, "a"), False))
            b = bool(session_state.get(help_key_builder(dim, concept, "b"), False))
            c = bool(session_state.get(help_key_builder(dim, concept, "c"), False))
            rt = bool(session_state.get(help_key_builder(dim, concept, "rt"), False))
            none = bool(session_state.get(none_key_builder(dim, concept), False))

            # Override state
            override_enabled = bool(session_state.get(override_key_builder(dim, concept), False))
            ov_val = session_state.get(override_level_key_builder(dim, concept), None)
            override_level = int(ov_val) if isinstance(ov_val, int) and ov_val in [1, 2, 3, 4, 5] else ""

            rows.append({
                **global_fields,

                "Dimension": dim,
                "Concept": concept,
                "Question": q.get("question", ""),

                # Checkboxes (raw inputs)
                "Check A": a,
                "Check B": b,
                "Check C": c,
                "Real-time": rt,
                "None of the above": none,

                # Override info
                "Override enabled": override_enabled,
                "Override level": override_level,

                # Final scoring
                "Final level": final_level,
                "Dimension level": dim_level,
                "Minimum level": minimum_levels.get(dim, ""),
            })

    return pd.DataFrame(rows)


from typing import Dict, List, Any, Optional, Tuple
import pandas as pd


def auto_load_answers_from_csv(
    *,
    question_bank: Dict[str, List[Dict[str, Any]]],
    session_state: Dict[str, Any],
    df: pd.DataFrame,
    qkey_builder,
    override_key_builder,
    override_level_key_builder,
    help_key_builder=None,
    none_key_builder=None,
) -> Tuple[int, Optional[str]]:
    """
    Loads answers from a CSV into session_state.

    Supports BOTH formats:
      - Old format: "Selected level"
      - New format: checkbox columns + override columns + "Final level"
      - Also loads GLOBAL fields (company + eligibility + sector) from row 0 if present.

    Returns: (loaded_count, company_name_if_found)
    """

    # -----------------------------
    # Helpers
    # -----------------------------
    def _to_bool(x) -> bool:
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

    def _to_optional_bool(x):
        if x is None:
            return None
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return None
        if s.lower() in {"true", "1", "yes", "y", "on"}:
            return True
        if s.lower() in {"false", "0", "no", "n", "off"}:
            return False
        return None

    def _to_int_or_none(x):
        try:
            v = int(float(x))
            return v
        except Exception:
            return None

    def _to_float_or_none(x):
        try:
            return float(x)
        except Exception:
            return None

    # -----------------------------
    # Validate required columns
    # -----------------------------
    required_cols = {"Dimension", "Concept"}
    if not required_cols.issubset(set(df.columns)):
        missing = ", ".join(sorted(required_cols - set(df.columns)))
        raise ValueError(f"Missing required columns: {missing}")

    # Identify what level column exists
    level_col = None
    if "Final level" in df.columns:
        level_col = "Final level"
    elif "Selected level" in df.columns:
        level_col = "Selected level"

    # Optional columns (new export)
    has_checkbox_cols = all(
        c in df.columns for c in ["Check A", "Check B", "Check C", "Real-time", "None of the above"]
    )
    has_override_cols = all(c in df.columns for c in ["Override enabled", "Override level"])

    # -----------------------------
    # Load GLOBAL fields (from first row)
    # -----------------------------
    company_name = None
    if len(df) > 0:
        first = df.iloc[0]

        # Company
        if "Company" in df.columns:
            cname = str(first.get("Company", "")).strip()
            if cname and cname.lower() != "nan":
                company_name = cname
                session_state["company_name_loaded"] = cname

        # Eligibility numeric inputs (if you added these to export)
        if "Employees" in df.columns:
            v = _to_int_or_none(first.get("Employees", None))
            if v is not None:
                session_state["elig_employees"] = v

        if "Turnover (€mill)" in df.columns:
            v = _to_float_or_none(first.get("Turnover (€mill)", None))
            if v is not None:
                session_state["elig_turnover_m"] = v

        if "Balance sheet (€mill)" in df.columns:
            v = _to_float_or_none(first.get("Balance sheet (€mill)", None))
            if v is not None:
                session_state["elig_balance_m"] = v

        # Eligibility flags
        if "Eligibility confirmed" in df.columns:
            session_state["eligibility_confirmed"] = _to_bool(first.get("Eligibility confirmed", False))

        if "Is SME" in df.columns:
            session_state["is_sme"] = _to_optional_bool(first.get("Is SME", None))

        if "Allow continue non-SME" in df.columns:
            session_state["allow_continue_non_sme"] = _to_bool(first.get("Allow continue non-SME", False))

        # Sector flags
        if "Sector confirmed" in df.columns:
            session_state["sector_confirmed"] = _to_bool(first.get("Sector confirmed", False))

        if "Is logistics" in df.columns:
            session_state["is_logistics"] = _to_optional_bool(first.get("Is logistics", None))

        if "Allow continue non-logistics" in df.columns:
            session_state["allow_continue_non_logistics"] = _to_bool(
                first.get("Allow continue non-logistics", False)
            )

    # -----------------------------
    # Load per-question fields
    # -----------------------------
    loaded = 0

    for _, row in df.iterrows():
        dim = str(row["Dimension"]).strip()
        concept = str(row["Concept"]).strip()

        if dim not in question_bank:
            continue

        concept_set = {qq["concept"] for qq in question_bank[dim]}
        if concept not in concept_set:
            continue

        # 1) Load checkbox states if present AND key builders provided
        if has_checkbox_cols and help_key_builder and none_key_builder:
            session_state[help_key_builder(dim, concept, "a")] = _to_bool(row.get("Check A", False))
            session_state[help_key_builder(dim, concept, "b")] = _to_bool(row.get("Check B", False))
            session_state[help_key_builder(dim, concept, "c")] = _to_bool(row.get("Check C", False))
            session_state[help_key_builder(dim, concept, "rt")] = _to_bool(row.get("Real-time", False))
            session_state[none_key_builder(dim, concept)] = _to_bool(row.get("None of the above", False))

        # 2) Load override state if present
        if has_override_cols:
            ov_enabled = _to_bool(row.get("Override enabled", False))
            session_state[override_key_builder(dim, concept)] = ov_enabled

            ov_lvl = _to_int_or_none(row.get("Override level", None))
            if ov_lvl in [1, 2, 3, 4, 5]:
                session_state[override_level_key_builder(dim, concept)] = ov_lvl

        # 3) Load final/selected level if present
        lvl = None
        if level_col:
            lvl = _to_int_or_none(row.get(level_col, None))

        if lvl in [1, 2, 3, 4, 5]:
            session_state[qkey_builder(dim, concept)] = lvl
            loaded += 1
        elif has_checkbox_cols and help_key_builder and none_key_builder:
            # If no level column, but we did load checkbox states, still count it as loaded for feedback
            loaded += 1

    return loaded, company_name

