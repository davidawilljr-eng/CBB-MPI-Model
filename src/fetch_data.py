from concurrent.futures import ThreadPoolExecutor
import datetime
import time
import pandas as pd
import requests

NCAA_BASE = "https://ncaa-api." + "henrygd.me"


def fetch_boxscore(game):
    """Fetches box score totals for a single completed game from NCAA API."""
    gid = game["game_id"]
    try:
        url = f"{NCAA_BASE}/game/{gid}/boxscore"
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()

        # Map teamId -> short team name
        id_to_name = {}
        for t in data.get("teams", []):
            tid = str(t.get("teamId", ""))
            id_to_name[tid] = t.get("nameShort", "")

        rows = []
        for tb in data.get("teamBoxscore", []):
            tid = str(tb.get("teamId", ""))
            team_name = id_to_name.get(tid, "")
            if not team_name:
                continue

            # Sum player stats for exact team totals
            fga, oreb, to, fta, pts = 0.0, 0.0, 0.0, 0.0, 0
            for p in tb.get("playerStats", []):
                fga += float(p.get("fieldGoalsAttempted") or 0)
                oreb += float(p.get("offensiveRebounds") or 0)
                to += float(p.get("turnovers") or 0)
                fta += float(p.get("freeThrowsAttempted") or 0)
                pts += int(p.get("points") or 0)

            # Fallback to teamStats object if playerStats is empty
            if fga == 0 and tb.get("teamStats"):
                ts = tb["teamStats"]
                fga = float(ts.get("fieldGoalsAttempted") or 0)
                oreb = float(ts.get("offensiveRebounds") or 0)
                to = float(ts.get("turnovers") or 0)
                fta = float(ts.get("freeThrowsAttempted") or 0)

            possessions = fga - oreb + to + (0.475 * fta)
            rows.append(
                {
                    "game_id": gid,
                    "team": team_name,
                    "pts": pts,
                    "possessions": round(possessions, 2),
                }
            )
        return rows
    except Exception:
        return []


def parse_scoreboard_date(date_obj, include_upcoming=False):
    """Pulls completed (or upcoming) games and conference info for a single date."""
    url = f"{NCAA_BASE}/scoreboard/basketball-men/d1/{date_obj.strftime('%Y/%m/%d')}"
    resp = requests.get(url, timeout=12)
    if resp.status_code != 200:
        return [], {}

    data = resp.json()
    games = []
    conf_map = {}

    for item in data.get("games", []):
        g = item.get("game", {})
        state = g.get("gameState", "")
        if not include_upcoming and state != "final":
            continue

        home = g.get("home", {})
        away = g.get("away", {})
        home_name = home.get("names", {}).get("short", "")
        away_name = away.get("names", {}).get("short", "")
        if not home_name or not away_name:
            continue

        # Capture conference tag for each team
        for side, name in [(home, home_name), (away, away_name)]:
            confs = side.get("conferences", [])
            if confs:
                c_seo = confs[0].get("conferenceSeo", "")
                if c_seo:
                    conf_map[name] = c_seo

        games.append(
            {
                "game_id": str(g.get("gameID", "")),
                "date": date_obj.strftime("%Y-%m-%d"),
                "home_team": home_name,
                "away_team": away_name,
                "home_score": int(home.get("score") or 0),
                "away_score": int(away.get("score") or 0),
                "neutral_site": False,
                "game_state": state,
                "start_time": g.get("startTime", ""),
            }
        )
    return games, conf_map


def fetch_season_data():
    print("🏀 Fetching 2026-27 College Basketball data via NCAA API...")
    start_date = datetime.date(2026, 11, 2)
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    all_games = []
    all_confs = {}

    curr = start_date
    while curr <= yesterday:
        day_games, day_confs = parse_scoreboard_date(
            curr, include_upcoming=False
        )
        all_games.extend(day_games)
        all_confs.update(day_confs)
        print(
            f"📅 {curr.strftime('%Y-%m-%d')}: Found {len(day_games)} completed games"
        )
        time.sleep(0.15)
        curr += datetime.timedelta(days=1)

    # Also grab today's slate for Daily Game Projections
    todays_games, today_confs = parse_scoreboard_date(
        today, include_upcoming=True
    )
    all_confs.update(today_confs)
    pd.DataFrame(todays_games).to_csv("data/todays_games.csv", index=False)
    print(
        f"📆 Saved {len(todays_games)} games on today's slate ({today.strftime('%Y-%m-%d')})"
    )

    # Save conference mappings
    conf_df = pd.DataFrame(
        [{"team": k, "conference": v} for k, v in all_confs.items()]
    )
    conf_df.to_csv("data/team_conferences.csv", index=False)

    # Save game info
    info_df = pd.DataFrame(all_games)
    info_df.to_csv("data/game_info.csv", index=False)

    print(
        f"⚡ Pulling box scores for {len(info_df)} completed games in parallel..."
    )
    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(fetch_boxscore, all_games))

    all_stats = [row for game_rows in results for row in game_rows]
    stats_df = pd.DataFrame(all_stats)
    stats_df.to_csv("data/team_game_stats.csv", index=False)

    print(
        f"✅ Success! Saved {len(info_df)} games and {len(stats_df)} team box scores!"
    )


if __name__ == "__main__":
    fetch_season_data()
