import datetime
import os

import pandas as pd
import streamlit as st


# --- CONFIGURATION ---
st.set_page_config(
    page_title="MRI Wave Scheduling Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Directory containing app.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

QUEUE_FILE = os.path.join(SCRIPT_DIR, "sample_patient_queue.csv")
KNN_FILE = os.path.join(
    SCRIPT_DIR,
    "knn_top_10_lego_candidates_revised.csv",
)


# --- CUSTOM CSS ---
st.markdown(
    """
    <style>
        @import url(
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap'
        );

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        [data-testid="stSidebar"] {
            background-color: #0f172a;
            color: #f8fafc;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {
            color: #f8fafc !important;
        }

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] select,
        [data-testid="stSidebar"] .stNumberInput input {
            color: #1e293b !important;
            background-color: #ffffff !important;
        }

        div[data-testid="stMetricValue"] {
            color: #3b82f6;
        }

        div.stButton > button {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }

        h1, h2, h3 {
            color: #1e293b;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- HELPER FUNCTIONS ---
def load_csv_safely(path: str) -> pd.DataFrame:
    """Load a CSV file or return an empty DataFrame if it is unavailable."""
    try:
        if os.path.exists(path):
            return pd.read_csv(path)
    except Exception as exc:
        st.error(f"Could not load {os.path.basename(path)}: {exc}")

    return pd.DataFrame()


def calculate_operational_score(
    row: pd.Series,
    scanner: str,
    available_minutes: int,
) -> tuple[int, str]:
    """Calculate the transparent rule-based replacement score."""
    score = 0
    reasons: list[str] = []

    readiness = str(row.get("readiness_status", "")).strip()
    scanner_eligibility = str(row.get("scanner_eligibility", "")).strip()
    risk = str(row.get("risk_of_delay", "")).strip()
    acuity = str(row.get("acuity", "")).strip()

    if readiness == "Ready":
        score += 100
        reasons.append("Ready Now (+100)")
    else:
        reasons.append("Not Ready")

    scanner_match = (
        scanner_eligibility == scanner
        or scanner_eligibility == "Either"
        or scanner == "Either"
    )

    if scanner_match:
        score += 50
        reasons.append("Scanner Match (+50)")
    else:
        reasons.append("Scanner Mismatch")

    try:
        duration = float(row.get("estimated_duration", 0))

        if duration <= available_minutes:
            score += 40
            reasons.append("Duration Fits Gap (+40)")
        else:
            reasons.append("Exceeds Gap Time")
    except (TypeError, ValueError):
        reasons.append("Duration Unavailable")

    if risk == "Low":
        score += 30
        reasons.append("Low Delay Risk (+30)")

    if acuity == "High":
        score += 20
        reasons.append("High Acuity (+20)")

    return score, ", ".join(reasons)


# --- SESSION STATE ---
if "queue_df" not in st.session_state:
    queue_df = load_csv_safely(QUEUE_FILE)

    if queue_df.empty:
        queue_df = pd.DataFrame(
            columns=[
                "patient_id",
                "protocol",
                "scanner_eligibility",
                "estimated_duration",
                "arrival_status",
                "readiness_status",
                "contrast_required",
                "sedation_required",
                "acuity",
                "transport_complexity",
                "risk_of_delay",
            ]
        )

    st.session_state.queue_df = queue_df

if "ranked_df" not in st.session_state:
    st.session_state.ranked_df = pd.DataFrame()

if "selected_ranking_method" not in st.session_state:
    st.session_state.selected_ranking_method = "Live operational score"


# Load the revised KNN results
knn_results = load_csv_safely(KNN_FILE)


# --- SIDEBAR ---
with st.sidebar:
    st.title("MRI Wave Assist")
    st.markdown("Operational Decision-Support")

    st.header("1. Input Open Slot")

    open_scanner = st.selectbox(
        "Scanner",
        ["1.5T", "3T", "Either"],
        index=1,
    )

    gap_minutes = st.number_input(
        "Available Gap (minutes)",
        min_value=15,
        max_value=240,
        value=30,
        step=15,
    )

    current_time = st.time_input(
        "Current Time",
        value=datetime.time(10, 0),
    )

    st.markdown("---")

    st.caption(
        "This tool provides operational scheduling candidates for human "
        "review by the Admin Tech. It does not make clinical decisions."
    )


# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Dashboard",
        "Patient Queue",
        "Lego-Block Ranking",
        "Scenario Comparison",
        "Export",
    ]
)


# --- DASHBOARD ---
with tab1:
    st.header("Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.metric("Open Scanner", open_scanner)
    col2.metric("Time Gap", f"{gap_minutes} mins")
    col3.metric("Current Queue Size", len(st.session_state.queue_df))

    st.markdown("### Queue Breakdown")

    if not st.session_state.queue_df.empty:
        df = st.session_state.queue_df

        c1, c2, c3, c4 = st.columns(4)

        if "readiness_status" in df.columns:
            ready_count = len(df[df["readiness_status"] == "Ready"])
        else:
            ready_count = 0

        if "arrival_status" in df.columns:
            late_count = len(df[df["arrival_status"] == "Late"])
            no_show_count = len(df[df["arrival_status"] == "No-Show"])
        else:
            late_count = 0
            no_show_count = 0

        if "contrast_required" in df.columns:
            contrast_count = len(df[df["contrast_required"] == "Yes"])
        else:
            contrast_count = 0

        c1.metric("Ready Now", ready_count)
        c2.metric("Late", late_count)
        c3.metric("No-Show", no_show_count)
        c4.metric("Needs Contrast", contrast_count)
    else:
        st.info("The patient queue is empty.")


# --- PATIENT QUEUE ---
with tab2:
    st.header("Patient Queue")

    st.write(
        "Upload a CSV or manually edit the current synthetic queue below."
    )

    uploaded_file = st.file_uploader(
        "Upload Queue CSV",
        type=["csv"],
    )

    if uploaded_file is not None:
        try:
            st.session_state.queue_df = pd.read_csv(uploaded_file)
            st.success("Queue uploaded successfully.")
        except Exception as exc:
            st.error(f"Could not read the uploaded CSV: {exc}")

    st.markdown("### Editable Queue")

    edited_df = st.data_editor(
        st.session_state.queue_df,
        num_rows="dynamic",
        use_container_width=True,
    )

    if st.button("Save Queue Changes"):
        st.session_state.queue_df = edited_df
        st.success("Queue updated.")


# --- LEGO-BLOCK RANKING ---
with tab3:
    st.header("Lego-Block Candidate Ranking")

    st.markdown(
        "Review either the live transparent operational score or the "
        "precomputed KNN similarity analysis."
    )

    ranking_method = st.radio(
        "Ranking view",
        [
            "Live operational score",
            "KNN 30-minute 3T scenario",
        ],
        horizontal=True,
    )

    st.session_state.selected_ranking_method = ranking_method

    if ranking_method == "Live operational score":
        st.subheader("Live Operational Candidate Ranking")

        st.caption(
            "This ranking responds to the scanner and gap selected in the sidebar."
        )

        df = st.session_state.queue_df.copy()

        if df.empty:
            st.info(
                "The queue is empty. Add patients in the Patient Queue tab."
            )
        else:
            required_columns = {
                "patient_id",
                "protocol",
                "scanner_eligibility",
                "estimated_duration",
                "readiness_status",
                "risk_of_delay",
                "acuity",
            }

            missing_columns = required_columns.difference(df.columns)

            if missing_columns:
                st.error(
                    "The patient queue is missing these required columns: "
                    + ", ".join(sorted(missing_columns))
                )
            else:
                scoring_results = df.apply(
                    lambda row: calculate_operational_score(
                        row,
                        open_scanner,
                        gap_minutes,
                    ),
                    axis=1,
                )

                df["Score"] = [result[0] for result in scoring_results]
                df["Why selected"] = [
                    result[1] for result in scoring_results
                ]

                ranked_df = (
                    df.sort_values(
                        by="Score",
                        ascending=False,
                    )
                    .reset_index(drop=True)
                )

                ranked_df["Rank"] = ranked_df.index + 1

                display_columns = [
                    "Rank",
                    "patient_id",
                    "protocol",
                    "scanner_eligibility",
                    "estimated_duration",
                    "Score",
                    "Why selected",
                ]

                st.dataframe(
                    ranked_df[display_columns],
                    use_container_width=True,
                    hide_index=True,
                )

                st.session_state.ranked_df = ranked_df

                st.caption(
                    "The live score is a transparent operational rule, not a "
                    "clinical recommendation."
                )

    else:
        st.subheader(
            "Top KNN Lego-Block Replacement Candidates "
            "for a 30-Minute 3T Opening"
        )

        if knn_results.empty:
            st.error(
                "The revised KNN file was not found. Upload "
                "'knn_top_10_lego_candidates_revised.csv' beside app.py."
            )
        else:
            preferred_columns = [
                "rank",
                "patient_number",
                "protocol",
                "scanner_eligibility",
                "simulated_duration",
                "unused_gap_minutes",
                "contrast",
                "sedation_anaesthesia",
                "arrival_status",
                "priority_acuity",
                "delay_risk",
                "knn_distance",
                "assigned_scanner",
            ]

            available_columns = [
                column
                for column in preferred_columns
                if column in knn_results.columns
            ]

            st.dataframe(
                knn_results[available_columns],
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Synthetic candidates were first filtered for scanner "
                "compatibility, readiness, safety constraints, and ability to "
                "fit within the 30-minute opening. Lower KNN distance indicates "
                "greater similarity to the target replacement profile within "
                "the synthetic dataset. It does not establish external "
                "generalizability to real patient populations."
            )

            st.session_state.knn_ranked_df = knn_results.copy()


# --- SCENARIO COMPARISON ---
with tab4:
    st.header("Simulation Insights: Why Wave Scheduling?")

    st.markdown(
        """
        > Project Five showed that arrival-status routing alone was not enough.
        > Policy B separated early, on-time, and late patients but did not
        > actively choose the best ready replacement patient. This Streamlit
        > prototype demonstrates that missing decision-support step.
        """
    )

    st.subheader("Policy A versus Policy B Output")

    col1, col2 = st.columns(2)

    box_path = os.path.join(
        SCRIPT_DIR,
        "assets",
        "staytime_boxplot.png",
    )

    bar_path = os.path.join(
        SCRIPT_DIR,
        "assets",
        "utilization_bar.png",
    )

    with col1:
        if os.path.exists(box_path):
            st.image(
                box_path,
                caption="Stay-Time Comparison",
                use_container_width=True,
            )
        else:
            st.info("Stay-time chart not found in the assets folder.")

    with col2:
        if os.path.exists(bar_path):
            st.image(
                bar_path,
                caption="Utilization Breakdown",
                use_container_width=True,
            )
        else:
            st.info("Utilization chart not found in the assets folder.")


# --- EXPORT ---
with tab5:
    st.header("Export Recommendations")

    ranking_method = st.session_state.selected_ranking_method

    if (
        ranking_method == "KNN 30-minute 3T scenario"
        and "knn_ranked_df" in st.session_state
        and not st.session_state.knn_ranked_df.empty
    ):
        export_df = st.session_state.knn_ranked_df.copy()
        best_patient = export_df.iloc[0]

        patient_id = best_patient.get(
            "patient_number",
            "Not available",
        )

        protocol = best_patient.get(
            "protocol",
            "Not available",
        )

        duration = best_patient.get(
            "simulated_duration",
            "Not available",
        )

        knn_distance = best_patient.get(
            "knn_distance",
            "Not available",
        )

        st.success(
            f"Top KNN Candidate: **{patient_id}** ({protocol})"
        )

        csv_data = export_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download KNN Candidate Ranking (CSV)",
            data=csv_data,
            file_name="mri_knn_candidate_ranking.csv",
            mime="text/csv",
        )

        st.markdown("### KNN Scenario Recommendation Report")

        report_text = f"""MRI KNN Lego-Block Candidate Report

Date: {datetime.date.today()}
Time: {current_time}

Open Slot Scenario:
Scanner: 3T
Available Gap: 30 minutes

Top Similarity Candidate:
Patient ID: {patient_id}
Protocol: {protocol}
Simulated Duration: {duration} minutes
KNN Distance: {knn_distance}

Interpretation:
A lower KNN distance indicates greater similarity to the target
replacement profile within the synthetic dataset.

Note:
This is a synthetic decision-support demonstration for human review.
It is not a clinical recommendation and does not establish external
generalizability to real patient populations.
"""

        st.text_area(
            "Report Preview",
            value=report_text,
            height=350,
        )

        st.download_button(
            label="Download KNN Report (TXT)",
            data=report_text.encode("utf-8"),
            file_name="mri_knn_recommendation_report.txt",
            mime="text/plain",
        )

    elif (
        "ranked_df" in st.session_state
        and not st.session_state.ranked_df.empty
    ):
        export_df = st.session_state.ranked_df.copy()
        best_patient = export_df.iloc[0]

        st.success(
            f"Top Recommendation: **{best_patient['patient_id']}** "
            f"({best_patient['protocol']})"
        )

        csv_data = export_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Candidate Ranking (CSV)",
            data=csv_data,
            file_name="mri_candidate_ranking.csv",
            mime="text/csv",
        )

        st.markdown("### Wet-Schedule Recommendation Report")

        report_text = f"""MRI Wet-Schedule Optimizer Report

Date: {datetime.date.today()}
Time: {current_time}

Open Slot Details:
Scanner: {open_scanner}
Available Gap: {gap_minutes} minutes

Recommended Replacement:
Patient ID: {best_patient['patient_id']}
Protocol: {best_patient['protocol']}
Duration: {best_patient['estimated_duration']} minutes

Selection Logic:
Score: {best_patient['Score']}
Reasons: {best_patient['Why selected']}

Note:
This is an operational suggestion for human review by the Admin Tech.
It does not make a clinical decision.
"""

        st.text_area(
            "Report Preview",
            value=report_text,
            height=350,
        )

        st.download_button(
            label="Download Report (TXT)",
            data=report_text.encode("utf-8"),
            file_name="mri_wet_schedule_report.txt",
            mime="text/plain",
        )

    else:
        st.info(
            "Open the Lego-Block Ranking tab and generate or select a "
            "candidate ranking before exporting."
        )
