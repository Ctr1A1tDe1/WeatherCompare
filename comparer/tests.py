from django.test import TestCase, Client # Add Client
from django.urls import reverse # To resolve URL names
from unittest.mock import patch, MagicMock, call # Add call for checking multiple calls
import pandas as pd
import requests
import os
from .views import MONTH_NAMES


# Import the functions we want to test from weather_utils
from .weather_utils import (
    get_coordinates_for_city, 
    get_historical_annual_data_by_month,
    _fetch_raw_annual_data_from_api,      # Test this helper
    _create_and_prepare_daily_dataframe, # Test this helper
    _aggregate_daily_data_to_monthly    # Test this helper
)

class WeatherUtilsTests(TestCase):

    # --- Tests for get_coordinates_for_city ---

    @patch('comparer.weather_utils.Nominatim') # Target 'Nominatim' where it's used
    def test_get_coordinates_for_city_success(self, mock_nominatim_class):
        """
        Test get_coordinates_for_city successfully returns coordinates.
        """
        # Configure the mock geolocator and its geocode method
        city_name = "London"
        expected_latitude = 51.5074
        expected_longitude = -0.1278
        expected_address = "London, UK"
        
        mock_location_object = MagicMock(
            name="SpecificLocationObject_SUCCESS") # Unique name
        mock_location_object.latitude = expected_latitude
        mock_location_object.longitude = expected_longitude
        mock_location_object.address = expected_address
        
        mock_geolocator_instance = mock_nominatim_class.return_value 
        mock_geolocator_instance.name = "MockedGeolocatorInstance_SUCCESS"
        mock_geolocator_instance.geocode.return_value = mock_location_object

        expected_result = {
            "latitude": expected_latitude, 
            "longitude": expected_longitude, 
            "address": expected_address
        }
        
        test_app_name = "TestWeatherAppForAgent"
        test_email = "test_contact@example.com"
        expected_user_agent_string = f"{test_app_name}/1.0 ({test_email})"
        
        with patch.dict(os.environ, {
            'NOMINATIM_USER_AGENT_APP_NAME': test_app_name,
            'NOMINATIM_USER_AGENT_EMAIL': test_email
        }):
            result = get_coordinates_for_city(city_name)
        
        self.assertEqual(result, expected_result)
        mock_nominatim_class.assert_called_once_with(user_agent=expected_user_agent_string)
        mock_geolocator_instance.geocode.assert_called_once_with(city_name, timeout=10)

    @patch('comparer.weather_utils.Nominatim')
    def test_get_coordinates_for_city_geocoder_timeout(self, mock_nominatim_class): # Parameter name updated
        from geopy.exc import GeocoderTimedOut # Import where it's used
        
        mock_geolocator_instance = mock_nominatim_class.return_value
        mock_geolocator_instance.name = "MockedGeolocatorInstance_TIMEOUT"
        # Configure the geocode method ON THAT INSTANCE to raise GeocoderTimedOut
        mock_geolocator_instance.geocode.side_effect = GeocoderTimedOut

        test_app_name = "TestAppTimeout"
        test_email = "testtimeout@example.com"
        expected_user_agent_string = f"{test_app_name}/1.0 ({test_email})"
        city_to_test = "London"

        with patch.dict(os.environ, {
            'NOMINATIM_USER_AGENT_APP_NAME': test_app_name,
            'NOMINATIM_USER_AGENT_EMAIL': test_email
        }):
            result = get_coordinates_for_city(city_to_test)
        
        self.assertIsNone(result)
        mock_nominatim_class.assert_called_once_with(user_agent=expected_user_agent_string)
        mock_geolocator_instance.geocode.assert_called_once_with(city_to_test, timeout=10)

    @patch('comparer.weather_utils.Nominatim')
    def test_get_coordinates_for_city_geocoder_timeout(self, mock_nominatim_class):
        """
        Test get_coordinates_for_city handles GeocoderTimedOut.
        """
        from geopy.exc import GeocoderTimedOut # Import specific exception
        mock_geolocator_instance = mock_nominatim_class.return_value
        mock_geolocator_instance.geocode.side_effect = GeocoderTimedOut

        result = get_coordinates_for_city("London")
        self.assertIsNone(result)

    # --- Tests for _fetch_raw_annual_data_from_api (helper function) ---

    @patch('comparer.weather_utils.requests.get')
    def test_fetch_raw_annual_data_success(self, mock_requests_get):
        """ Test _fetch_raw_annual_data_from_api successfully returns API data. """
        mock_response = MagicMock()
        mock_api_json = {
            "daily": {
                "time": ["2023-01-01"],
                "temperature_2m_mean": [5.0],
                "precipitation_sum": [0.5]
            },
            "daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm"}
        }
        mock_response.json.return_value = mock_api_json
        mock_response.raise_for_status = MagicMock() # Mock this to do nothing (no HTTP error)
        mock_requests_get.return_value = mock_response

        result = _fetch_raw_annual_data_from_api(51.5, -0.1, 2023)
        self.assertEqual(result, mock_api_json)
        # Check that requests.get was called (you can be more specific with URL if needed)
        mock_requests_get.assert_called_once() 

    @patch('comparer.weather_utils.requests.get')
    def test_fetch_raw_annual_data_http_error(self, mock_requests_get):
        """ Test _fetch_raw_annual_data_from_api handles HTTP errors. """
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        mock_requests_get.return_value = mock_response

        result = _fetch_raw_annual_data_from_api(51.5, -0.1, 2023)
        self.assertIsNone(result)

    @patch('comparer.weather_utils.requests.get')
    def test_fetch_raw_annual_data_missing_keys(self, mock_requests_get):
        """ Test _fetch_raw_annual_data_from_api handles missing keys in API response. """
        mock_response = MagicMock()
        mock_api_json_bad = {"unexpected_structure": True} # Missing "daily"
        mock_response.json.return_value = mock_api_json_bad
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response
        
        result = _fetch_raw_annual_data_from_api(51.5, -0.1, 2023)
        self.assertIsNone(result)

    # --- Tests for _create_and_prepare_daily_dataframe (helper function) ---
    
    def test_create_dataframe_success(self):
        """ Test _create_and_prepare_daily_dataframe successfully creates a DataFrame. """
        sample_api_data = {
            "daily": {
                "time": ["2023-01-01", "2023-01-02"],
                "temperature_2m_mean": ["5.0", "6.1"], # Test with string numbers
                "precipitation_sum": ["0.5", "0.0"]
            }
        }
        df = _create_and_prepare_daily_dataframe(sample_api_data)
        self.assertIsNotNone(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df.index))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['temperature_2m_mean']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['precipitation_sum']))

    def test_create_dataframe_empty_after_dropna(self):
        """ Test _create_and_prepare_daily_dataframe returns None if df becomes empty after dropna. """
        sample_api_data = { # Data that will result in NaNs for required columns
            "daily": {
                "time": ["2023-01-01"],
                "temperature_2m_mean": [None], # Will be NaN, then dropped
                "precipitation_sum": [None]    # Will be NaN, then dropped
            }
        }
        df = _create_and_prepare_daily_dataframe(sample_api_data)
        self.assertIsNone(df) # Expect None as per the function's logic

    def test_create_dataframe_missing_required_columns(self):
        """ Test _create_and_prepare_daily_dataframe returns None if required columns are missing. """
        sample_api_data = {
            "daily": {
                "time": ["2023-01-01"],
                # "temperature_2m_mean" is missing
                "precipitation_sum": ["0.5"]
            }
        }
        df = _create_and_prepare_daily_dataframe(sample_api_data)
        self.assertIsNone(df)

    # --- Tests for _aggregate_daily_data_to_monthly (helper function) ---

    def test_aggregate_data_to_monthly_success(self):
        """ Test _aggregate_daily_data_to_monthly successfully aggregates data. """
        # Create a sample daily DataFrame
        dates = pd.to_datetime(['2023-01-15', '2023-01-20', '2023-02-10', '2023-02-15'])
        data = {
            'temperature_2m_mean': [10, 12, 5, 7],
            'precipitation_sum': [1, 2, 0.5, 1.5]
        }
        daily_df = pd.DataFrame(data, index=dates)
        
        monthly_results = _aggregate_daily_data_to_monthly(daily_df, 2023)
        self.assertEqual(len(monthly_results), 12) # Should have results for all 12 months
        
        jan_data = next(m for m in monthly_results if m['month'] == 1)
        feb_data = next(m for m in monthly_results if m['month'] == 2)
        mar_data = next(m for m in monthly_results if m['month'] == 3)

        self.assertAlmostEqual(jan_data['avg_temp'], 11.0) # (10+12)/2
        self.assertAlmostEqual(jan_data['total_precip'], 3.0) # 1+2
        self.assertAlmostEqual(feb_data['avg_temp'], 6.0) # (5+7)/2
        self.assertAlmostEqual(feb_data['total_precip'], 2.0) # 0.5+1.5
        self.assertIsNone(mar_data['avg_temp']) # No data for March
        self.assertIsNone(mar_data['total_precip'])

    def test_aggregate_data_empty_df(self):
        """ Test _aggregate_daily_data_to_monthly handles empty DataFrame. """
        empty_df = pd.DataFrame(columns=['temperature_2m_mean', 'precipitation_sum'])
        empty_df.index = pd.to_datetime(empty_df.index) # Ensure datetime index
        
        monthly_results = _aggregate_daily_data_to_monthly(empty_df, 2023)
        self.assertEqual(monthly_results, [])

    # --- Tests for the main get_historical_annual_data_by_month function ---
    # This will mostly test the orchestration of the mocked helper functions.

    @patch('comparer.weather_utils._fetch_raw_annual_data_from_api')
    @patch('comparer.weather_utils._create_and_prepare_daily_dataframe')
    @patch('comparer.weather_utils._aggregate_daily_data_to_monthly')
    def test_get_historical_annual_data_success_flow(self, mock_aggregate, mock_create_df, mock_fetch_api):
        """ Test the successful flow of get_historical_annual_data_by_month. """
        # Setup mock return values
        mock_api_response_json = {
            "daily": {"time": ["2023-01-01"]}, # Minimal valid structure
            "daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm"}
        }
        mock_fetch_api.return_value = mock_api_response_json
        
        mock_prepared_df = MagicMock(spec=pd.DataFrame) # A mock DataFrame object
        mock_prepared_df.empty = False # Simulate it's not empty
        mock_create_df.return_value = mock_prepared_df
        
        mock_monthly_aggregated_list = [{"month": 1, "avg_temp": 5.0, "total_precip": 10.0}]
        mock_aggregate.return_value = mock_monthly_aggregated_list

        result = get_historical_annual_data_by_month(51.5, -0.1, 2023)

        self.assertIsNotNone(result)
        self.assertEqual(result['monthly_data'], mock_monthly_aggregated_list)
        self.assertEqual(result['temp_unit'], "°C")
        self.assertEqual(result['precip_unit'], "mm")
        
        mock_fetch_api.assert_called_once_with(51.5, -0.1, 2023)
        mock_create_df.assert_called_once_with(mock_api_response_json)
        mock_aggregate.assert_called_once_with(mock_prepared_df, 2023)

    @patch('comparer.weather_utils._fetch_raw_annual_data_from_api')
    def test_get_historical_annual_data_api_fetch_fails(self, mock_fetch_api):
        """ Test get_historical_annual_data_by_month when API fetch fails. """
        mock_fetch_api.return_value = None # Simulate API fetch failure

        result = get_historical_annual_data_by_month(51.5, -0.1, 2023)
        self.assertIsNone(result) # Expect None on critical API failure

    @patch('comparer.weather_utils._fetch_raw_annual_data_from_api')
    @patch('comparer.weather_utils._create_and_prepare_daily_dataframe')
    def test_get_historical_annual_data_dataframe_prep_fails(self, mock_create_df, mock_fetch_api):
        """ Test get_historical_annual_data_by_month when DataFrame prep fails. """
        mock_api_response_json = {
            "daily": {"time": ["2023-01-01"]}, 
            "daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm"}
        }
        mock_fetch_api.return_value = mock_api_response_json
        mock_create_df.return_value = None # Simulate DataFrame creation failure

        result = get_historical_annual_data_by_month(51.5, -0.1, 2023)
        
        self.assertIsNotNone(result) # Function should still return a dict
        self.assertEqual(result['monthly_data'], []) # Expect empty monthly data
        self.assertEqual(result['temp_unit'], "°C") # Units should still be there if API call was ok
        self.assertEqual(result['precip_unit'], "mm")

class ComparerViewsTests(TestCase):

    def setUp(self):
        """
        Set up the test client for all view tests.
        This method is called before each test method in this class.
        """
        self.client = Client()
        self.index_url = reverse('comparer:index')

        # Mock data for successful API/utility calls
        self.mock_coords_london = {"latitude": 51.5, "longitude": -0.1, "address": "London, UK"}
        self.mock_coords_paris = {"latitude": 48.8, "longitude": 2.3, "address": "Paris, FR"}
        
        self.mock_annual_data_london_raw = [{"month": m, "avg_temp": 5+m, "total_precip": 10*m} for m in range(1,13)]
        self.mock_annual_data_paris_raw = [{"month": m, "avg_temp": 6+m, "total_precip": 12*m} for m in range(1,13)]

        self.mock_annual_weather_london = {
            "monthly_data": self.mock_annual_data_london_raw,
            "temp_unit": "°C", "precip_unit": "mm"
        }
        self.mock_annual_weather_paris = {
            "monthly_data": self.mock_annual_data_paris_raw,
            "temp_unit": "°C", "precip_unit": "mm"
        }

    def test_index_view_get_request(self):
        """
        Test the index view for a GET request.
        """
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comparer/index.html')
        
        # Check initial context values
        self.assertFalse(response.context['form_submitted'])
        self.assertEqual(response.context['submitted_city1'], '')
        self.assertEqual(response.context['submitted_city2'], '')
        self.assertIsNotNone(response.context['selected_year'])
        self.assertEqual((response.context['month_labels_for_chart']), MONTH_NAMES)
        self.assertEqual((response.context['city_data_for_chart']), [])
        self.assertIsNone(response.context['error_message'])

    # --- Test POST Request for index_view ---

    @patch('comparer.views.get_historical_annual_data_by_month')
    @patch('comparer.views.get_coordinates_for_city')
    def test_index_view_post_request_success(self, mock_get_coords, mock_get_annual_data):
        """
        Test index_view for a successful POST request with valid city data.
        """
        # Configure mocks
        mock_get_coords.side_effect = [
            self.mock_coords_london, # Return for first call (London)
            self.mock_coords_paris   # Return for second call (Paris)
        ]
        # get_historical_annual_data_by_month will also be called twice
        mock_get_annual_data.side_effect = [
            self.mock_annual_weather_london, # For London
            self.mock_annual_weather_paris   # For Paris
        ]
        
        year_to_test = 2023
        city1_raw = 'london'
        city1_expected_in_view = 'London'
        city2_raw = 'PARIS '
        city2_expected_in_view = 'Paris'

        post_data = {
            'city_name_1': city1_raw,
            'city_name_2': city2_raw,
            'year': str(year_to_test)
        }
        response = self.client.post(self.index_url, data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comparer/index.html')
        self.assertContains(response, f"Comparison for {year_to_test}")
        self.assertContains(response, city1_expected_in_view)
        self.assertContains(response, city2_expected_in_view)
        
        self.assertEqual(response.context['submitted_city1'], city1_expected_in_view) 
        self.assertEqual(response.context['submitted_city2'], city2_expected_in_view)
        self.assertTrue(response.context['form_submitted'])
        self.assertEqual(response.context['selected_year'], 2023)
        self.assertIsNone(response.context['error_message'])

        # Check if utility functions were called correctly
        expected_coord_calls = [call(city1_expected_in_view),
            call(city2_expected_in_view)
        ]
        mock_get_coords.assert_has_calls(expected_coord_calls, any_order=False) # Order matters here

        expected_annual_data_calls = [
            call(self.mock_coords_london['latitude'], self.mock_coords_london['longitude'], 2023),
            call(self.mock_coords_paris['latitude'], self.mock_coords_paris['longitude'], 2023)
        ]
        mock_get_annual_data.assert_has_calls(expected_annual_data_calls, any_order=False)

        # Check the structure of city_details_for_display
        city_details = response.context['city_details_for_display']
        self.assertEqual(len(city_details), 2)
        self.assertEqual(city_details[0]['name'], 'London')
        self.assertIsNone(city_details[0]['error'])
        self.assertEqual(city_details[0]['address'], self.mock_coords_london['address'])
        self.assertEqual(city_details[1]['name'], 'Paris')
        self.assertIsNone(city_details[1]['error'])

        # Check chart data (complex structure, so check key parts)
        chart_data = (response.context['city_data_for_chart'])
        self.assertEqual(len(chart_data), 2)
        self.assertEqual(chart_data[0]['name'], 'London')
        self.assertEqual(len(chart_data[0]['temperatures']), 12)
        self.assertEqual(chart_data[0]['temperatures'][0], self.mock_annual_data_london_raw[0]['avg_temp'])
        self.assertEqual(chart_data[1]['name'], 'Paris')

    def test_index_view_post_missing_city(self):
        """ Test POST request when a city name is missing. """
        post_data = {
            'city_name_1': 'London',
            'city_name_2': '', # Missing second city
            'year': '2023'
        }
        response = self.client.post(self.index_url, data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['error_message'])
        expected_error_msg = "Please enter names for both cities"
        self.assertIn("Please enter names for both cities", response.context['error_message'])
        self.assertContains(response, expected_error_msg, msg_prefix="Error message for missing city not rendered")
        self.assertEqual((response.context['city_data_for_chart']), []) # No chart data
        

    @patch('comparer.views.get_coordinates_for_city')
    def test_index_view_post_geocoding_fails(self, mock_get_coords):
        """ Test POST when geocoding fails for one city. """
        mock_get_coords.side_effect = [
            self.mock_coords_london, # London geocodes fine
            None                    # Berlin fails to geocode
        ]
        # We don't need to mock get_historical_annual_data_by_month for Berlin because it won't be called if geocoding fails.
        # So, we only need to mock it for London if it's called.
        # To simplify, let's assume if one fails, the other might still try to proceed.
        # The view logic needs to handle this. Our current view calls fetch_and_process for both.

        # We expect get_historical_annual_data_by_month to be called only once for London
        with patch('comparer.views.get_historical_annual_data_by_month') as mock_get_annual_data:
            mock_get_annual_data.return_value = self.mock_annual_weather_london

            post_data = {
                'city_name_1': 'London',
                'city_name_2': 'NonExistent', # This will fail geocoding
                'year': '2023'
            }
            response = self.client.post(self.index_url, data=post_data)

            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.context['error_message']) # No general form error

            city_details = response.context['city_details_for_display']
            self.assertEqual(len(city_details), 2)
            self.assertEqual(city_details[0]['name'], 'London')
            self.assertIsNone(city_details[0]['error'])
            self.assertEqual(city_details[1]['name'], 'Nonexistent') # Title-cased
            self.assertIsNotNone(city_details[1]['error'])
            self.assertIn("Could not find coordinates", city_details[1]['error'])

            chart_data = (response.context['city_data_for_chart'])
            self.assertEqual(len(chart_data), 1) # Only London's data
            self.assertEqual(chart_data[0]['name'], 'London')
            
            mock_get_annual_data.assert_called_once_with(
                self.mock_coords_london['latitude'], self.mock_coords_london['longitude'], 2023
            )

    @patch('comparer.views.get_coordinates_for_city')
    @patch('comparer.views.get_historical_annual_data_by_month')
    def test_index_view_post_weather_fetch_fails_for_one(self, mock_get_annual_data, mock_get_coords):
        """ Test POST when weather data fetch fails for one city. """
        mock_get_coords.side_effect = [self.mock_coords_london, self.mock_coords_paris]
        mock_get_annual_data.side_effect = [
            self.mock_annual_weather_london, # London weather OK
            None                            # Paris weather fetch fails
        ]

        post_data = {'city_name_1': 'London', 'city_name_2': 'Paris', 'year': '2023'}
        response = self.client.post(self.index_url, data=post_data)

        self.assertEqual(response.status_code, 200)
        city_details = response.context['city_details_for_display']
        self.assertEqual(city_details[0]['name'], 'London')
        self.assertIsNone(city_details[0]['error'])
        self.assertEqual(city_details[1]['name'], 'Paris')
        self.assertIsNotNone(city_details[1]['error'])
        self.assertIn("Could not retrieve annual weather data", city_details[1]['error'])

        chart_data = (response.context['city_data_for_chart'])
        self.assertEqual(len(chart_data), 1) # Only London's data
        self.assertEqual(chart_data[0]['name'], 'London')