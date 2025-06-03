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
    for game_link_p in soup.select('td.gamelink p.links a'):
        href = game_link_p.get('href', '')
        # Ensure it's a box score link and not a play-by-play or other sub-page link
        if 'boxscores' in href and href.endswith('.html') and '/pbp/' not in href and '/shot-chart/' not in href and '/plus-minus/' not in href:
            game_links_found +=1
            yield f"https://www.basketball-reference.com{href}"

    if game_links_found == 0:
        logger.info(f"No box score links found on {daily_url}")


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
