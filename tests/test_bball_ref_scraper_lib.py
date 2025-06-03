import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
import requests # Import requests for its exceptions
from pathlib import Path
import logging

# Attempt to import the library functions
# This assumes the tests are run from the root of the repository,
# or that the 'scripts' directory is in PYTHONPATH.
try:
    from scripts import bball_ref_scraper_lib
except ImportError:
    # Fallback for cases where scripts is not directly importable
    # This might happen if tests are run from within the 'tests' directory itself
    # without further sys.path manipulation. For robust testing,
    # ensuring PYTHONPATH is set correctly or using a test runner that handles
    # this (like pytest with project structure) is better.
    import sys
    sys.path.append(str(Path(__file__).parent.parent)) # Add repo root to path
    from scripts import bball_ref_scraper_lib

# Suppress logging during tests unless specifically testing logging
logging.disable(logging.CRITICAL)


class BaseScraperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_path = Path(__file__).parent
        cls.daily_html_content = (base_path / "sample_html/daily_games_oct26_2023.html").read_text()
        cls.box_score_html_content = (base_path / "sample_html/box_score_202310260MIL.html").read_text()

        cls.daily_soup = BeautifulSoup(cls.daily_html_content, 'html.parser')
        cls.box_score_soup = BeautifulSoup(cls.box_score_html_content, 'html.parser')

class TestHelperFunctions(unittest.TestCase):
    def test_to_int(self):
        self.assertEqual(bball_ref_scraper_lib._to_int("5", "stat", "player", "game_url"), 5)
        self.assertIsNone(bball_ref_scraper_lib._to_int("", "stat", "player", "game_url"))
        self.assertIsNone(bball_ref_scraper_lib._to_int(None, "stat", "player", "game_url"))
        self.assertIsNone(bball_ref_scraper_lib._to_int("abc", "stat", "player", "game_url"))
        self.assertEqual(bball_ref_scraper_lib._to_int(" -5 ", "stat", "player", "game_url"), -5) # Test with spaces

    def test_to_real(self):
        self.assertEqual(bball_ref_scraper_lib._to_real(".500", "stat", "player", "game_url"), 0.5)
        self.assertIsNone(bball_ref_scraper_lib._to_real("", "stat", "player", "game_url"))
        self.assertIsNone(bball_ref_scraper_lib._to_real(None, "stat", "player", "game_url"))
        self.assertIsNone(bball_ref_scraper_lib._to_real("abc", "stat", "player", "game_url"))
        self.assertEqual(bball_ref_scraper_lib._to_real(" 0.75 ", "stat", "player", "game_url"), 0.75) # Test with spaces


class TestGetSoup(unittest.TestCase):
    @patch('scripts.bball_ref_scraper_lib.requests.get')
    def test_get_soup_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = "<html><body><p>Test</p></body></html>"
        mock_get.return_value = mock_response

        soup = bball_ref_scraper_lib.get_soup("http://example.com")
        self.assertIsNotNone(soup)
        self.assertEqual(soup.find("p").text, "Test")
        mock_get.assert_called_once_with("http://example.com", timeout=10)

    @patch('scripts.bball_ref_scraper_lib.requests.get')
    def test_get_soup_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Error")
        mock_get.return_value = mock_response

        # Enable logging temporarily for this test to check log output
        logging.disable(logging.NOTSET)
        with self.assertLogs(logger=bball_ref_scraper_lib.logger, level='ERROR') as cm:
            soup = bball_ref_scraper_lib.get_soup("http://example.com/404")
        self.assertIsNone(soup)
        self.assertTrue(any("Error fetching URL http://example.com/404" in message for message in cm.output))
        logging.disable(logging.CRITICAL) # Disable again

    @patch('scripts.bball_ref_scraper_lib.requests.get')
    def test_get_soup_request_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        logging.disable(logging.NOTSET)
        with self.assertLogs(logger=bball_ref_scraper_lib.logger, level='ERROR') as cm:
            soup = bball_ref_scraper_lib.get_soup("http://example.com/connection_error")
        self.assertIsNone(soup)
        self.assertTrue(any("Error fetching URL http://example.com/connection_error" in message for message in cm.output))
        logging.disable(logging.CRITICAL)


class TestParseDailyGamesPage(BaseScraperTest):
    def test_parse_daily_games_page_found(self):
        urls = list(bball_ref_scraper_lib.parse_daily_games_page(self.daily_soup, "dummy_daily_url"))
        self.assertEqual(len(urls), 2)
        self.assertIn("https://www.basketball-reference.com/boxscores/202310260MIL.html", urls)
        self.assertIn("https://www.basketball-reference.com/boxscores/202310260LAL.html", urls)

    def test_parse_daily_games_page_no_games(self):
        empty_soup = BeautifulSoup("<html><body></body></html>", 'html.parser')
        urls = list(bball_ref_scraper_lib.parse_daily_games_page(empty_soup, "dummy_empty_url"))
        self.assertEqual(len(urls), 0)

    def test_parse_daily_games_page_no_soup(self):
        urls = list(bball_ref_scraper_lib.parse_daily_games_page(None, "dummy_none_soup_url"))
        self.assertEqual(len(urls), 0)


class TestParseBoxScorePage(BaseScraperTest):
    def test_parse_box_score_page_valid(self):
        game_data = bball_ref_scraper_lib.parse_box_score_page(self.box_score_soup, "dummy_box_score_url")
        self.assertIsNotNone(game_data)

        # Test team names and scores
        self.assertEqual(game_data["home_team"], "Milwaukee Bucks")
        self.assertEqual(game_data["away_team"], "Philadelphia 76ers")
        self.assertEqual(game_data["home_score"], 118)
        self.assertEqual(game_data["away_score"], 117)

        # Test player data
        # PHI: Embiid, Maxey, EmptyStats, Oubre Jr. (4)
        # MIL: Giannis, Lillard (2)
        # Total = 6 (Player DNP is skipped)
        self.assertEqual(len(game_data["players"]), 6)

        # Joel Embiid (PHI)
        embiid = next(p for p in game_data["players"] if p["player_name"] == "Joel Embiid")
        self.assertEqual(embiid["team"], "PHI")
        self.assertEqual(embiid["mp"], "36:29")
        self.assertEqual(embiid["fg"], 9)
        self.assertEqual(embiid["fga"], 21)
        self.assertEqual(embiid["fg_pct"], 0.429)
        self.assertEqual(embiid["pts"], 24)
        self.assertEqual(embiid["plus_minus"], "+2") # From basic table in this sample

        # Player EmptyStats (PHI)
        empty_stats_player = next(p for p in game_data["players"] if p["player_name"] == "Player EmptyStats")
        self.assertEqual(empty_stats_player["team"], "PHI")
        self.assertEqual(empty_stats_player["mp"], "20:00")
        self.assertIsNone(empty_stats_player["fg"])
        self.assertIsNone(empty_stats_player["fga"])
        self.assertIsNone(empty_stats_player["fg_pct"])
        self.assertIsNone(empty_stats_player["pts"])
        self.assertIsNone(empty_stats_player["plus_minus"]) # Should be None as it's empty in basic

        # Giannis Antetokounmpo (MIL) - check plus_minus from advanced if basic doesn't have it
        # Note: The provided sample HTML for box_score has plus_minus in basic for Embiid.
        # The library logic currently only checks basic tables.
        # To test advanced table plus_minus, the sample HTML or library logic would need adjustment.
        # For now, we'll test Giannis as found in MIL basic table.
        giannis = next(p for p in game_data["players"] if p["player_name"] == "Giannis Antetokounmpo")
        self.assertEqual(giannis["team"], "MIL")
        self.assertEqual(giannis["mp"], "35:17")
        self.assertEqual(giannis["pts"], 23)
        # The sample HTML for MIL basic table doesn't have plus_minus, so it should be None
        # The advanced table data for Giannis is +7. The current lib `parse_box_score_page`
        # only parses basic tables. If we want to test merging, the lib needs to be updated.
        # For this test, we expect None because only basic is parsed for all fields other than player name/mp
        # The library was updated to take plus_minus from basic if available.
        # The sample HTML for Giannis does not have plus_minus in basic table.
        # The library's _get_cell_text will log a warning and return None.
        self.assertIsNone(giannis["plus_minus"])


    def test_parse_box_score_page_missing_scorebox(self):
        malformed_soup = BeautifulSoup("<html><body><table id='box-MIL-game-basic'></table></body></html>", 'html.parser')
        game_data = bball_ref_scraper_lib.parse_box_score_page(malformed_soup, "dummy_missing_scorebox_url")
        self.assertIsNone(game_data)

    def test_parse_box_score_page_no_player_tables(self):
        # HTML with scorebox but no player stat tables
        no_tables_html = """
        <div class="scorebox">
          <div><a href="#"><strong>Team A</strong></a><div class="score">100</div></div>
          <div><a href="#"><strong>Team B</strong></a><div class="score">90</div></div>
        </div>
        """
        no_tables_soup = BeautifulSoup(no_tables_html, 'html.parser')
        game_data = bball_ref_scraper_lib.parse_box_score_page(no_tables_soup, "dummy_no_tables_url")
        self.assertIsNotNone(game_data)
        self.assertEqual(game_data["home_team"], "Team B") # Home team is the second one listed
        self.assertEqual(game_data["away_team"], "Team A")
        self.assertEqual(game_data["home_score"], 90) # Score of Team B
        self.assertEqual(game_data["away_score"], 100) # Score of Team A
        self.assertEqual(len(game_data["players"]), 0)

    def test_parse_box_score_page_no_soup(self):
        game_data = bball_ref_scraper_lib.parse_box_score_page(None, "dummy_none_soup_url")
        self.assertIsNone(game_data)

if __name__ == '__main__':
    unittest.main()
