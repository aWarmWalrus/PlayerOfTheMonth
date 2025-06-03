import requests
from bs4 import BeautifulSoup
import logging

# Configure logger for the library
logger = logging.getLogger(__name__)

def get_soup(url, timeout=10):
    """Fetches URL and returns a BeautifulSoup object or None on error."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return None

def _get_cell_text(element, data_stat, player_name_for_log, game_url_for_log):
    """Helper function to safely get cell text or None. Logs warning if not found."""
    cell = element.find('td', attrs={"data-stat": data_stat})
    text_val = cell.text.strip() if cell and cell.text.strip() else None
    if text_val is None:
        logger.warning(f"Stat [{data_stat}] not found for player [{player_name_for_log}] in game [{game_url_for_log}]")
    return text_val

def _to_int(value, stat_name, player_name_for_log, game_url_for_log):
    """Helper function to convert to int or None. Logs warning on failure."""
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Could not convert stat [{stat_name}] value '{value}' to INTEGER for player [{player_name_for_log}] in game [{game_url_for_log}]")
        return None

def _to_real(value, stat_name, player_name_for_log, game_url_for_log):
    """Helper function to convert to real or None. Logs warning on failure."""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Could not convert stat [{stat_name}] value '{value}' to REAL for player [{player_name_for_log}] in game [{game_url_for_log}]")
        return None

def parse_daily_games_page(soup, daily_url):
    """
    Parses the HTML content of a daily games page to find box score links.
    Yields full box score URLs.
    """
    if not soup:
        logger.warning(f"No soup object provided for parsing daily games page: {daily_url}")
        return

    game_links_found = 0
    # Updated selector: looking for <a> tags directly within td.gamelink (or td.gamelink descendants)
    # that have "/boxscores/" in their href.
    selector_used = 'td.gamelink a[href*="/boxscores/"]'
    logger.info(f"Using selector: '{selector_used}' for daily games page {daily_url}")

    for game_link_tag in soup.select(selector_used):
        href = game_link_tag.get('href', '')
        # Ensure it's a box score link and not a play-by-play or other sub-page link
        # The main check is '/boxscores/' and ending with '.html'
        # Additional checks for common sub-pages help avoid false positives if structure is very flat.
        is_box_score_link = href.startswith('/boxscores/') and href.endswith('.html')
        is_not_sub_page = '/pbp/' not in href and \
                          '/shot-chart/' not in href and \
                          '/plus-minus/' not in href and \
                          '/leaders/' not in href # another potential sub-page type

        if is_box_score_link and is_not_sub_page:
            game_links_found +=1
            yield f"https://www.basketball-reference.com{href}"
        elif is_box_score_link and not is_not_sub_page:
            logger.debug(f"Filtered out potential sub-page link: {href} on {daily_url}")


    if game_links_found == 0:
        logger.warning(f"No box score links found using selector '{selector_used}' on {daily_url}. Trying a more general selector for game summaries.")
        # Fallback to a more general selector if the primary one fails
        # This targets divs that often wrap game summaries, then looks for links within.
        # Common pattern: <div class="game_summary"> ... <td class="gamelink"> ... <a> ...
        # Or simply any link within a game summary section.
        # This is a guess, actual structure would need inspection if above fails.
        selector_fallback = 'div.game_summary a[href*="/boxscores/"], div.games_summaries a[href*="/boxscores/"]'
        logger.info(f"Using fallback selector: '{selector_fallback}' for daily games page {daily_url}")

        for game_link_tag in soup.select(selector_fallback):
            href = game_link_tag.get('href', '')
            is_box_score_link = href.startswith('/boxscores/') and href.endswith('.html')
            is_not_sub_page = '/pbp/' not in href and \
                              '/shot-chart/' not in href and \
                              '/plus-minus/' not in href and \
                              '/leaders/' not in href
            if is_box_score_link and is_not_sub_page:
                game_links_found +=1
                yield f"https://www.basketball-reference.com{href}"
            elif is_box_score_link and not is_not_sub_page:
                logger.debug(f"Filtered out potential sub-page link (fallback): {href} on {daily_url}")

    if game_links_found == 0:
         logger.error(f"No box score links found on {daily_url} after trying primary and fallback selectors.")


def parse_box_score_page(soup, box_score_url):
    """
    Parses a single game's box score page.
    Returns a dictionary with game details and a list of player stats.
    """
    if not soup:
        logger.warning(f"No soup object provided for parsing box score page: {box_score_url}")
        return None

    game_data = {
        "home_team": None, "away_team": None,
        "home_score": None, "away_score": None,
        "players": []
    }

    scorebox = soup.find('div', class_='scorebox')
    if not scorebox:
        logger.error(f"Could not find scorebox for {box_score_url}. Cannot parse game details.")
        return None

    teams = scorebox.find_all('strong')
    team_names = [team.a.text if team.a else team.text for team in teams[:2]]
    scores_elements = scorebox.find_all('div', class_='score')
    final_scores_text = [score.text for score in scores_elements[:2]]

    if len(team_names) == 2:
        game_data["away_team"] = team_names[0] # Typically away team is listed first
        game_data["home_team"] = team_names[1] # Home team second
    else:
        logger.error(f"Could not reliably extract team names for {box_score_url}. Found: {team_names}")
        return None # Critical data missing

    if len(final_scores_text) == 2:
        try:
            # Scores correspond to the team order: away_score is first, home_score is second
            game_data["away_score"] = int(final_scores_text[0])
            game_data["home_score"] = int(final_scores_text[1])
        except ValueError:
            logger.error(f"Could not parse scores as integers for {box_score_url} (Scores: {final_scores_text}).")
            return None # Critical data missing
    else:
        logger.error(f"Could not reliably extract final scores for {box_score_url}. Found: {final_scores_text}")
        return None # Critical data missing

    player_stats_tables = soup.find_all('table', id=lambda x: x and x.startswith('box-') and x.endswith('-basic'))
    if not player_stats_tables:
        logger.warning(f"No basic player stats tables found for {box_score_url}.")

    for table in player_stats_tables:
        current_team_id_from_table = table.get('id').split('-')[1]
        tbody = table.find('tbody')
        if not tbody:
            logger.warning(f"No tbody found in stats table for team {current_team_id_from_table} in game {box_score_url}")
            continue

        for row in tbody.find_all('tr'):
            player_name_th = row.find('th', attrs={"data-stat": "player"})
            if not player_name_th or not player_name_th.a:
                if player_name_th and player_name_th.get_text(strip=True) not in ["Reserves", "Team Totals"]:
                    logger.debug(f"Skipping row with th: {player_name_th.get_text(strip=True) if player_name_th else 'Unknown TH'} in game {box_score_url} as it's not a player link row.")
                continue

            player_name = player_name_th.a.text
            mp_val = _get_cell_text(row, "mp", player_name, box_score_url)

            non_playing_statuses = ["Did Not Play", "Not With Team", "Did Not Dress", "Inactive", "Player Suspended"]
            if mp_val in non_playing_statuses or not mp_val:
                logger.debug(f"Player [{player_name}] did not play or status is '{mp_val}'. Skipping stats for this player.")
                continue

            player_row_data = {
                "player_name": player_name,
                "team": current_team_id_from_table,
                "mp": mp_val,
                "fg": _to_int(_get_cell_text(row, "fg", player_name, box_score_url), "fg", player_name, box_score_url),
                "fga": _to_int(_get_cell_text(row, "fga", player_name, box_score_url), "fga", player_name, box_score_url),
                "fg_pct": _to_real(_get_cell_text(row, "fg_pct", player_name, box_score_url), "fg_pct", player_name, box_score_url),
                "fg3": _to_int(_get_cell_text(row, "fg3", player_name, box_score_url), "fg3", player_name, box_score_url),
                "fg3a": _to_int(_get_cell_text(row, "fg3a", player_name, box_score_url), "fg3a", player_name, box_score_url),
                "fg3_pct": _to_real(_get_cell_text(row, "fg3_pct", player_name, box_score_url), "fg3_pct", player_name, box_score_url),
                "ft": _to_int(_get_cell_text(row, "ft", player_name, box_score_url), "ft", player_name, box_score_url),
                "fta": _to_int(_get_cell_text(row, "fta", player_name, box_score_url), "fta", player_name, box_score_url),
                "ft_pct": _to_real(_get_cell_text(row, "ft_pct", player_name, box_score_url), "ft_pct", player_name, box_score_url),
                "orb": _to_int(_get_cell_text(row, "orb", player_name, box_score_url), "orb", player_name, box_score_url),
                "drb": _to_int(_get_cell_text(row, "drb", player_name, box_score_url), "drb", player_name, box_score_url),
                "trb": _to_int(_get_cell_text(row, "trb", player_name, box_score_url), "trb", player_name, box_score_url),
                "ast": _to_int(_get_cell_text(row, "ast", player_name, box_score_url), "ast", player_name, box_score_url),
                "stl": _to_int(_get_cell_text(row, "stl", player_name, box_score_url), "stl", player_name, box_score_url),
                "blk": _to_int(_get_cell_text(row, "blk", player_name, box_score_url), "blk", player_name, box_score_url),
                "tov": _to_int(_get_cell_text(row, "tov", player_name, box_score_url), "tov", player_name, box_score_url),
                "pf": _to_int(_get_cell_text(row, "pf", player_name, box_score_url), "pf", player_name, box_score_url),
                "pts": _to_int(_get_cell_text(row, "pts", player_name, box_score_url), "pts", player_name, box_score_url),
                "plus_minus": _get_cell_text(row, "plus_minus", player_name, box_score_url) # Will be None if not in basic table
            }
            game_data["players"].append(player_row_data)

    return game_data

# --- Award Parsing Helpers ---
# Configure logger for the library if not already configured at module level for these helpers
# logger = logging.getLogger(__name__) # Assuming logger is already defined at module level

_MONTH_NAME_TO_NUMERIC = {
    'jan': 1, 'january': 1, 'jan.': 1,
    'feb': 2, 'february': 2, 'feb.': 2,
    'mar': 3, 'march': 3, 'mar.': 3,
    'apr': 4, 'april': 4, 'apr.': 4,
    'may': 5, 'may.': 5,
    'jun': 6, 'june': 6, 'jun.': 6,
    'jul': 7, 'july': 7, 'jul.': 7, # For completeness, though not typical for these awards
    'aug': 8, 'august': 8, 'aug.': 8, # For completeness
    'sep': 9, 'september': 9, 'sep.': 9, # For completeness
    'oct': 10, 'october': 10, 'oct.': 10,
    'nov': 11, 'november': 11, 'nov.': 11,
    'dec': 12, 'december': 12, 'dec.': 12,
    'oct/nov': 11, # basketball-reference specific for early season awards
}

def get_month_numeric(month_str):
    """
    Converts a month string (e.g., "Oct.", "October", "Jan") to its numeric representation.
    Case-insensitive. Handles combined months like "Oct/Nov" by returning the later month's number.
    Returns None if the month string is not recognized.
    """
    if not month_str:
        return None
    # Normalize: lower, strip, remove dots (e.g. "Oct." -> "oct")
    return _MONTH_NAME_TO_NUMERIC.get(month_str.lower().strip().replace('.', ''), None)

def get_award_year(season_str, month_numeric, award_month_text_for_log, award_name_for_log):
    """
    Determines the calendar year for an award given the season string and numeric month.
    Example: season "2022-23", month 10 (Oct) -> 2022.
             season "2022-23", month 1 (Jan)  -> 2023.
    Assumes NBA-like season spanning two calendar years.
    """
    if not season_str or month_numeric is None:
        logger.warning(f"Cannot determine award year for {award_name_for_log} due to missing season_str ('{season_str}') or month_numeric ('{month_numeric}'). Month Text: '{award_month_text_for_log}'")
        return None

    s_parts = season_str.split('-')
    if len(s_parts) != 2 or not s_parts[0].isdigit() or not s_parts[1].isdigit():
        logger.error(f"Invalid season string format '{season_str}' for {award_name_for_log} ({award_month_text_for_log}). Expected YYYY-YY or YYYY-YYYY (where second part is just for show).")
        return None

    try:
        start_year_season = int(s_parts[0])
    except ValueError as e: # Should be caught by isdigit above, but defensive.
        logger.error(f"Could not parse start year from '{s_parts[0]}' in season '{season_str}' for {award_name_for_log} ({award_month_text_for_log}). Error: {e}.")
        return None

    if not (1 <= month_numeric <= 12):
        logger.error(f"Invalid month_numeric '{month_numeric}' for {award_name_for_log} ({award_month_text_for_log}), season {season_str}. Cannot determine award year.")
        return None

    # Months for awards are typically Oct (10) to Apr (4), possibly May (5), Jun (6).
    # If month is Aug-Dec (e.g., Oct, Nov, Dec for start of season awards), it's the start_year_season.
    # If month is Jan-Jul (e.g., Jan, Feb, Mar, Apr for end of season awards), it's start_year_season + 1.
    if month_numeric >= 8: # Aug, Sep, Oct, Nov, Dec
        return start_year_season
    else: # Jan, Feb, Mar, Apr, May, Jun, Jul
        return start_year_season + 1

def parse_week_date_range(week_str, effective_season_start_year, current_row_for_log):
    """
    Parses a week string like "Oct 24-30" or "Dec 28-Jan 3" into start and end ISO dates.
    Uses effective_season_start_year to infer the correct calendar year for the dates.
    effective_season_start_year is the first year of the season (e.g. 2022 for 2022-23 season).
    """
    from datetime import datetime # Local import

    if not week_str or effective_season_start_year is None:
        logger.warning(f"Cannot parse week date range due to missing week_str or effective_season_start_year for {current_row_for_log}")
        return None, None

    try:
        # Normalize by removing dots and then splitting by space.
        # This helps handle "Oct. 24-30" and "Dec 25-Jan 3" consistently.
        normalized_week_str = week_str.replace('.', '')
        parts = normalized_week_str.split()

        # Handle "Month Day1 - Day2" case by checking parts length
        # If parts = ["Month", "Day1", "-", "Day2"] -> join Day1, -, Day2
        if len(parts) == 4 and parts[2] == '-':
            parts = [parts[0], f"{parts[1]}-{parts[3]}"]

        if not (2 <= len(parts) <= 3): # Expect ["Month", "DayRange"] or ["Month", "DayRangeStart-MonthEnd", "DayEnd"]
            logger.warning(f"Unexpected number of parts ({len(parts)}) in week string '{week_str}' after split for {current_row_for_log}. Parts: {parts}")
            return None, None

        month_name_str = parts[0]
        start_month_numeric = get_month_numeric(month_name_str)

        if not start_month_numeric:
            logger.warning(f"Unknown start month in POW date string: '{week_str}' (parsed month: '{month_name_str}') for {current_row_for_log}.")
            return None, None

        year_for_start_date = effective_season_start_year if start_month_numeric >= 8 else effective_season_start_year + 1

        day_range_str = parts[1]

        if '-' in day_range_str: # Format "D1-D2" or "D1-M2"
            start_day_str, end_day_or_month_str = day_range_str.split('-', 1)
            start_day = int(start_day_str)

            end_month_numeric_check = get_month_numeric(end_day_or_month_str)
            if end_month_numeric_check: # Month-crossing: "D1-M2", e.g., "25-Jan"
                end_month_numeric = end_month_numeric_check
                if len(parts) < 3: # Expecting Day2 as parts[2]
                    logger.warning(f"Incomplete date range for month-crossing week string '{week_str}' (expected Day2 as third part). Parts: {parts}. For {current_row_for_log}")
                    return None, None
                end_day = int(parts[2])

                year_for_end_date = year_for_start_date
                if end_month_numeric < start_month_numeric: # Year crossed
                    year_for_end_date = year_for_start_date + 1
            else: # Same month: "D1-D2", e.g., "24-30"
                end_month_numeric = start_month_numeric
                year_for_end_date = year_for_start_date
                end_day = int(end_day_or_month_str)

        elif day_range_str.isdigit(): # Single day: "Month Day", e.g., "Oct 24"
            start_day = int(day_range_str)
            end_day = start_day
            end_month_numeric = start_month_numeric
            year_for_end_date = year_for_start_date
        else:
            logger.warning(f"Unparseable day range format: '{day_range_str}' in week string '{week_str}' for {current_row_for_log}")
            return None, None

        start_date_obj = datetime(year_for_start_date, start_month_numeric, start_day)
        end_date_obj = datetime(year_for_end_date, end_month_numeric, end_day)

        return start_date_obj.strftime("%Y-%m-%d"), end_date_obj.strftime("%Y-%m-%d")

    except ValueError as ve: # Catches int() conversion errors, datetime errors for invalid dates
        logger.error(f"ValueError parsing week string '{week_str}': {ve}. For {current_row_for_log}")
        return None, None
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error parsing week string '{week_str}': {e}. For {current_row_for_log}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None
