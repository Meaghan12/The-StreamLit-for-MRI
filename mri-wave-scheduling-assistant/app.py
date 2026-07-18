import streamlit as st
import pandas as pd
import os
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="MRI Wave Scheduling Assistant", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS FOR MODERN AESTHETICS ---
st.markdown("""
<style>
    /* Global Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Vibrant Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        color: #f8fafc;
    }
    /* Fixed input text visibility */
    .stTextInput input, .stNumberInput input {
        color: #1e293b !important;
    }
    
    /* Clean Cards / Containers */
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
    
    /* Headers */
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- STATE INITIALIZATION ---
if 'queue_df' not in st.session_state:
    if os.path.exists("sample_patient_queue.csv"):
        st.session_state.queue_df = pd.read_csv("sample_patient_queue.csv")
    else:
        st.session_state.queue_df = pd.DataFrame(columns=[
            "patient_id", "protocol", "scanner_eligibility", "estimated_duration", 
            "arrival_status", "readiness_status", "contrast_required", 
            "sedation_required", "acuity", "transport_complexity", "risk_of_delay"
        ])

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png", width=60)
    st.title("MRI Wave Assist")
    st.markdown("Operational Decision-Support")
    
    st.header("1. Input Open Slot")
    open_scanner = st.selectbox("Scanner", ["1.5T", "3T", "Either"])
    gap_minutes = st.number_input("Available Gap (minutes)", min_value=15, max_value=240, value=45, step=15)
    current_time = st.time_input("Current Time", value=datetime.time(10, 0))
    
    st.markdown("---")
    st.caption("Note: This tool provides operational scheduling candidates for human review by the Admin Tech. It does not make clinical decisions.")

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dashboard", 
    "Patient Queue", 
    "Lego-Block Ranking", 
    "Scenario Comparison", 
    "Export"
])

# --- TAB 1: DASHBOARD ---
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
        c1.metric("Ready Now", len(df[df['readiness_status'] == 'Ready']))
        c2.metric("Late", len(df[df['arrival_status'] == 'Late']))
        c3.metric("No-Show", len(df[df['arrival_status'] == 'No-Show']))
        c4.metric("Needs Contrast", len(df[df['contrast_required'] == 'Yes']))

# --- TAB 2: PATIENT QUEUE ---
with tab2:
    st.header("Patient Queue")
    st.write("Upload a CSV or manually edit the current queue below.")
    
    uploaded_file = st.file_uploader("Upload Queue CSV", type=['csv'])
    if uploaded_file is not None:
        st.session_state.queue_df = pd.read_csv(uploaded_file)
        st.success("File uploaded successfully!")
        
    st.markdown("### Editable Queue")
    edited_df = st.data_editor(st.session_state.queue_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("Save Changes"):
        st.session_state.queue_df = edited_df
        st.success("Queue updated.")

# --- TAB 3: LEGO-BLOCK CANDIDATE RANKING ---
with tab3:
    st.header("Lego-Block Candidate Ranking")
    st.markdown("Transparent scoring logic to find the best replacement patient.")
    
    df = st.session_state.queue_df.copy()
    
    if df.empty:
        st.info("Queue is empty. Please add patients in the Patient Queue tab.")
    else:
        # Transparent Scoring Rule
        def calculate_score(row):
            score = 0
            reasons = []
            
            # 1. Readiness (Most important)
            if row['readiness_status'] == 'Ready':
                score += 100
                reasons.append("Ready Now (+100)")
            else:
                reasons.append("Not Ready")
                
            # 2. Scanner Eligibility
            if row['scanner_eligibility'] == open_scanner or row['scanner_eligibility'] == 'Either' or open_scanner == 'Either':
                score += 50
                reasons.append("Scanner Match (+50)")
                
            # 3. Duration fit
            try:
                est_dur = int(row['estimated_duration'])
                if est_dur <= gap_minutes:
                    score += 40
                    reasons.append("Duration Fits Gap (+40)")
                else:
                    reasons.append("Exceeds Gap Time")
            except:
                pass
                
            # 4. Delay Risk
            if row['risk_of_delay'] == 'Low':
                score += 30
                reasons.append("Low Delay Risk (+30)")
                
            # 5. Acuity
            if row['acuity'] == 'High':
                score += 20
                reasons.append("High Acuity (+20)")
                
            return score, ", ".join(reasons)

        scores = df.apply(calculate_score, axis=1)
        df['Score'] = [s[0] for s in scores]
        df['Why selected'] = [s[1] for s in scores]
        
        # Rank the candidates
        ranked_df = df.sort_values(by='Score', ascending=False).reset_index(drop=True)
        ranked_df['Rank'] = ranked_df.index + 1
        
        display_cols = ['Rank', 'patient_id', 'protocol', 'scanner_eligibility', 'estimated_duration', 'Score', 'Why selected']
        st.dataframe(ranked_df[display_cols], use_container_width=True, hide_index=True)
        
        # Store for export
        st.session_state.ranked_df = ranked_df

# --- TAB 4: SCENARIO COMPARISON ---
with tab4:
    st.header("Simulation Insights: Why Wave Scheduling?")
    st.markdown("""
    > "Project Five showed that arrival-status routing alone was not enough. Policy B failed because it separated early/on-time/late patients but did not actively choose a replacement patient. This Streamlit prototype implements the missing step: selecting the best ready patient for the open scanner gap."
    """)
    
    st.subheader("Policy A vs Policy B Output")
    
    col1, col2 = st.columns(2)
    
    # Load images if they exist
    box_path = "assets/staytime_boxplot.png"
    bar_path = "assets/utilization_bar.png"
    
    with col1:
        if os.path.exists(box_path):
            st.image(box_path, caption="Staytime Comparison (Winsorized)", use_container_width=True)
        else:
            st.info("Staytime comparison chart not found in assets/")
            
    with col2:
        if os.path.exists(bar_path):
            st.image(bar_path, caption="Utilization Breakdown", use_container_width=True)
        else:
            st.info("Utilization chart not found in assets/")

# --- TAB 5: EXPORT ---
with tab5:
    st.header("Export Recommendations")
    
    if 'ranked_df' in st.session_state and not st.session_state.ranked_df.empty:
        best_patient = st.session_state.ranked_df.iloc[0]
        st.success(f"Top Recommendation: **{best_patient['patient_id']}** ({best_patient['protocol']})")
        
        csv_data = st.session_state.ranked_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Candidate Ranking (CSV)",
            data=csv_data,
            file_name="mri_candidate_ranking.csv",
            mime="text/csv"
        )
        
        st.markdown("### Wet-Schedule Recommendation Report")
        report_text = f"""
        # MRI Wet-Schedule Optimizer Report
        Date: {datetime.date.today()}
        Time: {current_time}
        
        **Open Slot Details:**
        Scanner: {open_scanner}
        Available Gap: {gap_minutes} minutes
        
        **Recommended Replacement:**
        Patient ID: {best_patient['patient_id']}
        Protocol: {best_patient['protocol']}
        Estimated Duration: {best_patient['estimated_duration']} mins
        Reason: {best_patient['Why selected']}
        
        *Note: This is an operational suggestion for human review.*
        """
        st.text_area("Report Preview", value=report_text, height=250)
        
        st.download_button(
            label="Download Report (TXT)",
            data=report_text.encode('utf-8'),
            file_name="mri_wet_schedule_report.txt",
            mime="text/plain"
        )
    else:
        st.info("Please run the Lego-Block Ranking first to generate exportable reports.")
