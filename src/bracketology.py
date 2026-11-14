import pandas as pd


def generate_single_bracket(df, score_col, auto_bid_col, out_path):
    """Builds the official 76-team NCAA tournament bracket (32 Auto-Bids + 44 At-Large) + First Four Out."""
    work = df.copy()
    work = work.sort_values(score_col, ascending=False).reset_index(drop=True)

    # 1. Pick 32 Automatic Qualifiers (1 per D1 conference, including Pac-12)
    auto_teams = set()
    for conf, group in work.groupby("Conference"):
        best_team = group.sort_values(auto_bid_col, ascending=False).iloc[0]["Team"]
        auto_teams.add(best_team)

    work["Bid Type"] = work["Team"].apply(
        lambda t: "Auto-Bid" if t in auto_teams else "At-Large"
    )

    # 2. Pick top 44 At-Large teams (to reach 76 total teams)
    auto_df = work[work["Bid Type"] == "Auto-Bid"].copy()
    at_large_pool = work[work["Bid Type"] == "At-Large"].copy()

    # Trim auto_df to 32 in case of extra conference tag variants
    auto_df = auto_df.sort_values(score_col, ascending=False).iloc[:32].copy()
    at_large_in = at_large_pool.iloc[:44].copy()
    first_four_out = at_large_pool.iloc[44:48].copy()

    # Combine 76-team field and sort by overall seed list (1 to 76)
    field = (
        pd.concat([auto_df, at_large_in], ignore_index=True)
        .sort_values(score_col, ascending=False)
        .reset_index(drop=True)
    )
    field["Overall Seed"] = field.index + 1

    # Official 2027 Opening Round: Lowest 12 At-Large + Lowest 12 Auto-Bids (24 teams -> 12 games)
    opening_at_large = set(field[field["Bid Type"] == "At-Large"].tail(12)["Team"])
    opening_auto = set(field[field["Bid Type"] == "Auto-Bid"].tail(12)["Team"])

    # Assign 1-16 Seed Lines & S-Curve Regions (top 52 get byes to Round of 64; 24 play in Opening Round)
    regions = ["East", "South", "Midwest", "West"]
    seed_lines = []
    region_list = []
    notes = []

    for idx, row in field.iterrows():
        t_name = row["Team"]
        if t_name in opening_at_large:
            seed = 11
            reg = regions[idx % 4]
            note = "Opening Round (At-Large Play-In)"
        elif t_name in opening_auto:
            seed = 16
            reg = regions[idx % 4]
            note = "Opening Round (Auto-Bid Play-In)"
        else:
            # 52 direct Round-of-64 entrants mapped cleanly across seeds 1-15
            seed = min(15, (idx // 4) + 1)
            reg = regions[idx % 4] if (idx // 4) % 2 == 0 else regions[3 - (idx % 4)]
            note = ""

        seed_lines.append(seed)
        region_list.append(reg)
        notes.append(note)

    field["Seed"] = seed_lines
    field["Region"] = region_list
    field["Bubble Status"] = notes

    # Append First Four Out (#77 to #80)
    first_four_out["Overall Seed"] = range(77, 77 + len(first_four_out))
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
    print("🏆 Building Current & Projected 76-Team Brackets (2027 Format)...")
    ratings = pd.read_csv("data/ratings.csv")
    forecasts = pd.read_csv("data/forecasts.csv")

    if "Team" not in forecasts.columns:
        forecasts["Team"] = forecasts["Team and Record"].str.replace(
            r"\s*\(\d+-\d+\)$", "", regex=True
        )

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
        ],
        on="Team",
    )

    merged["Current_Score"] = merged["MPI"] + (merged["WAB"] * 2.5)
    generate_single_bracket(
        merged,
        score_col="Current_Score",
        auto_bid_col="Current_Score",
        out_path="data/bracket_current.csv",
    )

    proj_w = merged["Proj. W-L"].str.split("-").str.get(0).astype(float)
    merged["Projected_Score"] = (
        merged["MPI"]
        + (proj_w * 0.4)
        + (merged["% to Make March Madness"] * 0.05)
    )
    generate_single_bracket(
        merged,
        score_col="Projected_Score",
        auto_bid_col="% to Win Conf.",
        out_path="data/bracket_projected.csv",
    )

    print("✅ Saved 76-team brackets to data/bracket_current.csv & data/bracket_projected.csv!")


if __name__ == "__main__":
    build_brackets()
