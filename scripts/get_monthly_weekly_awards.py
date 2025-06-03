#!/usr/bin/env python3
"""
Overview:
  This script scrapes monthly and weekly awards (Player of the Month,
  Player of the Week, Rookie of the Month, Coach of the Month) from
  basketball-reference.com for specified seasons and stores them in a SQLite database.

Dependencies:
  - requests: For making HTTP requests.
  - beautifulsoup4: For parsing HTML.
  - sqlite3: For database interaction.
  - logging, os, argparse, datetime: Standard Python libraries.
  - bball_ref_scraper_lib: For get_soup and award parsing helper utilities.

How to Run:
  python scripts/get_monthly_weekly_awards.py --start_year YYYY --end_year YYYY [--qps QPS_VALUE] [--db_file DB_PATH]

Arguments:
  --start_year YYYY : The first season to scrape (e.g., 2022 for 2022-2023 season). Required.
  --end_year YYYY   : The last season to scrape (e.g., 2023 for 2023-2024 season). Required.
  --qps QPS_VALUE   : (Optional) Queries Per Second.
  --db_file DB_PATH : (Optional) Path to SQLite database. Default: data/bball_data.db
"""

import sqlite3
import logging
import os
import argparse
import time
from datetime import datetime
import sys

import requests
from bs4 import BeautifulSoup

try:
    from bball_ref_scraper_lib import get_soup, get_month_numeric, get_award_year, parse_week_date_range
    LIB_FUNCTIONS_IMPORTED = True
    # Logging will be set up in main, so initial info log might not be visible unless main is called.
except ImportError as e:
    LIB_FUNCTIONS_IMPORTED = False
    # Temporary basic logging for critical import error
    print(f"CRITICAL: Failed to import helper functions from bball_ref_scraper_lib: {e}. Ensure it's in PYTHONPATH and functions are defined. Script functionality will be severely impaired.", file=sys.stderr)
    # Define dummy functions if import fails
    def get_soup(url, retries=3, delay=5): print(f"DUMMY get_soup called for URL: {url}", file=sys.stderr); return None
    def get_month_numeric(month_str): print(f"DUMMY get_month_numeric called for {month_str}", file=sys.stderr); return None
    def get_award_year(season_str, month_numeric, award_month_text_for_log, award_name_for_log): print(f"DUMMY get_award_year for {season_str}, {month_numeric}", file=sys.stderr); return None
    def parse_week_date_range(week_str, season_start_year, current_row_for_log): print(f"DUMMY parse_week_date_range for {week_str}", file=sys.stderr); return None, None

AWARD_URLS = {
    "pom": "https://www.basketball-reference.com/awards/pom.html",
    "pow": "https://www.basketball-reference.com/awards/pow.html",
    "rom": "https://www.basketball-reference.com/awards/rom.html",
    "com": "https://www.basketball-reference.com/awards/com.html",
}

def setup_logging():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'awards_scraper.log')
    root_logger = logging.getLogger()
    if not root_logger.hasHandlers():
        root_logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s'))
        root_logger.addHandler(file_handler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(console_handler)
    logging.info("Logging configured.")


def init_db(db_path='data/bball_data.db'):
    data_dir = os.path.dirname(db_path)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, game_date TEXT, home_team TEXT, away_team TEXT, home_score INTEGER, away_score INTEGER, box_score_url TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS player_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, game_id INTEGER, player_name TEXT, team TEXT, mp TEXT, fg INTEGER, fga INTEGER, fg_pct REAL, fg3 INTEGER, fg3a INTEGER, fg3_pct REAL, ft INTEGER, fta INTEGER, ft_pct REAL, orb INTEGER, drb INTEGER, trb INTEGER, ast INTEGER, stl INTEGER, blk INTEGER, tov INTEGER, pf INTEGER, pts INTEGER, plus_minus TEXT, FOREIGN KEY (game_id) REFERENCES games (id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS player_of_the_month (id INTEGER PRIMARY KEY AUTOINCREMENT, player_name TEXT, team_abbreviation TEXT, month_numeric INTEGER, year_numeric INTEGER, conference TEXT, league_name TEXT, source_url TEXT, UNIQUE (player_name, month_numeric, year_numeric, conference, league_name))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS player_of_the_week (id INTEGER PRIMARY KEY AUTOINCREMENT, player_name TEXT, team_abbreviation TEXT, week_start_date TEXT, week_end_date TEXT, conference TEXT, league_name TEXT, source_url TEXT, UNIQUE (player_name, week_start_date, week_end_date, conference, league_name))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS rookie_of_the_month (id INTEGER PRIMARY KEY AUTOINCREMENT, player_name TEXT, team_abbreviation TEXT, month_numeric INTEGER, year_numeric INTEGER, conference TEXT, league_name TEXT, source_url TEXT, UNIQUE (player_name, month_numeric, year_numeric, conference, league_name))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS coach_of_the_month (id INTEGER PRIMARY KEY AUTOINCREMENT, coach_name TEXT, team_abbreviation TEXT, month_numeric INTEGER, year_numeric INTEGER, conference TEXT, league_name TEXT, source_url TEXT, UNIQUE (coach_name, team_abbreviation, month_numeric, year_numeric, conference, league_name))''')
    conn.commit()
    logging.info(f"Database initialized at {db_path}")
    return conn

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scrape basketball-reference.com for monthly/weekly awards.")
    parser.add_argument("--start_year", type=int, required=True, help="Start season year (e.g., 2022 for 2022-23 season).")
    parser.add_argument("--end_year", type=int, required=True, help="End season year (e.g., 2023 for 2023-24 season).")
    parser.add_argument('--qps', type=float, default=None, help='Queries per second.')
    parser.add_argument('--db_file', type=str, default='data/bball_data.db', help='Path to SQLite database file.')
    return parser.parse_args()

def setup_rate_limiting(qps_arg):
    delay_seconds = 0
    if qps_arg is not None:
        if qps_arg > 0: delay_seconds = 1.0 / qps_arg; logging.info(f"Rate limiting: {qps_arg} QPS, delay: {delay_seconds:.2f}s.")
        else: logging.warning("Invalid QPS (>0). No rate limiting.")
    else: logging.info("No rate limiting.")
    return delay_seconds

def find_award_table(soup, award_type_for_log, potential_selectors):
    """Iterates through potential CSS selectors to find the awards table."""
    if not soup: return None
    for i, selector in enumerate(potential_selectors):
        logging.debug(f"For {award_type_for_log}, trying selector {i+1}: '{selector}'")
        table = soup.select_one(selector)
        if table:
            # Ensure what's returned is a TABLE element, as select_one could return a parent div
            if table.name != 'table':
                if table.find('table'): # If the selector found a div, look for a table within it
                    table = table.find('table')
                else:
                    logging.warning(f"Selector '{selector}' for {award_type_for_log} found element <{table.name}>, not <table> and no child table.")
                    continue # Try next selector
            logging.info(f"Table found for {award_type_for_log} using selector: '{selector}'")
            return table
    logging.error(f"No table found for {award_type_for_log} after trying all selectors: {potential_selectors}")
    return None

def scrape_monthly_award(db_conn, award_type, base_url, qps_delay, start_season_year, end_season_year, potential_selectors, name_field):
    award_name_log = award_type.upper().replace("_", " ") # Make it more readable
    logging.info(f"Scraping {award_name_log} from {base_url}")
    if qps_delay > 0: time.sleep(qps_delay)
    soup = get_soup(base_url)
    if not soup: logging.error(f"No soup from {base_url} for {award_name_log}."); return 0

    table = find_award_table(soup, award_name_log, potential_selectors)
    if not table: return 0 # Error already logged by find_award_table

    inserted_count = 0
    cursor = db_conn.cursor()
    for row in table.find_all("tr"):
        if row.find("th", scope="col"): continue
        cells = row.find_all("td")
        if not cells or len(cells) < 6:
            if row.get_text(strip=True): logging.warning(f"Skipping row with <6 cells or no cells for {award_name_log}: {row.get_text(strip=True)[:100]}")
            continue
        try:
            season_str = cells[0].get_text(strip=True)
            league_name = cells[1].get_text(strip=True)
            entity_name_tag = cells[2].find("a")
            entity_name = entity_name_tag.get_text(strip=True) if entity_name_tag else cells[2].get_text(strip=True)
            conf = cells[3].get_text(strip=True)
            month_str = cells[4].get_text(strip=True)
            team_abbr_tag = cells[5].find("a")
            team_abbr = team_abbr_tag.get_text(strip=True) if team_abbr_tag else cells[5].get_text(strip=True)

            current_season_start_year = int(season_str.split("-")[0])
            if not (start_season_year <= current_season_start_year <= end_season_year): continue

            month_numeric = get_month_numeric(month_str)
            if month_numeric is None: logging.warning(f"Unknown month '{month_str}' for {award_name_log} {entity_name}, season {season_str}. Skipping."); continue

            year_numeric = get_award_year(season_str, month_numeric, month_str, f"{award_name_log} for {entity_name}")
            if year_numeric is None: continue

            if league_name != "NBA": logging.debug(f"Skipping non-NBA {award_name_log} for {entity_name}"); continue

            sql_table_name = award_type # Passed as e.g. "player_of_the_month"
            sql_name_field = name_field # Passed as "player_name" or "coach_name"

            conflict_fields_list = [sql_name_field, "month_numeric", "year_numeric", "conference", "league_name"]
            if award_type == "coach_of_the_month": # Coach unique constraint includes team
                 conflict_fields_list.insert(1, "team_abbreviation")
            conflict_fields = ", ".join(conflict_fields_list)

            cursor.execute(f"""
                INSERT INTO {sql_table_name} ({sql_name_field}, team_abbreviation, month_numeric, year_numeric, conference, league_name, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT({conflict_fields}) DO NOTHING
            """, (entity_name, team_abbr, month_numeric, year_numeric, conf if conf else None, league_name, base_url))

            if cursor.rowcount > 0: inserted_count += 1; logging.debug(f"Inserted {award_name_log}: {year_numeric}-{month_numeric:02d} {conf}, {entity_name}, {team_abbr}")
        except Exception as e:
            logging.error(f"Error parsing row for {award_name_log} {row.get_text(strip=True)[:100]}: {e}")
            import traceback; logging.error(traceback.format_exc())
    db_conn.commit()
    logging.info(f"Finished {award_name_log}. Inserted {inserted_count} new records.")
    return inserted_count

def scrape_player_of_the_week(db_conn, base_url, qps_delay, start_season_year, end_season_year, potential_selectors):
    award_name_log = "PLAYER OF THE WEEK"
    logging.info(f"Scraping {award_name_log} from {base_url}")
    if qps_delay > 0: time.sleep(qps_delay)
    soup = get_soup(base_url)
    if not soup: logging.error(f"No soup from {base_url} for {award_name_log}."); return 0

    table = find_award_table(soup, award_name_log, potential_selectors)
    if not table: return 0

    inserted_count = 0
    cursor = db_conn.cursor()
    current_processing_season_start_year = None

    for row in table.find_all("tr"):
        if row.find("th", scope="col"): continue
        season_header = row.find("th", {"data-stat": "season"})
        if season_header and season_header.get_text(strip=True):
            try: current_processing_season_start_year = int(season_header.get_text(strip=True).split("-")[0])
            except ValueError: logging.warning(f"Could not parse season from {award_name_log} header: {season_header.get_text(strip=True)}")
            continue
        cells = row.find_all("td")
        if len(cells) < 5:
            if cells and "season" in cells[0].get("class",[]): continue
            if row.get_text(strip=True): logging.warning(f"Skipping row with <5 cells for {award_name_log}: {row.get_text(strip=True)[:100]}")
            continue
        try:
            season_str_in_row = None
            effective_season_start_year = current_processing_season_start_year
            data_offset = 0
            first_cell_text = cells[0].get_text(strip=True)
            if first_cell_text and ("-" in first_cell_text or "–" in first_cell_text) and first_cell_text.replace('-', '').replace('–','').isdigit():
                try:
                    effective_season_start_year = int(first_cell_text.split("-")[0].split("–")[0])
                    season_str_in_row = first_cell_text
                    data_offset = 1
                    if len(cells) < data_offset + 5:
                         logging.warning(f"Skipping row with season in first cell but <{data_offset+5} total cells for {award_name_log}: {row.get_text(strip=True)[:100]}")
                         continue
                except ValueError:
                    logging.debug(f"First cell '{first_cell_text}' not a season year for {award_name_log}, assuming inherited season.")

            if effective_season_start_year is None: logging.warning(f"Season year undetermined for {award_name_log} row: {row.get_text(strip=True)[:100]}. Skipping."); continue
            if not (start_season_year <= effective_season_start_year <= end_season_year): continue

            league_name = cells[data_offset + 0].get_text(strip=True)
            week_str = cells[data_offset + 1].get_text(strip=True)
            player_name_tag = cells[data_offset + 2].find("a")
            player_name = player_name_tag.get_text(strip=True) if player_name_tag else cells[data_offset + 2].get_text(strip=True)
            conf = cells[data_offset + 3].get_text(strip=True)
            team_abbr_tag = cells[data_offset + 4].find("a")
            team_abbr = team_abbr_tag.get_text(strip=True) if team_abbr_tag else cells[data_offset + 4].get_text(strip=True)

            if league_name != "NBA": continue

            log_context = f"{award_name_log} for {player_name}, season {effective_season_start_year} (row season: {season_str_in_row or 'implied'})"
            week_start_date_str, week_end_date_str = parse_week_date_range(week_str, effective_season_start_year, log_context)
            if not week_start_date_str or not week_end_date_str: logging.warning(f"Skipping {award_name_log} for {player_name} due to unparseable week string '{week_str}'."); continue

            cursor.execute("""
                INSERT INTO player_of_the_week (player_name, team_abbreviation, week_start_date, week_end_date, conference, league_name, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_name, week_start_date, week_end_date, conference, league_name) DO NOTHING
            """, (player_name, team_abbr, week_start_date_str, week_end_date_str, conf if conf else None, league_name, base_url))
            if cursor.rowcount > 0: inserted_count += 1; logging.debug(f"Inserted {award_name_log}: {player_name} ({week_start_date_str} to {week_end_date_str})")
        except Exception as e:
            logging.error(f"Error parsing row for {award_name_log} {row.get_text(strip=True)[:150]}: {e}")
            import traceback; logging.error(traceback.format_exc())
    db_conn.commit()
    logging.info(f"Finished {award_name_log}. Inserted {inserted_count} new records.")
    return inserted_count

def main():
    setup_logging()

    if not LIB_FUNCTIONS_IMPORTED:
        logging.critical("One or more library functions failed to import at script start. Script cannot function correctly.")
        sys.exit(1)

    logging.info("Award Scraper Script started.")
    args = parse_arguments()

    if args.start_year > args.end_year: logging.error("Start year cannot be after end year."); sys.exit(1)
    qps_delay = setup_rate_limiting(args.qps)
    try: db_conn = init_db(args.db_file)
    except Exception as e: logging.critical(f"Failed to initialize database: {e}"); sys.exit(1)

    # Define selector lists for each award type
    # Using CSS selectors: '#' for ID, '.' for class, ' ' for descendant
    # These are educated guesses and might need refinement after viewing live HTML.
    pom_selectors = [
        "div#all_awards_NBA_POM table#awards_NBA_POM", # Highly specific
        "table#awards_NBA_POM",
        "div#all_pom table#pom", # Simpler variant
        "table#pom",
        "div#all_awards table#awards", # More generic div wrapper with 'awards' table
        "table#awards", # Generic 'awards' table ID
        "table" # Last resort: first table on page
    ]
    pow_selectors = [
        "div#all_awards_NBA_POW table#awards_NBA_POW",
        "table#awards_NBA_POW",
        "div#all_pow table#pow",
        "table#pow",
        "div#all_awards table#awards",
        "table#awards",
        "table"
    ]
    rom_selectors = [
        "div#all_awards_NBA_ROM table#awards_NBA_ROM",
        "table#awards_NBA_ROM",
        "div#all_rom table#rom",
        "table#rom",
        "div#all_awards table#awards",
        "table#awards",
        "table"
    ]
    cotm_selectors = [
        "div#all_awards_NBA_COTM table#awards_NBA_COTM",
        "table#awards_NBA_COTM",
        "div#all_com table#com",
        "table#com",
        "div#all_awards table#awards",
        "table#awards",
        "table"
    ]

    totals = {"pom": 0, "pow": 0, "rom": 0, "com": 0}
    try:
        totals["pom"] = scrape_monthly_award(db_conn, "player_of_the_month", AWARD_URLS["pom"], qps_delay, args.start_year, args.end_year, pom_selectors, "player_name")
        totals["pow"] = scrape_player_of_the_week(db_conn, AWARD_URLS["pow"], qps_delay, args.start_year, args.end_year, pow_selectors)
        totals["rom"] = scrape_monthly_award(db_conn, "rookie_of_the_month", AWARD_URLS["rom"], qps_delay, args.start_year, args.end_year, rom_selectors, "player_name")
        totals["com"] = scrape_monthly_award(db_conn, "coach_of_the_month", AWARD_URLS["com"], qps_delay, args.start_year, args.end_year, cotm_selectors, "coach_name")
    except Exception as e:
        logging.critical(f"Unhandled error during scraping: {e}")
        import traceback; logging.error(traceback.format_exc())
    finally:
        if db_conn: db_conn.close(); logging.info("Database connection closed.")
    logging.info(f"Script finished. POM={totals['pom']}, POW={totals['pow']}, ROM={totals['rom']}, COM={totals['com']}")

if __name__ == "__main__":
    main()
