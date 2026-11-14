import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="CBB MPI Analytics & Bracketology",
    page_icon="🏀",
    layout="wide",
)

st.title("🏀 College Basketball MPI Analytics & Bracketology")
st.caption(
    "Tempo-Free Opponent-Adjusted Efficiency (MPI), WAB, Monte Carlo Season Simulations & 76-Team Bracketology"
)

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊 Metrics (MPI & WAB)",
        "🎲 Season Forecasts",
        "🏆 Bracketology",
        "📅 Daily Game Projections",
    ]
)

# --- TAB 1: METRICS ---
with tab1:
    st.subheader("Team Efficiency & Resume Metrics")
    ratings = pd.read_csv("data/ratings.csv")

    col1, col2 = st.columns(2)
    with col1:
        confs = ["All Conferences"] + sorted(
            ratings["Conference"].dropna().unique().tolist()
        )
        selected_conf = st.selectbox(
            "Filter by Conference:", confs, key="metrics_conf"
        )
    with col2:
        search_team = st.text_input(
            "Search Team:", placeholder="e.g., Duke, Kansas, Gonzaga..."
        )

    view_df = ratings.copy()
    if selected_conf != "All Conferences":
        view_df = view_df[view_df["Conference"] == selected_conf]
    if search_team:
        view_df = view_df[
            view_df["Team and Record"].str.contains(
                search_team, case=False, na=False
            )
        ]

    display_cols = [
        "Rank",
        "Team and Record",
        "MPI",
        "Off. Eff.",
        "Def. Eff.",
        "WAB",
        "SOS",
        "Quality Wins",
    ]
    st.dataframe(
        view_df[display_cols],
        use_container_width=True,
        hide_index=True,
        height=600,
    )

# --- TAB 2: FORECASTS ---
with tab2:
    st.subheader("Monte Carlo Season Forecasts (5,000 Simulations)")
    forecasts = pd.read_csv("data/forecasts.csv")

    f_confs = ["All Conferences"] + sorted(
        forecasts["Conference"].dropna().unique().tolist()
    )
    f_conf = st.selectbox(
        "Filter by Conference:", f_confs, key="forecast_conf"
    )

    f_view = forecasts.copy()
    if f_conf != "All Conferences":
        f_view = f_view[f_view["Conference"] == f_conf]

    f_cols = [
        "Rank",
        "Team and Record",
        "MPI",
        "Proj. W-L",
        "Proj. Conf. W-L",
        "% to Win Conf.",
        "% to Make March Madness",
    ]
    st.dataframe(
        f_view[f_cols],
        use_container_width=True,
        hide_index=True,
        height=600,
    )

# --- TAB 3: BRACKETOLOGY ---
with tab3:
    st.subheader("NCAA Tournament 76-Team Bracketology (2027 Format)")

    bracket_mode = st.radio(
        "Select Bracket View:",
        [
            "Current Bracket (Based on Current Resume & MPI)",
            "Projected Bracket (Based on Season Simulations)",
        ],
        horizontal=True,
    )

    if "Current" in bracket_mode:
        b_df = pd.read_csv("data/bracket_current.csv")
    else:
        b_df = pd.read_csv("data/bracket_projected.csv")

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.info(
            "**Opening Round (12 At-Large Play-In Teams):**\n\n"
            + "\n".join(
                f"- {t}"
                for t in b_df[
                    b_df["Bubble Status"].str.contains(
                        "Opening Round (At-Large", regex=False, na=False
                    )
                ]["Team and Record"]
            )
        )
    with b_col2:
        st.warning(
            "**First Four Out (#77–#80):**\n\n"
            + "\n".join(
                f"- {t}"
                for t in b_df[
                    b_df["Bubble Status"].str.contains(
                        "First Four Out", na=False
                    )
                ]["Team and Record"]
            )
        )

    reg_tabs = st.tabs(["All Seeds (1-76)", "East", "South", "Midwest", "West"])
    with reg_tabs[0]:
        st.dataframe(b_df, use_container_width=True, hide_index=True, height=650)

    for idx, region_name in enumerate(["East", "South", "Midwest", "West"], start=1):
        with reg_tabs[idx]:
            reg_df = b_df[b_df["Region"] == region_name].sort_values("Seed")
            st.dataframe(reg_df, use_container_width=True, hide_index=True)

# --- TAB 4: DAILY GAME PROJECTIONS ---
with tab4:
    st.subheader("Today's Slate: Game-by-Game Projections")
    daily = pd.read_csv("data/daily_projections.csv")
    st.dataframe(daily, use_container_width=True, hide_index=True, height=650)
