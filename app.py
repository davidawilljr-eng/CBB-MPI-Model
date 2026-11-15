import pandas as pd
import streamlit as st

st.set_page_config(page_title="CBB MPI Analytics & Bracketology", page_icon="🏀", layout="wide")

ratings = pd.read_csv("data/ratings.csv")
forecasts = pd.read_csv("data/forecasts.csv")
game_info = pd.read_csv("data/game_info.csv")

for df_tmp in [ratings, forecasts]:
    if "Team" not in df_tmp.columns:
        df_tmp["Team"] = df_tmp["Team and Record"].str.replace(r"\s*\(\d+-\d+\)$", "", regex=True)

all_teams = sorted(ratings["Team"].dropna().unique().tolist())

if "selected_team" not in st.session_state:
    st.session_state.selected_team = "None (View Full Tables)"

st.title("🏀 College Basketball MPI Analytics & Bracketology")
st.caption("Tempo-Free Opponent-Adjusted Efficiency (MPI), WAB, Monte Carlo Season Simulations & 76-Team Bracketology")

nav_col1, nav_col2 = st.columns([4, 1])
with nav_col1:
    opts = ["None (View Full Tables)"] + all_teams
    idx = opts.index(st.session_state.selected_team) if st.session_state.selected_team in opts else 0
    st.session_state.selected_team = st.selectbox("🔍 Inspect Team Profile (Ratings, Projections & Full Game Log):", opts, index=idx)

with nav_col2:
    st.write("")
    st.write("")
    if st.session_state.selected_team != "None (View Full Tables)":
        if st.button("✖ Close Team Page", use_container_width=True):
            st.session_state.selected_team = "None (View Full Tables)"
            st.rerun()

if st.session_state.selected_team != "None (View Full Tables)":
    t_name = st.session_state.selected_team
    r_row = ratings[ratings["Team"] == t_name].iloc[0]
    f_row = forecasts[forecasts["Team"] == t_name].iloc[0]

    st.divider()
    st.header(f"🏀 {r_row['Team and Record']} — {str(r_row['Conference']).upper()}")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("MPI Rank", f"#{int(r_row['Rank'])}")
    m2.metric("MPI", f"{r_row['MPI']:+.2f}")
    m3.metric("Off. Eff.", f"{r_row['Off. Eff.']:+.2f}")
    m4.metric("Def. Eff.", f"{r_row['Def. Eff.']:+.2f}")
    m5.metric("WAB", f"{r_row['WAB']:+.2f}")
    m6.metric("SOS (Win %)", f"{r_row['SOS']:.3f}")

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Quality Wins (Top 40)", str(r_row["Quality Wins"]))
    p2.metric("Projected W-L", str(f_row["Proj. W-L"]))
    p3.metric("Proj. Conf. W-L", str(f_row["Proj. Conf. W-L"]))
    p4.metric("% to Win Conf.", f"{f_row['% to Win Conf.']:.1f}%")
    p5.metric("% March Madness", f"{f_row['% to Make March Madness']:.1f}%")

    st.subheader("📅 2026–27 Game Log & Results")
    t_games = game_info[(game_info["home_team"] == t_name) | (game_info["away_team"] == t_name)].copy()

    if t_games.empty:
        st.info("No completed games logged yet for this team.")
    else:
        mpi_lookup = dict(zip(ratings["Team"], ratings["Rank"]))
        log_rows = []
        for _, g in t_games.sort_values("date").iterrows():
            is_home = g["home_team"] == t_name
            opp = g["away_team"] if is_home else g["home_team"]
            loc = "vs." if is_home else "@"
            t_pts = int(g["home_score"] if is_home else g["away_score"])
            o_pts = int(g["away_score"] if is_home else g["home_score"])
            res = "W" if t_pts > o_pts else "L"
            opp_rk = f"#{int(mpi_lookup[opp])}" if opp in mpi_lookup else "Non-D1"
            log_rows.append({"Date": g["date"], "Location": loc, "Opponent": f"{opp} ({opp_rk})", "Result": res, "Score": f"{t_pts}-{o_pts}"})
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)
    st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Metrics (MPI & WAB)", "🎲 Season Forecasts", "🏆 Bracketology", "📅 Daily Game Projections"])

with tab1:
    st.subheader("Team Efficiency & Resume Metrics")
    col1, col2 = st.columns(2)
    with col1:
        confs = ["All Conferences"] + sorted(ratings["Conference"].dropna().unique().tolist())
        selected_conf = st.selectbox("Filter by Conference:", confs, key="metrics_conf")
    with col2:
        search_team = st.text_input("Search Team:", placeholder="e.g., Duke, Kansas, Gonzaga...")

    view_df = ratings.copy()
    if selected_conf != "All Conferences":
        view_df = view_df[view_df["Conference"] == selected_conf]
    if search_team:
        view_df = view_df[view_df["Team and Record"].str.contains(search_team, case=False, na=False)]

    display_cols = ["Rank", "Team and Record", "MPI", "Off. Eff.", "Def. Eff.", "WAB", "SOS", "Quality Wins"]
    st.dataframe(view_df[display_cols], use_container_width=True, hide_index=True, height=600)

with tab2:
    st.subheader("Monte Carlo Season Forecasts (5,000 Simulations)")
    f_confs = ["All Conferences"] + sorted(forecasts["Conference"].dropna().unique().tolist())
    f_conf = st.selectbox("Filter by Conference:", f_confs, key="forecast_conf")
    f_view = forecasts.copy()
    if f_conf != "All Conferences":
        f_view = f_view[f_view["Conference"] == f_conf]

    f_cols = ["Rank", "Team and Record", "MPI", "Proj. W-L", "Proj. Conf. W-L", "% to Win Conf.", "% to Make March Madness"]
    st.dataframe(f_view[f_cols], use_container_width=True, hide_index=True, height=600)

with tab3:
    st.subheader("NCAA Tournament 76-Team Bracketology (2027 Format)")
    bracket_mode = st.radio("Select Bracket View:", ["Current Bracket (Based on Current Resume & MPI)", "Projected Bracket (Based on Season Simulations)"], horizontal=True)
    b_df = pd.read_csv("data/bracket_current.csv") if "Current" in bracket_mode else pd.read_csv("data/bracket_projected.csv")

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.info("**Opening Round (12 At-Large Play-In Teams):**\n\n" + "\n".join(f"- {t}" for t in b_df[b_df["Bubble Status"].str.contains("Opening Round (At-Large", regex=False, na=False)]["Team and Record"]))
    with b_col2:
        st.warning("**First Four Out (#77–#80):**\n\n" + "\n".join(f"- {t}" for t in b_df[b_df["Bubble Status"].str.contains("First Four Out", na=False)]["Team and Record"]))

    reg_tabs = st.tabs(["All Seeds (1-76)", "East", "South", "Midwest", "West"])
    with reg_tabs[0]:
        st.dataframe(b_df, use_container_width=True, hide_index=True, height=650)

    for idx, region_name in enumerate(["East", "South", "Midwest", "West"], start=1):
        with reg_tabs[idx]:
            reg_df = b_df[b_df["Region"] == region_name].sort_values("Seed")
            st.dataframe(reg_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Today's Slate: Game-by-Game Projections")
    daily = pd.read_csv("data/daily_projections.csv")
    st.dataframe(daily, use_container_width=True, hide_index=True, height=650)
