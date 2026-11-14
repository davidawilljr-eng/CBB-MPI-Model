import numpy as np
import pandas as pd
from scipy.stats import norm

D1_CONFERENCES = {
    "acc", "sec", "big-ten", "big-12", "big-east", "pac-12",
    "mountain-west", "wcc", "atlantic-10", "american", "mvc",
    "cusa", "mac", "sun-belt", "wac", "uac-", "big-sky",
    "big-south", "big-west", "caa", "horizon", "ivy-league",
    "metro", "maac", "meac", "nec", "ovc", "patriot",
    "socon", "southland", "summit-league", "swac", "america-east", "asun"
}

# Realistic Conference Strength Priors (MPI points above/below D1 average)
CONF_PRIORS = {
    "sec": 10.5,
    "big-ten": 10.0,
    "big-12": 10.5,
    "acc": 8.5,
    "big-east": 8.5,
    "mountain-west": 3.5,
    "wcc": 2.5,
    "atlantic-10": 2.0,
    "pac-12": 2.5,
    "american": 1.0,
    "mvc": 1.0,
    "ivy-league": -1.5,
    "cusa": -2.0,
    "sun-belt": -2.5,
    "mac": -3.0,
    "caa": -3.5,
    "big-west": -3.5,
    "wac": -3.5,
    "uac-": -4.0,
    "horizon": -4.5,
    "socon": -4.5,
    "big-sky": -5.5,
    "summit-league": -5.5,
    "asun": -6.0,
    "big-south": -6.5,
    "metro": -6.5,
    "maac": -6.5,
    "ovc": -7.5,
    "patriot": -7.5,
    "america-east": -8.0,
    "southland": -8.5,
    "nec": -10.5,
    "swac": -11.5,
    "meac": -12.0,
}

# Preseason Top-25 / Elite Program Boosts (on top of conference prior)
TEAM_BOOSTS = {
    "Duke": 14.0, "Kansas": 13.5, "UConn": 13.5, "Houston": 13.5,
    "Florida": 12.5, "Alabama": 12.5, "Auburn": 12.0, "Iowa St.": 12.0,
    "Purdue": 11.5, "Arizona": 11.5, "Gonzaga": 16.5, "Michigan St.": 11.0,
    "North Carolina": 11.0, "Kentucky": 11.0, "Tennessee": 11.0,
    "Baylor": 10.5, "Marquette": 10.0, "Creighton": 9.5, "Illinois": 10.0,
    "Texas": 9.5, "Indiana": 9.0, "Arkansas": 9.5, "UCLA": 9.5,
    "St. John's": 9.5, "BYU": 9.0, "Texas Tech": 9.0, "Louisville": 8.5,
    "Michigan": 8.5, "Ohio St.": 8.0, "Wisconsin": 8.0, "Xavier": 8.0,
    "Saint Mary's": 12.0, "San Diego St.": 9.5, "Memphis": 9.5,
    "New Mexico": 8.5, "Boise St.": 8.0, "Utah St.": 7.5, "Dayton": 8.5,
    "VCU": 8.0, "Virginia": 8.0, "Clemson": 7.5, "Miami (FL)": 7.5,
    "Ole Miss": 7.5, "Texas A&M": 8.0, "Missouri": 7.0, "Vanderbilt": 6.5,
    "Villanova": 7.5, "Cincinnati": 7.5, "TCU": 7.0, "Oklahoma": 7.0,
}


def build_ratings():
    print("📊 Calculating Calibrated MPI with Preseason & Conference Priors...")
    info_df = pd.read_csv("data/game_info.csv")
    stats_df = pd.read_csv("data/team_game_stats.csv")
    conf_df = pd.read_csv("data/team_conferences.csv")

    conf_df = conf_df[conf_df["conference"].isin(D1_CONFERENCES)].copy()
    conf_map = dict(zip(conf_df["team"], conf_df["conference"]))

    home_rows = pd.DataFrame(
        {
            "game_id": info_df["game_id"].astype(str),
            "date": info_df["date"],
            "team_team": info_df["home_team"],
            "team_opp": info_df["away_team"],
            "pts_team": info_df["home_score"],
            "pts_opp": info_df["away_score"],
            "is_home": 1,
            "neutral_site": info_df["neutral_site"].fillna(False).astype(bool),
        }
    )
    away_rows = pd.DataFrame(
        {
            "game_id": info_df["game_id"].astype(str),
            "date": info_df["date"],
            "team_team": info_df["away_team"],
            "team_opp": info_df["home_team"],
            "pts_team": info_df["away_score"],
            "pts_opp": info_df["home_score"],
            "is_home": 0,
            "neutral_site": info_df["neutral_site"].fillna(False).astype(bool),
        }
    )
    df = pd.concat([home_rows, away_rows], ignore_index=True)

    if not stats_df.empty:
        stats_df["game_id"] = stats_df["game_id"].astype(str)
        game_poss = (
            stats_df.groupby("game_id")["possessions"].mean().to_dict()
        )
        df["poss"] = df["game_id"].map(game_poss)
    else:
        df["poss"] = np.nan

    est_poss = (df["pts_team"] + df["pts_opp"]) / (2.0 * 1.05)
    df["poss"] = df["poss"].fillna(est_poss).clip(lower=45.0, upper=95.0)

    df["raw_oe"] = (df["pts_team"] / df["poss"]) * 100.0
    df["raw_de"] = (df["pts_opp"] / df["poss"]) * 100.0
    df["win"] = (df["pts_team"] > df["pts_opp"]).astype(int)

    # Diminishing returns on huge blowouts (> 22 pts per 100 poss)
    margin = df["raw_oe"] - df["raw_de"]
    excess = np.maximum(0.0, np.abs(margin) - 22.0)
    capped_margin = np.where(
        np.abs(margin) > 22.0,
        np.sign(margin) * (22.0 + np.log1p(excess) * 3.0),
        margin,
    )
    mid_pts = (df["raw_oe"] + df["raw_de"]) / 2.0
    df["raw_oe"] = mid_pts + (capped_margin / 2.0)
    df["raw_de"] = mid_pts - (capped_margin / 2.0)

    HCA = 3.2
    df["hca_adj"] = 0.0
    df.loc[~df["neutral_site"] & (df["is_home"] == 1), "hca_adj"] = HCA
    df.loc[~df["neutral_site"] & (df["is_home"] == 0), "hca_adj"] = -HCA

    d1_teams = sorted(list(set(df["team_team"]).intersection(set(conf_map.keys()))))
    df = df[
        df["team_team"].isin(d1_teams) & df["team_opp"].isin(d1_teams)
    ].copy()

    nat_avg = df["raw_oe"].mean()
    teams = pd.DataFrame({"Team": d1_teams})

    # Build team-specific Preseason Prior (split evenly between Offense & Defense)
    prior_oe = {}
    prior_de = {}
    for t in d1_teams:
        c_prior = CONF_PRIORS.get(conf_map.get(t, ""), -3.0)
        t_boost = TEAM_BOOSTS.get(t, 0.0)
        total_prior = c_prior + t_boost
        prior_oe[t] = nat_avg + (total_prior / 2.0)
        prior_de[t] = nat_avg - (total_prior / 2.0)

    adj_oe = prior_oe.copy()
    adj_de = prior_de.copy()

    # Prior weight = 8 games (naturally fades out as teams play 20-30 games)
    PRIOR_GAMES = 8.0

    for _ in range(25):
        df["opp_de"] = df["team_opp"].map(adj_de)
        df["opp_oe"] = df["team_opp"].map(adj_oe)

        df["adj_game_oe"] = (
            df["raw_oe"] - (df["opp_de"] - nat_avg) - (df["hca_adj"] / 2.0)
        )
        df["adj_game_de"] = (
            df["raw_de"] - (df["opp_oe"] - nat_avg) + (df["hca_adj"] / 2.0)
        )

        grouped = df.groupby("team_team").agg(
            sum_oe=("adj_game_oe", "sum"),
            sum_de=("adj_game_de", "sum"),
            n_games=("adj_game_oe", "count"),
        )

        new_oe, new_de = {}, {}
        for t in d1_teams:
            if t in grouped.index:
                n = grouped.loc[t, "n_games"]
                s_oe = grouped.loc[t, "sum_oe"]
                s_de = grouped.loc[t, "sum_de"]
                new_oe[t] = (s_oe + PRIOR_GAMES * prior_oe[t]) / (n + PRIOR_GAMES)
                new_de[t] = (s_de + PRIOR_GAMES * prior_de[t]) / (n + PRIOR_GAMES)
            else:
                new_oe[t] = prior_oe[t]
                new_de[t] = prior_de[t]

        mean_oe = np.mean(list(new_oe.values()))
        mean_de = np.mean(list(new_de.values()))
        for t in d1_teams:
            adj_oe[t] = new_oe[t] - (mean_oe - nat_avg)
            adj_de[t] = new_de[t] - (mean_de - nat_avg)

    teams["Conference"] = teams["Team"].map(conf_map)
    teams["Off. Eff."] = teams["Team"].map(
        lambda t: round(adj_oe[t] - nat_avg, 2)
    )
    teams["Def. Eff."] = teams["Team"].map(
        lambda t: round(nat_avg - adj_de[t], 2)
    )
    teams["MPI"] = (teams["Off. Eff."] + teams["Def. Eff."]).round(2)

    teams = teams.sort_values("MPI", ascending=False).reset_index(drop=True)
    teams["Rank"] = teams.index + 1
    bubble_mpi = teams.iloc[41:48]["MPI"].mean()
    top_40_teams = set(teams.iloc[:40]["Team"])
    mpi_map = dict(zip(teams["Team"], teams["MPI"]))

    records, sos_list, wab_list, qw_list = [], [], [], []
    for team in teams["Team"]:
        t_games = df[df["team_team"] == team]
        wins = int(t_games["win"].sum())
        losses = int(len(t_games) - wins)
        records.append(f"{wins}-{losses}")

        exp_bubble_wins = 0.0
        for _, row in t_games.iterrows():
            opp_mpi = mpi_map[row["team_opp"]]
            exp_margin = (bubble_mpi - opp_mpi) * 0.68 + row["hca_adj"]
            win_prob = norm.cdf(exp_margin / 11.0)
            exp_bubble_wins += win_prob

        sos_list.append(round(exp_bubble_wins, 2))
        wab_list.append(round(wins - exp_bubble_wins, 2))

        q_games = t_games[t_games["team_opp"].isin(top_40_teams)]
        q_wins = int(q_games["win"].sum())
        q_losses = int(len(q_games) - q_wins)
        qw_list.append(f"{q_wins}-{q_losses}")

    teams["Team and Record"] = teams["Team"] + " (" + pd.Series(records) + ")"
    teams["WAB"] = wab_list
    teams["SOS"] = sos_list
    teams["Quality Wins"] = qw_list

    teams.to_csv("data/ratings.csv", index=False)
    print("✅ Saved calibrated data/ratings.csv! New Top 15:")
    print(
        teams[
            ["Rank", "Team and Record", "MPI", "Off. Eff.", "Def. Eff.", "WAB", "Quality Wins"]
        ]
        .head(15)
        .to_string(index=False)
    )


if __name__ == "__main__":
    build_ratings()
