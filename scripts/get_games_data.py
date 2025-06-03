#!/usr/bin/env python3
"""
Overview:
  This script scrapes game and player statistics from basketball-reference.com for a specified date range.
  It fetches data from daily score pages and individual game box score pages, then stores the
  extracted information into a SQLite database.

Dependencies:
  - requests: For making HTTP requests to fetch web page content.
  - beautifulsoup4: For parsing HTML content.
  - sqlite3: For database interaction (part of standard Python library).
  - logging: For progress and error logging (part of standard Python library).
  - os: For directory creation (part of standard Python library).
  - sys: For exiting script on critical errors (part of standard Python library).
  - datetime: For date manipulation (part of standard Python library).
  - argparse: For command-line argument parsing (part of standard Python library).

  Install external dependencies using:
    pip install -r requirements.txt
  (requirements.txt should contain 'requests' and 'beautifulsoup4')

How to Run:
  The script is executed from the command line, providing a start and end date,
  and an optional rate limit.

  Command-line usage:
    python scripts/scrape_bball_reference.py --start_date YYYY-MM-DD --end_date YYYY-MM-DD [--qps QPS_VALUE]

  Arguments:
    --start_date YYYY-MM-DD : The first date to scrape (inclusive).
    --end_date YYYY-MM-DD   : The last date to scrape (inclusive).
    --qps QPS_VALUE         : (Optional) Queries Per Second to limit the request rate.
                              For example, `--qps 0.5` means 1 request every 2 seconds.
                              If not provided, no rate limiting is applied.

  Example:
    python scripts/scrape_bball_reference.py --start_date 2023-10-24 --end_date 2023-10-26 --qps 1
    python scripts/scrape_bball_reference.py --start_date 2023-11-01 --end_date 2023-11-01

  The start and end dates are inclusive.

Database Schema:
  The script creates a SQLite database file at `data/bball_data.db`.
  The database contains two main tables: `games` and `player_stats`.
  The `data/` directory is created automatically if it doesn't exist.

  `games` table:
    - id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for each game.
    - game_date (TEXT): Date of the game in YYYY-MM-DD format.
    - home_team (TEXT): Name of the home team.
    - away_team (TEXT): Name of the away team.
    - home_score (INTEGER): Final score of the home team.
    - away_score (INTEGER): Final score of the away team.
    - box_score_url (TEXT UNIQUE): URL of the game's box score page. This is used to prevent
                                   duplicate entries for the same game.

  `player_stats` table:
    - id (INTEGER PRIMARY KEY AUTOINCREMENT): Unique identifier for each player stat entry.
    - game_id (INTEGER): Foreign key referencing the `id` in the `games` table, linking
                         the player's stats to a specific game.
    - player_name (TEXT): Name of the player.
    - team (TEXT): Abbreviation of the team the player played for in this game (e.g., "LAL", "GSW").
    - mp (TEXT): Minutes Played (e.g., "35:12"). Stored as text as it's not always a simple number.
    - fg (INTEGER): Field Goals Made.
    - fga (INTEGER): Field Goal Attempts.
    - fg_pct (REAL): Field Goal Percentage (e.g., 0.450). Calculated as FG/FGA.
    - fg3 (INTEGER): 3-Point Field Goals Made.
    - fg3a (INTEGER): 3-Point Field Goal Attempts.
    - fg3_pct (REAL): 3-Point Field Goal Percentage. Calculated as 3P/3PA.
    - ft (INTEGER): Free Throws Made.
    - fta (INTEGER): Free Throw Attempts.
    - ft_pct (REAL): Free Throw Percentage. Calculated as FT/FTA.
    - orb (INTEGER): Offensive Rebounds.
    - drb (INTEGER): Defensive Rebounds.
    - trb (INTEGER): Total Rebounds.
    - ast (INTEGER): Assists.
    - stl (INTEGER): Steals.
    - blk (INTEGER): Blocks.
    - tov (INTEGER): Turnovers.
    - pf (INTEGER): Personal Fouls.
    - pts (INTEGER): Points Scored.
    - plus_minus (TEXT): Plus/Minus statistic (e.g., "+5", "-12"). Can be empty if not available
                         or if the player did not play. Stored as text due to the '+' sign.

Logging:
  - The script logs its progress and any errors encountered.
  - Logs are saved to a file at `logs/scraper.log`.
  - Log messages are also printed to the console.
  - The `data/` and `logs/` directories are created automatically by the script if they do not
    already exist.
"""

import argparse
import datetime
# import requests # No longer directly used in main
# from bs4 import BeautifulSoup # No longer directly used in main
import sqlite3
import os
import bball_ref_scraper_lib # Import the new library
import logging
import sys
import time # Import time module

# Configure logging
def setup_logging():
    """Sets up logging to file and console."""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'scraper.log')

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)

def init_db(db_name='bball_data.db'):
    """Initializes the database and creates tables if they don't exist."""
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, db_name)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create games table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_date TEXT,
        home_team TEXT,
        away_team TEXT,
        home_score INTEGER,
        away_score INTEGER,
        box_score_url TEXT UNIQUE
    )
    ''')

    # Create player_stats table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        player_name TEXT,
        team TEXT,
        mp TEXT,
        fg INTEGER,
        fga INTEGER,
        fg_pct REAL,
        fg3 INTEGER,
        fg3a INTEGER,
        fg3_pct REAL,
        ft INTEGER,
        fta INTEGER,
        ft_pct REAL,
        orb INTEGER,
        drb INTEGER,
        trb INTEGER,
        ast INTEGER,
        stl INTEGER,
        blk INTEGER,
        tov INTEGER,
        pf INTEGER,
        pts INTEGER,
        plus_minus TEXT,
        FOREIGN KEY (game_id) REFERENCES games (id)
    )
    ''')

    # Create player_of_the_month table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_of_the_month (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT,
        team_abbreviation TEXT,
        month_numeric INTEGER,
        year_numeric INTEGER,
        conference TEXT,
        league_name TEXT,
        source_url TEXT,
        UNIQUE (player_name, month_numeric, year_numeric, conference, league_name)
    )
    ''')

    # Create player_of_the_week table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_of_the_week (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT,
        team_abbreviation TEXT,
        week_start_date TEXT,
        week_end_date TEXT,
        conference TEXT,
        league_name TEXT,
        source_url TEXT,
        UNIQUE (player_name, week_start_date, week_end_date, conference, league_name)
    )
    ''')

    # Create rookie_of_the_month table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rookie_of_the_month (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT,
        team_abbreviation TEXT,
        month_numeric INTEGER,
        year_numeric INTEGER,
        conference TEXT,
        league_name TEXT,
        source_url TEXT,
        UNIQUE (player_name, month_numeric, year_numeric, conference, league_name)
    )
    ''')

    # Create coach_of_the_month table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS coach_of_the_month (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coach_name TEXT,
        team_abbreviation TEXT,
        month_numeric INTEGER,
        year_numeric INTEGER,
        conference TEXT,
        league_name TEXT,
        source_url TEXT,
        UNIQUE (coach_name, team_abbreviation, month_numeric, year_numeric, conference, league_name)
    )
    ''')

    conn.commit()
    logging.info(f"Database initialized at {db_path}")
    return conn

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scrape basketball-reference.com for box score links within a date range.")
    parser.add_argument("--start_date", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument('--qps', type=float, default=None, help='Queries per second (e.g., 0.5 for 1 request every 2 seconds). If not provided, no rate limiting is applied.')
    return parser.parse_args()

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + datetime.timedelta(n)

# Helper Functions Start

def setup_rate_limiting(qps_arg):
    """Sets up rate limiting based on QPS argument."""
    delay_seconds = 0
    if qps_arg is not None:
        if qps_arg > 0:
            delay_seconds = 1.0 / qps_arg
            logging.info(f"Rate limiting enabled: {qps_arg} QPS. Delay between requests: {delay_seconds:.2f} seconds.")
        else:
            logging.warning("Invalid QPS value. QPS must be greater than 0. Proceeding without rate limiting.")
    else:
        logging.info("No rate limiting applied.")
    return delay_seconds

def fetch_and_parse_daily_page(daily_page_url, delay_seconds):
    """Fetches and parses the daily games page to find box score URLs."""
    logging.info(f"Fetching daily page: {daily_page_url}")
    if delay_seconds > 0:
        logging.debug(f"Applying rate limit delay: {delay_seconds:.2f} seconds before fetching daily page: {daily_page_url}")
        time.sleep(delay_seconds)
    daily_soup = bball_ref_scraper_lib.get_soup(daily_page_url)

    if not daily_soup:
        # get_soup already logs the error
        return []

    box_score_urls_found = list(bball_ref_scraper_lib.parse_daily_games_page(daily_soup, daily_page_url))
    logging.info(f"Found {len(box_score_urls_found)} game(s) from {daily_page_url}.")
    return box_score_urls_found

def insert_game_into_db(db_cursor, game_date_str, game_data, box_score_url):
    """Inserts a game into the database and returns the game_id."""
    game_id_to_insert = None
    try:
        db_cursor.execute('''
            INSERT INTO games (game_date, home_team, away_team, home_score, away_score, box_score_url)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(box_score_url) DO NOTHING
        ''', (game_date_str, game_data['home_team'], game_data['away_team'], game_data['home_score'], game_data['away_score'], box_score_url))

        # Regardless of conflict, get the game_id
        db_cursor.execute("SELECT id FROM games WHERE box_score_url = ?", (box_score_url,))
        game_id_row = db_cursor.fetchone()
        if game_id_row:
            game_id_to_insert = game_id_row[0]
        else:
            logging.error(f"    CRITICAL: Failed to retrieve game_id for {box_score_url} even after insert attempt. Skipping player stats.")
            return None
    except sqlite3.Error as e:
        logging.error(f"    Database error processing game {box_score_url}: {e}")
        return None
    return game_id_to_insert

def insert_player_stats_into_db(db_cursor, game_id, players_data_list, box_score_url):
    """Inserts player stats for a given game_id into the database."""
    current_game_players_inserted = 0
    for player_stat_data in players_data_list:
        player_stat_data["game_id"] = game_id
        try:
            expected_keys = ["game_id", "player_name", "team", "mp", "fg", "fga", "fg_pct", "fg3", "fg3a",
                             "fg3_pct", "ft", "fta", "ft_pct", "orb", "drb", "trb", "ast", "stl",
                             "blk", "tov", "pf", "pts", "plus_minus"]
            values_to_insert = [player_stat_data.get(key) for key in expected_keys]
            columns = ', '.join(expected_keys)
            placeholders = ', '.join(['?'] * len(expected_keys))
            sql = f"INSERT INTO player_stats ({columns}) VALUES ({placeholders})"
            db_cursor.execute(sql, values_to_insert)
            current_game_players_inserted += 1
        except sqlite3.Error as e:
            logging.error(f"    Database error inserting player stats for {player_stat_data.get('player_name', 'Unknown Player')} in game ID {game_id} ({box_score_url}): {e}")
        except KeyError as e:
            logging.error(f"    Missing expected key {e} in player data for {player_stat_data.get('player_name', 'Unknown Player')} in game {box_score_url}")
    return current_game_players_inserted

def process_single_box_score(box_score_url, game_date_str, db_conn, db_cursor, delay_seconds):
    """Processes a single box score URL, fetches data, and stores it in the DB."""
    game_processed_flag = False
    players_inserted_count_for_game = 0

    logging.info(f"  Fetching box score: {box_score_url}")
    if delay_seconds > 0:
        logging.debug(f"Applying rate limit delay: {delay_seconds:.2f} seconds before fetching box score: {box_score_url}")
        time.sleep(delay_seconds)
    box_score_soup = bball_ref_scraper_lib.get_soup(box_score_url)
    if not box_score_soup:
        return False, 0 # game_processed_flag = False, players_inserted_count_for_game = 0

    game_data = bball_ref_scraper_lib.parse_box_score_page(box_score_soup, box_score_url)

    if not game_data or not game_data.get("home_team") or not game_data.get("away_team"):
        logging.error(f"    Could not parse critical game data (e.g. team names) from {box_score_url}. Skipping database insertion.")
        return False, 0

    game_id = insert_game_into_db(db_cursor, game_date_str, game_data, box_score_url)

    if not game_id:
        # Error already logged by insert_game_into_db
        return False, 0

    players_inserted_count_for_game = insert_player_stats_into_db(db_cursor, game_id, game_data.get("players", []), box_score_url)

    if players_inserted_count_for_game > 0:
        db_conn.commit()
        logging.info(f"    Successfully inserted/updated game (ID: {game_id}) and inserted {players_inserted_count_for_game} player stat records for {box_score_url}.")
        game_processed_flag = True
    elif game_id: # Game existed or was inserted, but no new players were added
        db_conn.commit() # Commit game insertion even if no players
        logging.info(f"    Game (ID: {game_id}) processed for {box_score_url}. No new player stats were added.")
        # To count a game as "processed" even if no new players, if it was successfully inserted/found
        game_processed_flag = True # Set to true if the game itself was handled.

    return game_processed_flag, players_inserted_count_for_game

def process_date(date_obj, db_conn, db_cursor, delay_seconds):
    """Processes all games for a single date."""
    single_date_str = date_obj.strftime('%Y-%m-%d')
    month = date_obj.strftime("%m")
    day = date_obj.strftime("%d")
    year = date_obj.strftime("%Y")
    daily_page_url = f"https://www.basketball-reference.com/boxscores/?month={month}&day={day}&year={year}"

    logging.info(f"Processing date: {single_date_str}, URL: {daily_page_url}")
    box_score_urls = fetch_and_parse_daily_page(daily_page_url, delay_seconds)

    if not box_score_urls:
        logging.info(f"No games found or error fetching for date {single_date_str}.")
        return 0, 0

    games_processed_today = 0
    players_inserted_today = 0

    for box_score_url in box_score_urls:
        game_processed, players_in_game = process_single_box_score(box_score_url, single_date_str, db_conn, db_cursor, delay_seconds)
        if game_processed: # If game was processed (even if no new players, but game itself was handled)
            games_processed_today += 1
        players_inserted_today += players_in_game

    return games_processed_today, players_inserted_today

# Helper Functions End

def main():
    setup_logging()
    logging.info("Script started.")
    args = parse_arguments()

    delay_seconds = setup_rate_limiting(args.qps)

    total_games_processed = 0
    total_players_inserted = 0

    db_conn = init_db()
    if not db_conn:
        logging.error("Failed to initialize database. Exiting.")
        sys.exit(1) # Critical error, exit script

    db_cursor = db_conn.cursor()

    try:
        start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()
    except ValueError:
        logging.error("Error: Dates must be in YYYY-MM-DD format. Please check input arguments.")
        if db_conn: # Ensure DB connection is closed before exiting
            db_conn.close()
        sys.exit(1)

    if start_date > end_date:
        logging.error("Error: Start date cannot be after end date.")
        if db_conn: # Ensure DB connection is closed before exiting
            db_conn.close()
        sys.exit(1)

    for single_date_obj in daterange(start_date, end_date):
        games_today, players_today = process_date(single_date_obj, db_conn, db_cursor, delay_seconds)
        total_games_processed += games_today
        total_players_inserted += players_today

    if db_conn:
        db_conn.close()
        logging.info("Database connection closed.")

    logging.info(f"Script finished. Successfully processed and stored data for {total_games_processed} games and inserted {total_players_inserted} player stat records.")

if __name__ == "__main__":
    main()
