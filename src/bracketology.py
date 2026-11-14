import pandas as pd


def generate_single_bracket(df, score_col, auto_bid_col, out_path):
    """Builds a 68-team NCAA tournament bracket + First Four Out."""
    work = df.copy()
    work = work.sort_values(score_col, ascending=False).reset_index(drop=True)

    # 1. Pick 31 Automatic Qualifiers (1 per D1 conference)
    auto_teams = set()
    for conf, group in work.groupby("Conference"):
        best_team = group.sort_values(auto_bid_col, ascending=False).iloc[0]["Team"]
        auto_teams.add(best_team)

    work["Bid Type"] = work["Team"].apply(
        lambda t: "Auto-Bid" if t in auto_teams else "At-Large"
    )

    # 2. Pick top 37 At-Large teams
    auto_df = work[work["Bid Type"] == "Auto-Bid"].copy()
    at_large_pool = work[work["Bid Type"] == "At-Large"].copy()

    at_large_in = at_large_pool.iloc[:37].copy()
    first_four_out = at_large_pool.iloc[37:41].copy()

    # Combine 68-team field and sort by overall seed list (1 to 68)
    field = (
        pd.concat([auto_df, at_large_in], ignore_index=True)
        .sort_values(score_col, ascending=False)
        .reset_index(drop=True)
    )
    field["Overall Seed"] = field.index + 1

    # Identify Last Four In (lowest 4 At-Large seeds)
    last_four_at_large = set(
        field[field["Bid Type"] == "At-Large"].tail(4)["Team"]
    )

    # Assign 1-16 Seed Lines & S-Curve Regions
    regions = ["East", "South", "Midwest", "West"]
    seed_lines = []
    region_list = []
    notes = []

    for idx, row in field.iterrows():
        # Standard 1-16 seed grouping (4 teams per seed line, extra 4 on 11 & 16 for First Four)
        if idx < 40:
            seed = (idx // 4) + 1
            reg = regions[idx % 4] if (idx // 4) % 2 == 0 else regions[3 - (idx % 4)]
        elif idx < 46:
            seed = 11
            reg = regions[(idx - 40) % 4]
        elif idx < 62:
            seed = ((idx - 46) // 4) + 12
            reg = regions[(idx - 46) % 4]
        else:
            seed = 16
            reg = regions[(idx - 62) % 4]

        seed_lines.append(seed)
        region_list.append(reg)
        notes.append("Last Four In (First Four)" if row["Team"] in last_four_at_large else "")

    field["Seed"] = seed_lines
    field["Region"] = region_list
    field["Bubble Status"] = notes

    # Append First Four Out at the bottom for easy display
    first_four_out["Overall Seed"] = range(69, 73)
    first_four_out["Seed"] = "-"
    first_four_out["Region"] = "-"
    first_four_out["Bubble Status"] = "First Four Out"

    full_out = pd.concat([field, first_four_out], ignore_index=True)
    cols = [
        "Overall Seed",
        "Seed",
        "Region",
        "Team and Record",
        "Conference",
        "Bid Type",
        "MPI",
        "WAB",
        "Bubble Status",
    ]
    full_out[cols].to_csv(out_path, index=False)
    return full_out[cols]


def build_brackets():
    print("🏆 Building Current & Projected 68-Team Brackets...")
    ratings = pd.read_csv("data/ratings.csv")
    forecasts = pd.read_csv("data/forecasts.csv")

    merged = pd.merge(
        ratings,
        forecasts[
            [
                "Team",
                "Proj. W-L",
                "Proj. Conf. W-L",
                "% to Win Conf.",
                "% to Make March Madness",
            ]
        ]
        if "Team" in forecasts.columns
        else forecasts.assign(
            Team=forecasts["Team and Record"].str.replace(
                r"\s*\(\d+-\d+\)$", "", regex=True
            )
        )[
            [
                "Team",
                "Proj. W-L",
                "Proj. Conf. W-L",
                "% to Win Conf.",
                "% to Make March Madness",
            ]
        ],
        on="Team",
    )

    # Current Bracket Score: Blends current MPI + WAB resume
    merged["Current_Score"] = merged["MPI"] + (merged["WAB"] * 2.5)
    curr_df = generate_single_bracket(
        merged,
        score_col="Current_Score",
        auto_bid_col="Current_Score",
        out_path="data/bracket_current.csv",
    )

    # Projected Bracket Score: Blends MPI + Projected Season Wins + Tourney Odds
    proj_w = merged["Proj. W-L"].str.split("-").str.get(0).astype(float)
    merged["Projected_Score"] = (
        merged["MPI"]
        + (proj_w * 0.4)
        + (merged["% to Make March Madness"] * 0.05)
    )
    proj_df = generate_single_bracket(
        merged,
        score_col="Projected_Score",
        auto_bid_col="% to Win Conf.",
        out_path="data/bracket_projected.csv",
    )

    print("✅ Saved data/bracket_current.csv & data/bracket_projected.csv!")
    print("\n--- Current #1 Seeds ---")
    print(curr_df.head(4).to_string(index=False))
    print("\n--- Projected #1 Seeds ---")
    print(proj_df.head(4).to_string(index=False))


if __name__ == "__main__":
    build_brackets()
