"""PharmaGuard: educational medication interaction information assistant."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import auth
import database
from faiss_engine import DrugInteractionSearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="PharmaGuard", page_icon="🩺", layout="wide")

st.markdown(
    """
    <div style="background:#fff3cd;border:2px solid #d39e00;border-radius:8px;
                padding:14px 18px;color:#4a3900;font-weight:600;margin-bottom:16px">
      ⚠️ MEDICAL DISCLAIMER — PharmaGuard is an educational/informational decision-support
      tool. It does not replace professional clinical advice, diagnosis, or treatment.
      Do not start, stop, or change medication based on this tool. Always consult a
      qualified clinician or pharmacist; seek emergency care for urgent symptoms.
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("🩺 PharmaGuard")
st.caption("Medical information assistant & medication interaction checker")


def _get_search_engine(records: list[dict[str, Any]]) -> DrugInteractionSearch:
    signature = tuple(
        (row.get("id"), row["drug1"].casefold(), row["drug2"].casefold()) for row in records
    )
    if st.session_state.get("faiss_signature") != signature:
        engine = DrugInteractionSearch(records)
        st.session_state["faiss_engine"] = engine
        st.session_state["faiss_signature"] = signature
    engine = st.session_state.get("faiss_engine")
    if not isinstance(engine, DrugInteractionSearch):
        raise RuntimeError("The medication search index could not be initialized.")
    return engine


def _get_google_identity() -> tuple[Any | None, bool]:
    """Read Streamlit's optional OIDC user without failing when auth is unconfigured."""
    user = getattr(st, "user", None)
    if user is None:
        user = getattr(st, "experimental_user", None)
    if user is None:
        return None, False
    try:
        logged_in = user.get("is_logged_in", False)
    except (AttributeError, KeyError, TypeError):
        logged_in = getattr(user, "is_logged_in", False)
    return user, bool(logged_in)


def _render_login() -> bool:
    user, google_logged_in = _get_google_identity()
    if google_logged_in and user is not None:
        email = str(user.get("email", "")).strip().casefold()
        if not email or not user.get("email_verified", False):
            st.error("Google did not provide a verified email address. Access is denied.")
            if st.button("Sign out"):
                st.logout()
            return False

        configured_admins = st.secrets.get("pharmaguard", {}).get("admin_emails", [])
        if isinstance(configured_admins, str):
            configured_admins = [configured_admins]
        admin_emails = {
            str(admin_email).strip().casefold()
            for admin_email in configured_admins
            if str(admin_email).strip()
        }
        st.session_state["authenticated"] = True
        st.session_state["username"] = email
        st.session_state["role"] = "Admin" if email in admin_emails else "User"
        st.session_state["auth_method"] = "google"
        return True

    if (
        st.session_state.get("authenticated")
        and st.session_state.get("auth_method") == "local"
    ):
        return True

    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["auth_method"] = None
    st.header("Welcome to PharmaGuard")
    st.write("Sign in to your account or create one to access the interaction checker.")
    sign_in_tab, create_account_tab = st.tabs(["Sign in", "Create account"])

    with sign_in_tab:
        with st.form("account_login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            login_submitted = st.form_submit_button("Sign in", use_container_width=True)
        if login_submitted:
            try:
                if auth.authenticate(email, password):
                    st.rerun()
                st.error("Email or password is incorrect.")
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))

    with create_account_tab:
        with st.form("create_account_form"):
            new_email = st.text_input("Email address", key="create_email")
            new_password = st.text_input(
                "Password (at least 12 characters)",
                type="password",
                key="create_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="confirm_password",
            )
            create_submitted = st.form_submit_button(
                "Create account", use_container_width=True
            )
        if create_submitted:
            try:
                auth.create_account(new_email, new_password, confirm_password)
                st.success("Account created. Sign in with your new credentials.")
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))

    st.divider()
    auth_configured = bool(st.secrets.get("auth", {}).get("client_id"))
    if auth_configured:
        if st.button("Continue with Google", use_container_width=True):
            st.login()
    else:
        st.caption("Google sign-in is available when OAuth is configured by the administrator.")
    return False


def _render_interaction_result(row: dict[str, Any]) -> None:
    severity_colors = {
        "Low": "#2e8b57",
        "Moderate": "#d4a017",
        "High": "#e87500",
        "Critical": "#c62828",
    }
    severity = row["severity"]
    st.markdown(
        f"### {row['drug1']} + {row['drug2']} "
        f"<span style='color:{severity_colors.get(severity, '#555')};font-size:0.8em'>"
        f"— {severity} risk</span>",
        unsafe_allow_html=True,
    )
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=int(row["percentile"]),
            number={"suffix": "%"},
            title={"text": "Knowledge-base risk percentile*"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": severity_colors.get(severity, "#496a81")},
                "steps": [
                    {"range": [0, 25], "color": "#e8f5e9"},
                    {"range": [25, 50], "color": "#fff8e1"},
                    {"range": [50, 75], "color": "#fff3e0"},
                    {"range": [75, 100], "color": "#ffebee"},
                ],
            },
        )
    )
    gauge.update_layout(height=230, margin={"t": 55, "b": 10, "l": 25, "r": 25})
    left, right = st.columns([1, 2])
    with left:
        st.plotly_chart(gauge, use_container_width=True, key=f"gauge_{row['id']}")
        st.caption("*Editorial indicator only; not an individual probability or validated clinical score.")
    with right:
        st.markdown(f"**How the medicines interact**  \n{row['mechanism']}")
        st.markdown(f"**What may be happening in the body**  \n{row['what_happens']}")
        st.markdown(f"**Why this may be harmful**  \n{row['why_harmful']}")
        st.markdown(f"**Symptoms to watch for**  \n{row['symptoms']}")
        st.info(f"**Precautions and next steps:** {row['precautions']}")
    st.divider()


def _render_checker(records: list[dict[str, Any]]) -> None:
    st.header("Medication interaction checker")
    st.write("Select medications you currently take or are considering discussing with a clinician.")
    medications = sorted(
        {str(row[field]).strip() for row in records for field in ("drug1", "drug2")},
        key=str.casefold,
    )
    selected = st.multiselect(
        "Medications",
        medications,
        key="selected_medications",
        help="Only medication pairs present in the verified knowledge base are reported.",
    )
    if len(selected) < 2:
        st.info("Select at least two medications to check known pairs.")
        return
    try:
        matches = _get_search_engine(records).search(selected)
    except (ValueError, RuntimeError) as exc:
        logger.exception("Interaction search failed")
        st.error(f"Could not search the interaction knowledge base: {exc}")
        return
    if not matches:
        st.success("No matching interaction is listed for these selected pairs in this knowledge base.")
        st.caption("This is not proof that the combination is safe. Ask a clinician or pharmacist.")
        return
    st.warning(
        f"Found {len(matches)} known interaction(s). Risk depends on your health, doses, "
        "timing, and other medicines; discuss every result with a clinician."
    )
    for match in matches:
        _render_interaction_result(match)


def _render_analytics(records: list[dict[str, Any]]) -> None:
    st.header("Knowledge-base analytics")
    if not records:
        st.info("No interaction records are available.")
        return
    frame = pd.DataFrame(records)
    total, high_risk, medication_count = st.columns(3)
    total.metric("Known pairs", len(frame))
    high_risk.metric("High / Critical pairs", int(frame["severity"].isin(["High", "Critical"]).sum()))
    medication_count.metric(
        "Distinct medications",
        len(set(frame["drug1"].str.casefold()) | set(frame["drug2"].str.casefold())),
    )
    first, second = st.columns(2)
    with first:
        severity_order = ["Low", "Moderate", "High", "Critical"]
        counts = frame["severity"].value_counts().reindex(severity_order, fill_value=0)
        chart = px.bar(
            x=counts.index,
            y=counts.values,
            labels={"x": "Severity", "y": "Number of pairs"},
            title="Interaction records by severity",
            color=counts.index,
            color_discrete_map={
                "Low": "#2e8b57",
                "Moderate": "#d4a017",
                "High": "#e87500",
                "Critical": "#c62828",
            },
        )
        st.plotly_chart(chart, use_container_width=True)
    with second:
        pie = px.pie(frame, names="severity", title="Knowledge-base severity mix")
        st.plotly_chart(pie, use_container_width=True)
    st.caption("Charts summarize the local knowledge base, not patient-specific outcomes.")


def _render_admin(records: list[dict[str, Any]]) -> None:
    st.header("Admin dashboard")
    st.warning(
        "Only add interactions supported by reliable clinical references and reviewed by a "
        "qualified professional. Knowledge-base entries are not automatically clinically validated."
    )
    with st.form("add_interaction_form", clear_on_submit=True):
        first, second = st.columns(2)
        with first:
            drug1 = st.text_input("Medication 1")
            severity = st.selectbox("Severity", database.SEVERITIES)
            mechanism = st.text_area("Pharmacological mechanism")
            why_harmful = st.text_area("Why it may be harmful")
            precautions = st.text_area("Precautions / mitigation")
        with second:
            drug2 = st.text_input("Medication 2")
            percentile = st.number_input("Editorial risk percentile", min_value=0, max_value=100, value=50)
            what_happens = st.text_area("What happens biologically")
            symptoms = st.text_area("Symptoms to watch for")
        submitted = st.form_submit_button("Save interaction and rebuild search index")
    if submitted:
        try:
            database.add_interaction(
                {
                    "drug1": drug1,
                    "drug2": drug2,
                    "severity": severity,
                    "percentile": percentile,
                    "mechanism": mechanism,
                    "what_happens": what_happens,
                    "why_harmful": why_harmful,
                    "symptoms": symptoms,
                    "precautions": precautions,
                }
            )
            refreshed = database.get_interactions()
            st.session_state["faiss_engine"] = DrugInteractionSearch(refreshed)
            st.session_state["faiss_signature"] = tuple(
                (row.get("id"), row["drug1"].casefold(), row["drug2"].casefold())
                for row in refreshed
            )
            st.success("Interaction saved; the search index has been rebuilt.")
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
    st.subheader("Current knowledge base")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Medication 1": row["drug1"],
                    "Medication 2": row["drug2"],
                    "Severity": row["severity"],
                    "Risk percentile*": row["percentile"],
                }
                for row in records
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("*Editorial indicator only; not an individualized probability.")


try:
    database.initialize_database()
    database.initialize_session_state()
except RuntimeError as exc:
    logger.exception("Database initialization failed")
    st.error(str(exc))
    st.stop()

if not _render_login():
    st.info("Sign in to access PharmaGuard.")
    st.stop()

with st.sidebar:
    st.write(f"Signed in: **{st.session_state['username']}** ({st.session_state['role']})")
    if st.button("Log out", use_container_width=True):
        if st.session_state.get("auth_method") == "google":
            st.logout()
        else:
            auth.logout()
            st.rerun()
    pages = ["Interaction checker", "Analytics"]
    if st.session_state["role"] == "Admin":
        pages.append("Admin dashboard")
    page = st.radio("Navigate", pages)

try:
    interaction_records = database.get_interactions()
except RuntimeError as exc:
    logger.exception("Could not load interactions")
    st.error(str(exc))
    st.stop()

if page == "Interaction checker":
    _render_checker(interaction_records)
elif page == "Analytics":
    _render_analytics(interaction_records)
elif page == "Admin dashboard" and st.session_state["role"] == "Admin":
    _render_admin(interaction_records)
