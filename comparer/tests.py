from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock, call
import pandas as pd
import requests
import os
import sqlite3
from .views import MONTH_NAMES

# Import the functions we want to test
from .weather_utils import (
    get_coordinates_for_city,
    get_historical_annual_data_by_month,
    _fetch_raw_annual_data_from_api,
    _create_and_prepare_daily_dataframe,
    _aggregate_daily_data_to_monthly,
)

from .db_utils import (
    get_coordinates_from_db,
    search_cities,
    get_popular_cities,
)


class DbUtilsTests(TestCase):
    """Tests for database utility functions"""
    
    @patch("comparer.db_utils.get_db_connection")
    def test_get_coordinates_from_db_success(self, mock_get_connection):
        """Test get_coordinates_from_db with successful database lookup"""
        # Setup mock cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        # Setup mock query result
        mock_cursor.fetchone.return_value = ("London", "GB", "United Kingdom", 51.5074, -0.1278, "Greater London")
        
        # Test the function
        result = get_coordinates_from_db("London")
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["latitude"], 51.5074)
        self.assertEqual(result["longitude"], -0.1278)
        self.assertEqual(result["address"], "London, United Kingdom")
        
        # Verify SQL query was executed
        mock_cursor.execute.assert_called()
        
    @patch("comparer.db_utils.get_db_connection")
    def test_get_coordinates_from_db_no_match(self, mock_get_connection):
        """Test get_coordinates_from_db with no matching city"""
        # Setup mock cursor with no results
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        # No match in database
        mock_cursor.fetchone.return_value = None
        
        # Test the function
        result = get_coordinates_from_db("NonExistentCity123")
        
        # Should return None when no match
        self.assertIsNone(result)
        
    @patch("comparer.db_utils.get_db_connection")
    def test_search_cities(self, mock_get_connection):
        """Test search_cities functionality"""
        # Setup mock cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        # Setup mock query results
        mock_cursor.fetchall.return_value = [
            (1, "New York", "US", "United States", "NY", 40.7128, -74.0060),
            (2, "New Orleans", "US", "United States", "LA", 29.9511, -90.0715)
        ]
        
        # Test the function
        results = search_cities("new", 2)
        
        # Assertions
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "New York")
        self.assertEqual(results[1]["name"], "New Orleans")
        self.assertTrue("latitude" in results[0])
        self.assertTrue("longitude" in results[0])
        
        # Verify SQL query was executed
        mock_cursor.execute.assert_called_once()
        self.assertIn("%new%", str(mock_cursor.execute.call_args))
        
    @patch("comparer.db_utils.get_db_connection")
    def test_get_popular_cities(self, mock_get_connection):
        """Test get_popular_cities returns cities sorted by population"""
        # Setup mock cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        # Setup mock query results - should be ordered by population in real function
        mock_cursor.fetchall.return_value = [
            (1, "Tokyo", "JP", "Japan", "", 35.6762, 139.6503),
            (2, "Delhi", "IN", "India", "", 28.7041, 77.1025)
        ]
        
        # Test the function
        results = get_popular_cities(2)
        
        # Assertions
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Tokyo")
        self.assertEqual(results[1]["name"], "Delhi")
        
        # Verify SQL query was executed with correct limit
        mock_cursor.execute.assert_called_once()
        self.assertIn("population DESC", str(mock_cursor.execute.call_args))
        self.assertIn("2", str(mock_cursor.execute.call_args))


class WeatherUtilsTests(TestCase):

    # --- Tests for get_coordinates_for_city ---
    
    @patch("comparer.weather_utils.get_coordinates_from_db")
    def test_get_coordinates_for_city_success(self, mock_get_coords_from_db):
        """Test that get_coordinates_for_city calls the database function"""
        expected_result = {
            "latitude": 51.5074, 
            "longitude": -0.1278, 
            "address": "London, UK"
        }
        mock_get_coords_from_db.return_value = expected_result
        
        result = get_coordinates_for_city("London")
        
        self.assertEqual(result, expected_result)
        mock_get_coords_from_db.assert_called_once_with("London")
        
    @patch("comparer.weather_utils.get_coordinates_from_db")
    def test_get_coordinates_for_city_not_found(self, mock_get_coords_from_db):
        """Test that get_coordinates_for_city returns None when city not found"""
        mock_get_coords_from_db.return_value = None
        
        result = get_coordinates_for_city("NonExistentCity")
        
        self.assertIsNone(result)
        mock_get_coords_from_db.assert_called_once_with("NonExistentCity")

    # --- Tests for _fetch_raw_annual_data_from_api (helper function) ---

    @patch("comparer.weather_utils.requests.get")
    def test_fetch_raw_annual_data_success(self, mock_requests_get):
        """Test _fetch_raw_annual_data_from_api successfully returns API data."""
        mock_response = MagicMock()
        mock_api_json = {
            "daily": {
                "time": ["time"],
                "temperature_2m_mean": [5.0],
                "precipitation_sum": [0.5],
            },
            "daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm"},
        }
        mock_response.json.return_value = mock_api_json
        mock_response.raise_for_status = (
            MagicMock()
        )  # Mock this to do nothing (no HTTP error)
        mock_requests_get.return_value = mock_response

        result = _fetch_raw_annual_data_from_api(51.5, -0.1, 2025)
        self.assertEqual(result, mock_api_json)
        # Check that requests.get was called (you can be more specific with URL if needed)
        mock_requests_get.assert_called_once()

    @patch("comparer.weather_utils.requests.get")
    def test_fetch_raw_annual_data_http_error(self, mock_requests_get):
        """Test _fetch_raw_annual_data_from_api handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "API Error"
        )
        mock_requests_get.return_value = mock_response

        result = _fetch_raw_annual_data_from_api(51.5, -0.1, 2025)
        self.assertIsNone(result)

    @patch("comparer.weather_utils.requests.get")
    def test_fetch_raw_annual_data_missing_keys(self, mock_requests_get):
        """Test _fetch_raw_annual_data_from_api handles missing keys in API response."""
        mock_response = MagicMock()
        mock_api_json_bad = {"unexpected_structure": True}  # Missing "daily"
        mock_response.json.return_value = mock_api_json_bad
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        result = _fetch_raw_annual_data_from_api(51.5, -0.1, 2025)
        self.assertIsNone(result)

    # --- Tests for _create_and_prepare_daily_dataframe (helper function) ---

    def test_create_dataframe_success(self):
        """Test _create_and_prepare_daily_dataframe successfully creates a DataFrame."""
        sample_api_data = {
            "daily": {
                "time": ["2025-01-01", "2025-01-02"],
                "temperature_2m_mean": ["5.0", "6.1"],  # Test with string numbers
                "precipitation_sum": ["0.5", "0.0"],
            }
        }
        df = _create_and_prepare_daily_dataframe(sample_api_data)
        self.assertIsNotNone(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df.index))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["temperature_2m_mean"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["precipitation_sum"]))

    def test_create_dataframe_empty_after_dropna(self):
        """Test _create_and_prepare_daily_dataframe returns None if df becomes empty after dropna."""
        sample_api_data = {  # Data that will result in NaNs for required columns
            "daily": {
                "time": ["2025-01-01"],
                "temperature_2m_mean": [None],  # Will be NaN, then dropped
                "precipitation_sum": [None],  # Will be NaN, then dropped
            }
        }
        df = _create_and_prepare_daily_dataframe(sample_api_data)
        self.assertIsNone(df)  # Expect None as per the function's logic

    def test_create_dataframe_missing_required_columns(self):
        """Test _create_and_prepare_daily_dataframe returns None if required columns are missing."""
        sample_api_data = {
            "daily": {
                "time": ["2025-01-01"],
                # "temperature_2m_mean" is missing
                "precipitation_sum": ["0.5"],
            }
        }
        df = _create_and_prepare_daily_dataframe(sample_api_data)
        self.assertIsNone(df)

    # --- Tests for _aggregate_daily_data_to_monthly (helper function) ---

    def test_aggregate_data_to_monthly_success(self):
        """Test _aggregate_daily_data_to_monthly successfully aggregates data."""
        # Create a sample daily DataFrame
        dates = pd.to_datetime(["2025-01-15", "2025-01-20", "2025-02-10", "2025-02-15"])
        data = {
            "temperature_2m_mean": [10, 12, 5, 7],
            "precipitation_sum": [1, 2, 0.5, 1.5],
        }
        daily_df = pd.DataFrame(data, index=dates)

        monthly_results = _aggregate_daily_data_to_monthly(daily_df, 2025)
        self.assertEqual(
            len(monthly_results), 12
        )  # Should have results for all 12 months

        jan_data = next(m for m in monthly_results if m["month"] == 1)
        feb_data = next(m for m in monthly_results if m["month"] == 2)
        mar_data = next(m for m in monthly_results if m["month"] == 3)

        self.assertAlmostEqual(jan_data["avg_temp"], 11.0)  # (10+12)/2
        self.assertAlmostEqual(jan_data["total_precip"], 3.0)  # 1+2
        self.assertAlmostEqual(feb_data["avg_temp"], 6.0)  # (5+7)/2
        self.assertAlmostEqual(feb_data["total_precip"], 2.0)  # 0.5+1.5
        self.assertIsNone(mar_data["avg_temp"])  # No data for March
        self.assertIsNone(mar_data["total_precip"])

    def test_aggregate_data_empty_df(self):
        """Test _aggregate_daily_data_to_monthly handles empty DataFrame."""
        empty_df = pd.DataFrame(columns=["temperature_2m_mean", "precipitation_sum"])
        empty_df.index = pd.to_datetime(empty_df.index)  # Ensure datetime index

        monthly_results = _aggregate_daily_data_to_monthly(empty_df, 2025)
        self.assertEqual(monthly_results, [])

    # --- Tests for the main get_historical_annual_data_by_month function ---
    # This will mostly test the orchestration of the mocked helper functions.

    @patch("comparer.weather_utils.cache")
    @patch("comparer.weather_utils._fetch_raw_annual_data_from_api")
    @patch("comparer.weather_utils._create_and_prepare_daily_dataframe")
    @patch("comparer.weather_utils._aggregate_daily_data_to_monthly")
    def test_get_historical_annual_data_success_flow(
        self, mock_aggregate, mock_create_df, mock_fetch_api, mock_cache
    ):
        """Test the successful flow of get_historical_annual_data_by_month."""
        # Setup mock cache to return None (to ensure we call the fetch function)
        mock_cache.get.return_value = None
        
        # Setup mock return values
        mock_api_response_json = {
            "daily": {"time": ["2025-01-01"]},  # Minimal valid structure
            "daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm"},
        }
        mock_fetch_api.return_value = mock_api_response_json

        mock_prepared_df = MagicMock(spec=pd.DataFrame)  # A mock DataFrame object
        mock_prepared_df.empty = False  # Simulate it's not empty
        mock_create_df.return_value = mock_prepared_df

        mock_monthly_aggregated_list = [
            {"month": 1, "avg_temp": 5.0, "total_precip": 10.0}
        ]
        mock_aggregate.return_value = mock_monthly_aggregated_list
        
        # Test year
        test_year = 2025

        result = get_historical_annual_data_by_month(51.5, -0.1, test_year)

        self.assertIsNotNone(result)
        self.assertEqual(result["temp_unit"], "°C")
        self.assertEqual(result["precip_unit"], "mm")
        self.assertEqual(result["monthly_data"], mock_monthly_aggregated_list)

        mock_cache.get.assert_called_once()
        mock_fetch_api.assert_called_once_with(51.5, -0.1, test_year)
        mock_create_df.assert_called_once_with(mock_api_response_json)
        mock_aggregate.assert_called_once_with(mock_prepared_df, test_year)

    @patch("comparer.weather_utils._fetch_raw_annual_data_from_api")
    def test_get_historical_annual_data_api_fetch_fails(self, mock_fetch_api):
        """Test get_historical_annual_data_by_month when API fetch fails."""
        mock_fetch_api.return_value = None  # Simulate API fetch failure

        result = get_historical_annual_data_by_month(51.5, -0.1, 2025)
        self.assertIsNone(result)  # Expect None on critical API failure

    @patch("comparer.weather_utils._fetch_raw_annual_data_from_api")
    @patch("comparer.weather_utils._create_and_prepare_daily_dataframe")
    def test_get_historical_annual_data_dataframe_prep_fails(
        self, mock_create_df, mock_fetch_api
    ):
        """Test get_historical_annual_data_by_month when DataFrame prep fails."""
        mock_api_response_json = {
            "daily": {"time": ["2025-01-01"]},
            "daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm"},
        }
        mock_fetch_api.return_value = mock_api_response_json
        mock_create_df.return_value = None  # Simulate DataFrame creation failure

        result = get_historical_annual_data_by_month(51.5, -0.1, 2025)

        self.assertIsNotNone(result)  # Function should still return a dict
        self.assertEqual(result["monthly_data"], [])  # Expect empty monthly data
        self.assertEqual(
            result["temp_unit"], "°C"
        )  # Units should still be there if API call was ok
        self.assertEqual(result["precip_unit"], "mm")


class ComparerViewsTests(TestCase):

    def setUp(self):
        """
        Set up the test client for all view tests.
        This method is called before each test method in this class.
        """
        self.client = Client()
        self.index_url = reverse("comparer:index")

        # Mock data for successful API/utility calls
        self.mock_coords_london = {
            "latitude": 51.5,
            "longitude": -0.1,
            "address": "London, UK",
        }
        self.mock_coords_paris = {
            "latitude": 48.8,
            "longitude": 2.3,
            "address": "Paris, FR",
        }

        self.mock_annual_data_london_raw = [
            {"month": m, "avg_temp": 5 + m, "total_precip": 10 * m}
            for m in range(1, 13)
        ]
        self.mock_annual_data_paris_raw = [
            {"month": m, "avg_temp": 6 + m, "total_precip": 12 * m}
            for m in range(1, 13)
        ]

        self.mock_annual_weather_london = {
            "monthly_data": self.mock_annual_data_london_raw,
            "temp_unit": "°C",
            "precip_unit": "mm",
        }
        self.mock_annual_weather_paris = {
            "monthly_data": self.mock_annual_data_paris_raw,
            "temp_unit": "°C",
            "precip_unit": "mm",
        }

    def test_index_view_get_request(self):
        """
        Test the index view for a GET request.
        """
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "comparer/index.html")

        # Check initial context values
        self.assertFalse(response.context["form_submitted"])
        self.assertEqual(response.context["submitted_city1"], "")
        self.assertEqual(response.context["submitted_city2"], "")
        self.assertEqual(response.context["submitted_city3"], "")
        self.assertIsNotNone(response.context["current_year"])
        self.assertEqual((response.context["month_labels_for_chart"]), MONTH_NAMES)
        self.assertEqual((response.context["city_data_for_chart"]), [])
        self.assertEqual((response.context["weather_cards_data"]), [])
        self.assertIsNone(response.context["error_message"])

    # --- Test POST Request for index_view ---

    @patch("comparer.views._process_cities_concurrently")
    def test_index_view_post_request_success(
        self, mock_process_cities
    ):
        """
        Test index_view for a successful POST request with valid city data.
        """
        """
        Test index_view for a successful POST request with valid city data.
        """
        # Mock the concurrent processing function
        mock_process_cities.return_value = (
            [
                {"name": "London", "address": "London, UK", "error": None},  # London success
                {"name": "Paris", "address": "Paris, France", "error": None}  # Paris success
            ],
            [
                {"name": "London (5-Year Average)", "temperatures": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]},
                {"name": "Paris (5-Year Average)", "temperatures": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}
            ],
            []  # No error messages
        )

        year_to_test = 2023
        city1_raw = "london"
        city1_expected_in_view = "London"
        city2_raw = "PARIS "
        city2_expected_in_view = "Paris"

        post_data = {
            "city_name_1": city1_raw,
            "city_name_2": city2_raw,
            "year": str(year_to_test),
        }
        
        response = self.client.post(self.index_url, data=post_data)

        # Verify the response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "comparer/index.html")
        self.assertContains(response, "Weather Compare")

        # Check that the form values were processed correctly
        self.assertTrue(response.context["form_submitted"])
        self.assertEqual(response.context["submitted_city1"], city1_raw)
        self.assertEqual(response.context["submitted_city2"], city2_raw.strip())
        # The application uses the current year, not the year from the POST data
        self.assertIsNotNone(response.context["current_year"])
        self.assertIsNone(response.context["error_message"])

        # Check that the mock was called properly
        mock_process_cities.assert_called_once()
        
        # Check the weather cards were properly passed to the context
        weather_cards = response.context["weather_cards_data"]
        self.assertEqual(len(weather_cards), 2)
        self.assertEqual(weather_cards[0]["name"], "London")
        self.assertIsNone(weather_cards[0]["error"])
        self.assertEqual(weather_cards[1]["name"], "Paris") 
        self.assertIsNone(weather_cards[1]["error"])
        
        # Check the chart data was properly passed to the context
        chart_data = response.context["city_data_for_chart"]
        self.assertEqual(len(chart_data), 2)

    def test_index_view_post_missing_city1(self):
        """Test POST request when the required city1 name is missing."""
        post_data = {
            "city_name_1": "",  # Missing first city (required)
            "city_name_2": "Paris",
            "year": "2023",
        }
        response = self.client.post(self.index_url, data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["error_message"])
        expected_error_msg = "Please enter a name for City 1"
        self.assertIn(
            expected_error_msg, response.context["error_message"]
        )
        self.assertContains(
            response,
            'data-testid="main-navigation"',
        )

    def test_bootstrap_card_integration(self):
        """
        Test that the weather data is displayed in Bootstrap cards.
        """
        # Mock the concurrent processing function to return valid data
        with patch("comparer.views._process_cities_concurrently") as mock_process:
            mock_process.return_value = (
                [{"name": "London", "address": "London, UK", "error": None}],  # weather cards
                [{"name": "London (5-Year Average)", "temperatures": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}],  # chart data
                []  # no errors
            )
            
            post_data = {
                "city_name_1": "London",
            }
            response = self.client.post(self.index_url, data=post_data)
            
            self.assertContains(
                response,
                '<div class="card">',
            )

    def test_bootstrap_form_integration(self):
        """
        Test that the form inputs use Bootstrap's form-control class.
        """
        response = self.client.get(self.index_url)
        self.assertContains(
            response,
            '<input type="text" name="city_name_1" id="city_name_1" class="form-control"',
        )

    def test_index_view_post_optional_cities(self):
        """Test POST request with only city1 provided (city2 and city3 are optional)."""
        # Mock the city processing function to return valid data
        with patch("comparer.views._process_cities_concurrently") as mock_process:
            mock_process.return_value = (
                [{"name": "London", "address": "London, UK", "error": None}],  # weather cards
                [{"name": "London (5-Year Average)", "temperatures": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}],  # chart data
                []  # no errors
            )
            
            post_data = {
                "city_name_1": "London",
                "city_name_2": "",  # Optional city2 not provided
                "city_name_3": "",  # Optional city3 not provided
                "year": "2023",
            }
            response = self.client.post(self.index_url, data=post_data)
            
            # Test should pass because city2 and city3 are optional
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.context["error_message"])  # No error expected
            self.assertNotEqual((response.context["city_data_for_chart"]), [])  # Should have chart data
            self.assertEqual(len(response.context["weather_cards_data"]), 1)  # Should have one weather card

    @patch("comparer.views._process_cities_concurrently")
    def test_index_view_post_geocoding_fails(self, mock_process_cities):
        """Test POST when geocoding fails for one city."""
        # Mock the concurrent processing function to return one successful and one failed city
        mock_process_cities.return_value = (
            [
                {"name": "London", "address": "London, UK", "error": None},  # London success
                {"name": "Nonexistent", "address": None, "error": "Could not process data for Nonexistent"}  # Nonexistent city fails
            ],
            [{"name": "London (5-Year Average)", "temperatures": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}],  # Only London chart data
            ["Could not find coordinates for 'Nonexistent'"]  # Error messages
        )

        post_data = {
            "city_name_1": "London",
            "city_name_2": "NonExistent",  # This will fail geocoding
            "year": "2023",
        }
        response = self.client.post(self.index_url, data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            response.context["error_message"]
        )  # No general form error

        weather_cards = response.context["weather_cards_data"]
        self.assertEqual(len(weather_cards), 2)
        self.assertEqual(weather_cards[0]["name"], "London")
        self.assertIsNone(weather_cards[0]["error"])
        self.assertEqual(weather_cards[1]["name"], "Nonexistent")  # Title-cased
        self.assertIsNotNone(weather_cards[1]["error"])
        self.assertIn("Could not process data", weather_cards[1]["error"])

        chart_data = response.context["city_data_for_chart"]
        self.assertEqual(len(chart_data), 1)  # Only London's data
        # Chart data names now include year range
        self.assertTrue(chart_data[0]["name"].startswith("London"))

    @patch("comparer.views._process_cities_concurrently")
    def test_index_view_post_weather_fetch_fails_for_one(
        self, mock_process_cities
    ):
        """Test POST when weather data fetch fails for one city."""
        # Mock the concurrent processing function to return a successful and a failed city
        mock_process_cities.return_value = (
            [
                {"name": "London", "address": "London, UK", "error": None},  # London success
                {"name": "Paris", "address": "Paris, France", "error": "Could not process data for Paris"}  # Paris fails
            ],
            [{"name": "London (5-Year Average)", "temperatures": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}],  # Only London chart data
            ["Error processing Paris"]  # Error messages
        )

        post_data = {"city_name_1": "London", "city_name_2": "Paris", "year": "2025"}
        response = self.client.post(self.index_url, data=post_data)

        self.assertEqual(response.status_code, 200)
        weather_cards = response.context["weather_cards_data"]
        self.assertEqual(len(weather_cards), 2)
        self.assertEqual(weather_cards[0]["name"], "London")
        self.assertIsNone(weather_cards[0]["error"])
        self.assertEqual(weather_cards[1]["name"], "Paris")
        self.assertIsNotNone(weather_cards[1]["error"])
        self.assertIn(
            "Could not process data", weather_cards[1]["error"]
        )

        chart_data = response.context["city_data_for_chart"]
        self.assertEqual(len(chart_data), 1)  # Only London's data
        self.assertTrue(chart_data[0]["name"].startswith("London"))

    def test_base_template_integration(self):
        """
        Test that the index view uses the base template with Bootstrap navbar.
        This test will fail initially, then pass after Bootstrap integration.
        """
        response = self.client.get(self.index_url)
        self.assertContains(
            response,
            'data-testid="main-navigation"',
        )
        
        
class CityDataViewTests(TestCase):
    """Tests for the city_data_view function that provides autocomplete data"""
    
    def setUp(self):
        """Set up the test client"""
        self.client = Client()
        self.city_data_url = reverse("comparer:city_data")
    
    @patch("comparer.views.search_cities")
    def test_city_data_view_with_query(self, mock_search_cities):
        """Test city_data_view with a search query"""
        # Setup mock result
        mock_cities = [
            {'id': 1, 'name': 'London', 'country': 'GB', 'latitude': 51.5074, 'longitude': -0.1278, 'location': 'London, Greater London, United Kingdom'},
            {'id': 2, 'name': 'Londonderry', 'country': 'GB', 'latitude': 54.9966, 'longitude': -7.3086, 'location': 'Londonderry, Northern Ireland, United Kingdom'}
        ]
        mock_search_cities.return_value = mock_cities
        
        # Make request with query
        response = self.client.get(self.city_data_url, {'q': 'lond', 'limit': '2'})
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data), 2)
        self.assertEqual(response_data[0]['name'], 'London')
        self.assertEqual(response_data[1]['name'], 'Londonderry')
        
        # Verify search_cities was called with correct params
        mock_search_cities.assert_called_once_with('lond', 2)
        
    @patch("comparer.views.get_popular_cities")
    def test_city_data_view_without_query(self, mock_get_popular_cities):
        """Test city_data_view without a search query returns popular cities"""
        # Setup mock result for popular cities
        mock_cities = [
            {'id': 1, 'name': 'Tokyo', 'country': 'JP', 'latitude': 35.6762, 'longitude': 139.6503, 'location': 'Tokyo, Japan'},
            {'id': 2, 'name': 'Delhi', 'country': 'IN', 'latitude': 28.7041, 'longitude': 77.1025, 'location': 'Delhi, India'}
        ]
        mock_get_popular_cities.return_value = mock_cities
        
        # Make request without query
        response = self.client.get(self.city_data_url, {'limit': '2'})
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data), 2)
        self.assertEqual(response_data[0]['name'], 'Tokyo')
        self.assertEqual(response_data[1]['name'], 'Delhi')
        
        # Verify get_popular_cities was called with correct params
        mock_get_popular_cities.assert_called_once_with(2)
        
    @patch("comparer.views.search_cities")
    def test_city_data_view_error_handling(self, mock_search_cities):
        """Test city_data_view handles errors gracefully"""
        # Setup mock to raise exception
        mock_search_cities.side_effect = Exception("Database error")
        
        # Make request that will cause error
        response = self.client.get(self.city_data_url, {'q': 'test'})
        
        # Verify error response
        self.assertEqual(response.status_code, 500)
        response_data = response.json()
        self.assertTrue('error' in response_data)
