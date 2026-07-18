# MRI Wave Scheduling Decision-Support Tool

> This Streamlit prototype translates MRI simulation findings into an operational decision-support tool. It helps an Admin Tech identify the best ready, scanner-eligible replacement patient when the scheduled patient is late, not ready, cancelled, or a no-show. The tool uses transparent ranking logic based on readiness, scanner eligibility, estimated scan duration, protocol fit, contrast/sedation complexity, acuity, and delay risk. It is not a clinical decision system; it is a human-in-the-loop scheduling support prototype.

## Running the App

1. Ensure you have `streamlit` and `pandas` installed (e.g., `pip install streamlit pandas`).
2. Run the application from this directory:
   ```bash
   uv run streamlit run app.py
   # or
   streamlit run app.py
   ```

## Workflow

1. **Patient Queue**: Upload or review the current patient queue.
2. **Dashboard**: Enter the current open scanner gap and details.
3. **Lego-Block Ranking**: Rank candidates based on standard transparent operational rules.
4. **Scenario Comparison**: Review the simulation results (Policy A vs Policy B) that justify active wave scheduling.
5. **Export**: Export the recommended replacement to a CSV report for the record.
