# comparer/weather_utils.py
import requests
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import os

# --- Constants for API interaction ---
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
API_TIMEOUT_SECONDS = 20  # Increased timeout for potentially larger annual data
DAILY_METRICS = "temperature_2m_mean,precipitation_sum"
TIMEZONE = "GMT" # Or use "auto" to guess from lat/lon

# --- Geocoding Function ---
def get_coordinates_for_city(city_name):
    """
    Geocodes a city name to its latitude and longitude using Nominatim.

    Args:
        city_name (str): The name of the city.

    Returns:
        dict: A dictionary with 'latitude', 'longitude', and 'address', 
              or None if not found or an error occurs.
    """
    if not city_name:
        print("Warning: Empty city name provided for geocoding.")
        return None
    
    # Construct user_agent from environment variables with fallbacks
    app_name = os.environ.get("NOMINATIM_USER_AGENT_APP_NAME", "DefaultWeatherApp")
    contact_email = os.environ.get("NOMINATIM_USER_AGENT_EMAIL", "anonymous_user@example.com")
    user_agent_string = f"{app_name}/1.0 ({contact_email})"   
    
    try:
        geolocator = Nominatim(user_agent=user_agent_string)
                
        location = geolocator.geocode(city_name, timeout=10)        
        if location:
            return {"latitude": location.latitude,
                    "longitude": location.longitude,
                    "address": location.address}            
        else:
            print(f"Info: Could not geocode city: '{city_name}'. No location found by Nominatim.")
            return None
    except GeocoderTimedOut:
        print(f"Warning: Geocoding service timed out for city: '{city_name}'")
        return None
    except GeocoderUnavailable:
        print(f"Warning: Geocoding service unavailable for city: '{city_name}'")
        return None
    except Exception as e:
        print(f"Error: An unexpected error occurred during geocoding for '{city_name}': {e}")
        return None

# --- Weather Data Fetching and Processing Helpers ---

def _fetch_raw_annual_data_from_api(latitude, longitude, year):
    """
    Helper to fetch raw daily weather data for a full year from Open-Meteo.
    Returns the JSON response data or None on failure.
    """
    start_date_str = f"{year}-01-01"
    end_date_str = f"{year}-12-31"
    
    params = {
        "latitude": latitude, "longitude": longitude,
        "start_date": start_date_str, "end_date": end_date_str,
        "daily": DAILY_METRICS, "timezone": TIMEZONE
    }
    
    # For debugging, you can uncomment the next line:
    # print(f"Requesting Open-Meteo URL: {requests.Request('GET', OPEN_METEO_ARCHIVE_URL, params=params).prepare().url}")

    try:
        response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        
        api_data = response.json()
        # Basic validation of the API response structure
        if not api_data.get("daily") or not isinstance(api_data["daily"].get("time"), list):
            print(f"Warning: API response for {year} at ({latitude},{longitude}) lacks 'daily' data or 'time' array is not a list.")
            return None
        return api_data
        
    except requests.exceptions.RequestException as e:
        print(f"API Request Error for {year} at ({latitude},{longitude}): {e}")
        return None
    except ValueError as e: # Handles JSON decoding errors if response is not valid JSON
        print(f"API JSON Decode Error for {year} at ({latitude},{longitude}): {e}")
        return None

def _create_and_prepare_daily_dataframe(api_data_json):
    """
    Converts raw API JSON data into a prepared Pandas DataFrame for daily weather.
    Returns the DataFrame or None if input is invalid or processing fails.
    """
    if not api_data_json or "daily" not in api_data_json:
        print("Warning: Invalid or empty API data provided for DataFrame creation.")
        return None

    try:
        df = pd.DataFrame(api_data_json["daily"])
        
        required_cols = ['time', 'temperature_2m_mean', 'precipitation_sum']
        if not all(col in df.columns for col in required_cols):
            print(f"Warning: DataFrame from API is missing one or more required columns: {required_cols}")
            # Log which columns are actually present for debugging
            # print(f"Available columns: {df.columns.tolist()}")
            return None
            
        df['time'] = pd.to_datetime(df['time'])
        df['temperature_2m_mean'] = pd.to_numeric(df['temperature_2m_mean'], errors='coerce')
        df['precipitation_sum'] = pd.to_numeric(df['precipitation_sum'], errors='coerce')
        
        # Drop rows where essential data (temp or precip) became NaN after coercion.
        # This is important for accurate monthly aggregation.
        df.dropna(subset=['temperature_2m_mean', 'precipitation_sum'], inplace=True)
        
        if df.empty:
            print("Warning: DataFrame became empty after cleaning (dropna). This means no valid daily entries were found for the period.")
            return None # Explicitly return None if no data remains
            
        df.set_index('time', inplace=True)
        return df
        
    except KeyError as e:
        print(f"DataFrame Creation Error: Missing expected key in API data: {e}")
        return None
    except Exception as e: # Catch any other pandas-related errors
        print(f"DataFrame Creation/Preparation Error: {e}")
        return None

def _aggregate_daily_data_to_monthly(daily_df, year):
    """
    Aggregates a DataFrame of daily weather data to monthly averages/sums.
    Returns a list of dictionaries, one for each month. Returns empty list on error or if no data.
    """
    if daily_df is None or daily_df.empty:
        # print("Info: No daily data provided for monthly aggregation.") # Can be verbose
        return [] 

    try:
        # Resample to get monthly mean temperature and sum of precipitation
        # 'ME' stands for Month End frequency.
        monthly_avg_temp = daily_df['temperature_2m_mean'].resample('ME').mean()
        monthly_total_precip = daily_df['precipitation_sum'].resample('ME').sum()

        monthly_results = []
        for month_num in range(1, 13):
            # Construct month-end date for reliable lookup in resampled Series
            # This is the index pandas uses for 'ME' resampling.
            try:
                # For month_num=12, year_for_next_month = year + 1, next_month_start_num = 1
                # else, year_for_next_month = year, next_month_start_num = month_num + 1
                if month_num == 12:
                    # Last day of December
                    month_end_lookup_date = pd.Timestamp(datetime(year, 12, 31))
                else:
                    # Last day of the current month_num
                    month_end_lookup_date = pd.Timestamp(datetime(year, month_num + 1, 1) - pd.Timedelta(days=1))
                
                avg_temp_val = monthly_avg_temp.get(month_end_lookup_date)
                total_precip_val = monthly_total_precip.get(month_end_lookup_date)

            except KeyError: # Should ideally not happen if resample covers all months
                avg_temp_val = None
                total_precip_val = None
            
            monthly_results.append({
                "month": month_num,
                "avg_temp": round(avg_temp_val, 2) if pd.notnull(avg_temp_val) else None,
                "total_precip": round(total_precip_val, 2) if pd.notnull(total_precip_val) else None
            })
        return monthly_results
        
    except Exception as e:
        print(f"Error during monthly aggregation: {e}")
        return [] # Return empty list on aggregation failure

# --- Main Public Function ---
def get_historical_annual_data_by_month(latitude, longitude, year):
    """
    Fetches and processes daily historical weather data for an entire year, 
    aggregating it into monthly averages for temperature and total precipitation.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        year (int): The year for which to fetch data.

    Returns:
        dict: Contains 'monthly_data' (list of 12 monthly stats), 
              'temp_unit', 'precip_unit'. Returns None if critical failure (e.g., API down).
              'monthly_data' will be an empty list if aggregation fails or no usable data.
    """
    raw_api_data = _fetch_raw_annual_data_from_api(latitude, longitude, year)
    if not raw_api_data:
        return None # Critical failure in fetching data (API error, network issue, etc.)

    daily_df = _create_and_prepare_daily_dataframe(raw_api_data)
    # If daily_df is None here, it means the data from API was unusable or became empty after cleaning.
    # We still want to return the units if possible, but monthly_data will be empty.
    
    monthly_aggregated_data = [] # Default to empty list
    if daily_df is not None: # Only attempt aggregation if DataFrame is valid
        monthly_aggregated_data = _aggregate_daily_data_to_monthly(daily_df, year)
    else:
        print(f"Info: DataFrame preparation failed or resulted in empty data for {year} at ({latitude},{longitude}). No monthly aggregation performed.")

    # Extract units from the raw API data (if available, even if DataFrame prep failed)
    temp_unit = raw_api_data.get('daily_units', {}).get('temperature_2m_mean', '°C')
    precip_unit = raw_api_data.get('daily_units', {}).get('precipitation_sum', 'mm')

    return {
        "monthly_data": monthly_aggregated_data, # This list might be empty
        "temp_unit": temp_unit,
        "precip_unit": precip_unit
    }


# --- Test Block ---
if __name__ == "__main__":
    print("--- Testing Geocoding Function ---")
    city1 = "london" # Test lowercase
    coords1 = get_coordinates_for_city(city1)
    if coords1:
        print(f"Coordinates for '{city1.title()}': Lat={coords1['latitude']}, Lon={coords1['longitude']}, Address: {coords1['address']}")
    else:
        print(f"Could not find coordinates for '{city1.title()}'.")

    city2 = "NonExistentCity123XYZ"
    coords2 = get_coordinates_for_city(city2)
    if coords2:
        print(f"Coordinates for '{city2}': {coords2}") # Should not happen
    else:
        print(f"Correctly failed to find coordinates for '{city2}'.")

    city3 = "" # Test empty string
    coords3 = get_coordinates_for_city(city3)
    if coords3:
        print(f"Coordinates for empty city string: {coords3}") # Should not happen
    else:
        print("Correctly handled empty city string for geocoding.")

    print("\n--- Testing Annual Historical Weather Data ---")
    # Test with valid coordinates (e.g., for London from previous geocoding test)
    if coords1:
        test_lat = coords1['latitude']
        test_lon = coords1['longitude']
        test_year = 2022 # A recent full year

        print(f"\nFetching annual data for London ({test_lat}, {test_lon}) for {test_year}...")
        annual_data_london = get_historical_annual_data_by_month(test_lat, test_lon, test_year)

        if annual_data_london:
            print(f"Data received for London, {test_year}:")
            print(f"  Temperature Unit: {annual_data_london['temp_unit']}")
            print(f"  Precipitation Unit: {annual_data_london['precip_unit']}")
            if annual_data_london['monthly_data']:
                for month_data in annual_data_london['monthly_data']:
                    print(f"  Month {month_data['month']:02d}: Avg Temp={month_data['avg_temp']}, Total Precip={month_data['total_precip']}")
            else:
                print("  Monthly data list is empty. This might be due to data quality or processing issues for this specific year/location.")
        else:
            print(f"Could not retrieve any annual weather data for London for {test_year} (Critical API or initial processing failure).")
            
        # Test a year with potentially sparse data or known issues if you have one, e.g., a very old year
        # test_year_old = 1950 
        # print(f"\nFetching annual data for London for {test_year_old}...")
        # annual_data_london_old = get_historical_annual_data_by_month(test_lat, test_lon, test_year_old)
        # if annual_data_london_old:
        #     # ... similar print statements ...
        # else:
        #     print(f"Could not retrieve annual weather data for London for {test_year_old}.")

    else:
        print("\nSkipping weather data test as initial geocoding for London failed.")

    # Test with known problematic coordinates or year (e.g., latitude out of bounds)
    # This would primarily test _fetch_raw_annual_data_from_api's error handling if Open-Meteo returns an error JSON
    print("\nFetching data for invalid coordinates (e.g., on Mars)...")
    invalid_coords_data = get_historical_annual_data_by_month(latitude=0, longitude=0, year=2022) # Middle of ocean
    if invalid_coords_data and invalid_coords_data['monthly_data']:
         print("Data received for (0,0), 2022 (unexpected for invalid location, check API response):")
         # ... print details ...
    elif invalid_coords_data and not invalid_coords_data['monthly_data']:
        print("API call for (0,0), 2022 was made, units might be present, but no monthly data aggregated (expected for invalid location).")
        print(f"  Temp Unit: {invalid_coords_data['temp_unit']}, Precip Unit: {invalid_coords_data['precip_unit']}")
    else:
        print("Correctly failed to retrieve or process data for invalid coordinates (0,0), 2022 (e.g. API returned error).")