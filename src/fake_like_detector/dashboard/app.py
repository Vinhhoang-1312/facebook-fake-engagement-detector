from __future__ import annotations

import pandas as pd
import streamlit as st

from fake_like_detector.config import Settings
from fake_like_detector.dashboard.queries import DashboardRepository
from fake_like_detector.storage.db import create_engine_and_session
from fake_like_detector.storage.repository import Repository


def main() -> None:
    st.set_page_config(page_title="Fake Engagement Detector", layout="wide")
    settings = Settings()
    _, factory = create_engine_and_session(settings.database_url)
    dashboard = DashboardRepository(Repository(factory))
    st.title("Facebook Engagement Anomaly Review")
    st.caption("Anomaly risk is not fraud probability and not fake-account percentage.")
    page = st.sidebar.radio("Page", ["Overview", "Posts", "Post Detail", "Data Health", "Review Queue", "Coordination"])
    if page == "Overview":
        view = dashboard.overview()
        columns = st.columns(4)
        columns[0].metric("Posts", view.post_count)
        columns[1].metric("Assessments", view.assessed_count)
        columns[2].metric("Suspicious", view.suspicious_count)
        columns[3].metric("Failed collections", view.failed_collection_runs)
    elif page in {"Posts", "Review Queue"}:
        rows = dashboard.posts()
        if page == "Review Queue":
            rows = [row for row in rows if row.risk_level in {"watch", "suspicious", "highly_suspicious"}]
        st.dataframe(pd.DataFrame([row.__dict__ for row in rows]), use_container_width=True)
    elif page == "Post Detail":
        posts = dashboard.posts()
        if not posts:
            st.info("No posts yet. Run the demo or collect command first.")
        else:
            selected = st.selectbox("Post", [item.post_id for item in posts])
            detail = dashboard.post_detail(selected)
            st.subheader(f"Risk: {detail.post.risk_level}")
            st.dataframe(pd.DataFrame(detail.snapshots), use_container_width=True)
            st.write("Evidence", detail.evidence or "None")
            st.write("Counter-evidence", detail.counter_evidence or "None")
    elif page == "Data Health":
        st.json(dashboard.data_health().__dict__)
    else:
        st.info("Account-level coordination needs privacy-reviewed actor interaction data. It is intentionally disabled in this MVP.")


if __name__ == "__main__":
    main()

