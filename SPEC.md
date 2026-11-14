# Project: College Basketball MPI Analytics & Bracketology Suite

## Overview
Build a modular Python pipeline and interactive Streamlit web app that calculates tempo-free opponent-adjusted efficiency ratings (MPI), resume metrics (WAB, SOS, Quality Wins), Monte Carlo season simulations, daily game projections, and a 68-team NCAA Tournament bracket.

## Tech Stack
- **Language:** Python 3.11+
- **Data & Math:** `pandas`, `numpy`, `scipy`
- **Data Fetching:** `cbbpy` or `requests`/`BeautifulSoup` (pulling current D1 men's basketball schedules, box scores, and conference affiliations)
- **Frontend:** `streamlit`
- **Automation:** GitHub Actions workflow (`.github/workflows/daily_update.yml`) to run the data pipeline daily at 11:00 UTC (6:00 AM EST).

## Folder Structure
1. `data/` - Stores processed CSVs (`ratings.csv`, `forecasts.csv`, `daily_projections.csv`, `bracket_current.csv`, `bracket_projected.csv`).
2. `src/fetch_data.py` - Pulls all D1 games played to date and remaining scheduled games, including possessions (`FGA - OR + TO + 0.475 * FTA`), location (Home/Away/Neutral), and conference tags.
3. `src/ratings.py` - Calculates iterative opponent-adjusted metrics and resume stats.
4. `src/simulations.py` - Runs 10,000 Monte Carlo simulations of remaining regular-season and conference tournament games.
5. `src/bracketology.py` - Builds both the Current Bracket and Projected Bracket using NCAA selection rules (31 automatic conference qualifiers + 37 at-large bids, seeded 1-16).
6. `app.py` - Multi-page Streamlit web application displaying the tables and interactive toggles.

## Mathematical Specifications

### 1. Metrics Table (`ratings.csv`)
- **Possessions & Pace:** Calculate possessions per game; compute team Adjusted Tempo.
- **Offensive & Defensive Efficiency (Points Above Average):** Use an iterative adjustment loop (20 iterations) adjusting for opponent strength and Home Court Advantage (~3.2 pts/100 poss). Express `Off_Eff` as points scored per 100 possessions *above* national average (positive = better) and `Def_Eff` as points allowed per 100 possessions *below* national average (positive = better defense).
- **MPI (My Power Index):** `Off_Eff + Def_Eff` (net efficiency points above average per 100 possessions).
- **Strength of Schedule (SOS):** Identify the "Bubble Baseline MPI" by averaging the MPI of teams ranked #42 through #48. For every game a team has played so far, calculate the win probability of that Bubble Baseline team against that opponent (accounting for game location) using a Normal CDF (`std_dev = 11.0`). Sum these probabilities to get `Expected_Bubble_Wins`. Lower score = harder schedule.
- **WAB (Wins Above Bubble):** `Actual_Wins - Expected_Bubble_Wins`.
- **Quality Wins:** Team's W-L record specifically in games played against opponents currently ranked in the MPI Top 40.
- **Columns to output:** `Rank`, `Team & Record`, `MPI`, `Off. Eff.`, `Def. Eff.`, `WAB`, `SOS`, `Quality Wins`.

### 2. Forecasts Table (`forecasts.csv`)
- Run 10,000 Monte Carlo simulations of all remaining scheduled games using win probabilities derived from `MPI` difference, expected game pace, and Home Court Advantage.
- **Columns to output:** `Rank`, `Team & Record`, `MPI`, `Proj. W-L`, `Proj. Conf. W-L`, `% to Win Conf.`, `% to Make March Madness`.

### 3. Bracketology (`bracket_current.csv` & `bracket_projected.csv`)
- Rank teams using a composite of MPI and WAB (resume + predictive).
- Award 31 Automatic Bids to the highest-ranked team (or simulated tournament winner) in each D1 conference.
- Award 37 At-Large Bids to the highest-ranked remaining teams.
- Seed teams 1 through 68 across four regions (1–16 seeds, plus First Four play-in games for the last four at-large teams and bottom four auto-bids).

### 4. Streamlit Web App (`app.py`)
Create a clean sidebar or top navigation with 4 pages:
- **Page 1: Metrics** (Interactive sortable dataframe of `ratings.csv` with conference filter).
- **Page 2: Forecasts** (Interactive sortable dataframe of `forecasts.csv`).
- **Page 3: Bracketology** (Includes a prominent toggle switch: `Current Bracket` vs. `Projected Bracket`, displaying seeds 1–16 by region plus "Last Four In" and "First Four Out").
- **Page 4: Daily Game Projections** (Displays today's slate of games with projected winner, projected spread, win probability %, and predicted total score).
