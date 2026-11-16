import numpy as np
import pandas as pd
from scipy.stats import norm

AVG_PACE = 68.5
HCA_PTS = 3.2
NAT_AVG_EFF = 105.0
STD_DEV = 11.0


def predict_matchup(
    home_team, away_team, mpi_map, off_map, def_map, neutral=False
):
    """Calculates expected spread, win probability, and projected scores for a single game."""
    h_mpi = mpi_map.get(home_team, 0.0)
    a_mpi = mpi_map.get(away_team, 0.0)
    hca = 0.0 if neutral else HCA_PTS

    exp_margin = ((h_mpi - a_mpi) * (AVG_PACE / 100.0)) + hca
    home_win_prob = float(norm.cdf(exp_margin / STD_DEV))

    h_off = off_map.get(home_team, 0.0)
    h_def = def_map.get(home_team, 0.0)
    a_off = off_map.get(away_team, 0.0)
    a_def = def_map.get(away_team, 0.0)

    h_pts = (
        (NAT_AVG_EFF + h_off - a_def) * (AVG_PACE / 100.0) + (hca / 2.0)
    )
    a_pts = (
        (NAT_AVG_EFF + a_off - h_def) * (AVG_PACE / 100.0) - (hca / 2.0)
    )

    return round(exp_margin, 1), home_win_prob, round(h_pts), round(a_pts)


def run_simulations(n_sims=5000):
    print("🎲 Building Daily Projections & Running 5,000 Season Simulations (76-Team Field)...")
    ratings = pd.read_csv("data/ratings.csv")
    todays_games = pd.read_csv("data/todays_games.csv")

    mpi_map = dict(zip(ratings["Team"], ratings["MPI"]))
    off_map = dict(zip(ratings["Team"], ratings["Off. Eff."]))
    def_map = dict(zip(ratings["Team"], ratings["Def. Eff."]))

    rec_split = ratings["Team and Record"].str.extract(r"\((\d+)-(\d+)\)")
    ratings["cur_w"] = rec_split.iloc[:, 0].astype(int)
    ratings["cur_l"] = rec_split.iloc[:, 1].astype(int)

    # 1. DAILY GAME PROJECTIONS
    daily_rows = []
    for _, g in todays_games.iterrows():
        h_team = g["home_team"]
        a_team = g["away_team"]
        margin, h_prob, h_pts, a_pts = predict_matchup(
            h_team, a_team, mpi_map, off_map, def_map
        )

        if margin >= 0:
            fav = h_team
            spread = f"-{abs(margin):.1f}"
            win_prob = round(h_prob * 100, 1)
        else:
            fav = a_team
            spread = f"-{abs(margin):.1f}"
            win_prob = round((1.0 - h_prob) * 100, 1)

        daily_rows.append(
            {
                "Time (ET)": g.get("start_time", ""),
                "Away Team": a_team,
                "Home Team": h_team,
                "Projected Winner": fav,
                "Spread": f"{fav} {spread}",
                "Win Prob %": win_prob,
                "Projected Score": f"{a_team} {a_pts} - {h_team} {h_pts}",
            }
        )

    daily_df = pd.DataFrame(daily_rows)
    daily_df.to_csv("data/daily_projections.csv", index=False)
    print(f"📅 Saved {len(daily_df)} game projections to data/daily_projections.csv")

    # 2. MONTE CARLO SEASON SIMULATIONS WITH RATING DRIFT
    rng = np.random.default_rng(42)
    teams = ratings["Team"].tolist()
    n_teams = len(teams)
    team_to_idx = {t: i for i, t in enumerate(teams)}

    rem_games = []
    non_conf_games = [int(ratings.loc[i, "cur_w"] + ratings.loc[i, "cur_l"]) for i in range(n_teams)]
    for i in range(n_teams):
        attempts = 0
        while non_conf_games[i] < 13 and attempts < 80:
            attempts += 1
            opp_idx = int(rng.integers(0, n_teams))
            if opp_idx != i and non_conf_games[opp_idx] < 13 and ratings.loc[i, "Conference"] != ratings.loc[opp_idx, "Conference"]:
                rem_games.append((i, opp_idx, False, True))
                non_conf_games[i] += 1
                non_conf_games[opp_idx] += 1

    for conf, group in ratings.groupby("Conference"):
        c_indices = [team_to_idx[t] for t in group["Team"]]
        if len(c_indices) < 2:
            continue
        for i in range(len(c_indices)):
            for step in range(1, 10):
                opp = c_indices[(i + step) % len(c_indices)]
                if opp != c_indices[i]:
                    rem_games.append((c_indices[i], opp, True, False))

    home_list, away_list, conf_list, neut_list = zip(*rem_games)
    home_idx = np.array(home_list)
    away_idx = np.array(away_list)
    is_conf = np.array(conf_list)
    is_neut = np.array(neut_list)

    # Simulate season-long form drift (+/- 3.8 MPI std dev for injuries, slumps, or breakouts)
    base_mpis = ratings["MPI"].values
    sim_mpis = base_mpis + rng.normal(0.0, 3.8, size=(n_sims, n_teams))

    hca_vec = np.where(is_neut, 0.0, HCA_PTS)
    margins = (
        (sim_mpis[:, home_idx] - sim_mpis[:, away_idx]) * (AVG_PACE / 100.0)
    ) + hca_vec
    win_probs = norm.cdf(margins / STD_DEV)

    rand_draws = rng.random((n_sims, len(rem_games)))
    home_wins = rand_draws < win_probs

    total_w = np.tile(ratings["cur_w"].values, (n_sims, 1))
    total_l = np.tile(ratings["cur_l"].values, (n_sims, 1))
    conf_w = np.zeros((n_sims, n_teams), dtype=int)
    conf_l = np.zeros((n_sims, n_teams), dtype=int)

    np.add.at(total_w, (slice(None), home_idx), home_wins)
    np.add.at(total_l, (slice(None), home_idx), ~home_wins)
    np.add.at(total_w, (slice(None), away_idx), ~home_wins)
    np.add.at(total_l, (slice(None), away_idx), home_wins)

    conf_mask = is_conf
    np.add.at(conf_w, (slice(None), home_idx[conf_mask]), home_wins[:, conf_mask])
    np.add.at(conf_l, (slice(None), home_idx[conf_mask]), ~home_wins[:, conf_mask])
    np.add.at(conf_w, (slice(None), away_idx[conf_mask]), ~home_wins[:, conf_mask])
    np.add.at(conf_l, (slice(None), away_idx[conf_mask]), home_wins[:, conf_mask])

    auto_bids = np.zeros((n_sims, n_teams), dtype=bool)
    for conf, group in ratings.groupby("Conference"):
        c_idx = np.array([team_to_idx[t] for t in group["Team"]])
        tourney_chaos = rng.normal(0.0, 3.8, size=(n_sims, len(c_idx)))
        c_scores = conf_w[:, c_idx] + (sim_mpis[:, c_idx] * 0.25) + tourney_chaos
        winners = c_idx[np.argmax(c_scores, axis=1)]
        auto_bids[np.arange(n_sims), winners] = True
        # Add Conference Tournament games (3 wins for champ; 1-2 games for others; NO March Madness games)
        for idx_in_c, t_global in enumerate(c_idx):
            is_champ = (winners == t_global)
            advances_r1 = (~is_champ) & (rng.random(n_sims) < np.clip(0.35 + (sim_mpis[:, t_global] - 0.0) * 0.015, 0.10, 0.75))
            total_w[:, t_global] += np.where(is_champ, 3, np.where(advances_r1, 1, 0))
            total_l[:, t_global] += np.where(is_champ, 0, 1)

    # 76-Team Format: 32 Auto-Bids + Top 44 At-Large Teams
    sim_resume = total_w + (sim_mpis * 0.45)
    sim_resume_masked = np.where(auto_bids, -9999.0, sim_resume)
    at_large_idx = np.argpartition(-sim_resume_masked, 44, axis=1)[:, :44]

    in_tourney = auto_bids.copy()
    in_tourney[np.arange(n_sims)[:, None], at_large_idx] = True

    avg_w = np.round(total_w.mean(axis=0)).astype(int)
    avg_l = np.round(total_l.mean(axis=0)).astype(int)
    avg_cw = np.round(conf_w.mean(axis=0)).astype(int)
    avg_cl = np.round(conf_l.mean(axis=0)).astype(int)

    # Cap display odds between 0.1% and 99.9%
    conf_win_pct = np.clip(np.round(auto_bids.mean(axis=0) * 100, 1), 0.1, 99.9)
    tourney_pct = np.clip(np.round(in_tourney.mean(axis=0) * 100, 1), 0.1, 99.9)

    forecasts = pd.DataFrame(
        {
            "Rank": ratings["Rank"],
            "Team and Record": ratings["Team and Record"],
            "Conference": ratings["Conference"],
            "MPI": ratings["MPI"],
            "Proj. W-L": [f"{w}-{l}" for w, l in zip(avg_w, avg_l)],
            "Proj. Conf. W-L": [f"{w}-{l}" for w, l in zip(avg_cw, avg_cl)],
            "% to Win Conf.": conf_win_pct,
            "% to Make March Madness": tourney_pct,
        }
    )
    forecasts.to_csv("data/forecasts.csv", index=False)
    print("✅ Saved data/forecasts.csv! Top 15 March Madness Odds:")
    print(
        forecasts.sort_values("% to Make March Madness", ascending=False)
        .head(15)
        .to_string(index=False)
    )


if __name__ == "__main__":
    run_simulations()
