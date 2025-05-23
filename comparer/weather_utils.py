# comparer/weather_utils.py
import requests
import pandas as pd
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import os
import time
from functools import wraps
from typing import Dict, List, Optional, Union, Any, Tuple
from django.core.cache import cache

# --- Constants for API interaction ---
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_CURRENT_URL = "https://api.open-meteo.com/v1/forecast"
API_TIMEOUT_SECONDS = 20  # Increased timeout for potentially larger annual data
DAILY_METRICS = "temperature_2m_mean,precipitation_sum"  # Fixed: removed unsupported parameters for archive API
CURRENT_METRICS = "temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m,weathercode"
TIMEZONE = "GMT"  # Or use "auto" to guess from lat/lon

# --- Cache durations in seconds ---
GEOCODING_CACHE_DURATION = 7 * 86400  # 7 days
WEATHER_CACHE_DURATION = 86400  # 24 hours

# --- API Rate Limits ---
NOMINATIM_CALLS_LIMIT = 1  # Calls per second
NOMINATIM_TIME_PERIOD = 1  # Second
OPEN_METEO_CALLS_LIMIT = 10  # Calls per minute
OPEN_METEO_TIME_PERIOD = 60  # Seconds

# --- Default values ---
DEFAULT_TEMP_UNIT = "°C"
DEFAULT_PRECIP_UNIT = "mm"
DEFAULT_APP_NAME = "DefaultWeatherApp"
DEFAULT_CONTACT_EMAIL = "anonymous_user@example.com"

# --- Type aliases ---
CoordinatesDict = Dict[str, Union[float, str]]
MonthlyDataItem = Dict[str, Optional[Union[int, float]]]
MonthlyDataList = List[MonthlyDataItem]
WeatherDataDict = Dict[str, Union[MonthlyDataList, str]]
APIResponseDict = Dict[str, Any]


# --- Rate limiting ---
class RateLimiter:
    """Simple rate limiter to prevent API abuse"""

    def __init__(self, calls_limit: int, time_period: int):
        self.calls_limit = calls_limit  # Max calls allowed
        self.time_period = time_period  # Time period in seconds
        self.calls_timestamps: List[datetime] = []

    def wait_if_needed(self) -> None:
        """Wait if rate limit is reached"""
        now = datetime.now()

        # Remove timestamps older than the time period
        self.calls_timestamps = [
            ts
            for ts in self.calls_timestamps
            if now - ts < timedelta(seconds=self.time_period)
        ]

        # If we've reached the limit, wait
        if len(self.calls_timestamps) >= self.calls_limit:
            oldest_timestamp = min(self.calls_timestamps)
            wait_time = (
                oldest_timestamp + timedelta(seconds=self.time_period) - now
            ).total_seconds()
            if wait_time > 0:
                time.sleep(wait_time)

        # Add current timestamp
        self.calls_timestamps.append(datetime.now())


# Create rate limiters for each API
NOMINATIM_RATE_LIMITER = RateLimiter(
    calls_limit=NOMINATIM_CALLS_LIMIT, time_period=NOMINATIM_TIME_PERIOD
)
OPEN_METEO_RATE_LIMITER = RateLimiter(
    calls_limit=OPEN_METEO_CALLS_LIMIT, time_period=OPEN_METEO_TIME_PERIOD
)


# --- Memoization decorator ---
def memoize(func):
    """Simple memoization decorator for function results"""
    cache_dict = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create a key from the function arguments
        key = str(args) + str(sorted(kwargs.items()))

        # Return cached result if available
        if key in cache_dict:
            return cache_dict[key]

        # Calculate and cache result
        result = func(*args, **kwargs)
        cache_dict[key] = result
        return result

    return wrapper


def _create_user_agent() -> str:
    """
    Creates a user agent string for Nominatim based on environment variables.

    Returns:
        str: The formatted user agent string.
    """
    app_name = os.environ.get("NOMINATIM_USER_AGENT_APP_NAME", DEFAULT_APP_NAME)
    contact_email = os.environ.get("NOMINATIM_USER_AGENT_EMAIL", DEFAULT_CONTACT_EMAIL)
    return f"{app_name}/1.0 ({contact_email})"


# --- Geocoding Function ---
def get_coordinates_for_city(city_name: str) -> Optional[CoordinatesDict]:
    """
    Geocodes a city name to its latitude and longitude using Nominatim.

    Args:
        city_name: The name of the city.

    Returns:
        A dictionary with 'latitude', 'longitude', and 'address',
        or None if not found or an error occurs.
    """
    if not city_name:
        print("Warning: Empty city name provided for geocoding.")
        return None

    # Create a cache key - replace spaces with underscores to avoid memcached issues
    cache_key = f"geocode_{city_name.lower().strip().replace(' ', '_')}"

    # Try to get from cache
    cached_coords = cache.get(cache_key)
    if cached_coords:
        return cached_coords

    # Get user agent string
    user_agent_string = _create_user_agent()

    try:
        # Apply rate limiting
        NOMINATIM_RATE_LIMITER.wait_if_needed()

        geolocator = Nominatim(user_agent=user_agent_string)

        location = geolocator.geocode(city_name, timeout=10)
        if location:
            result = {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "address": location.address,
            }
            # Cache for a longer period as coordinates rarely change
            cache.set(cache_key, result, GEOCODING_CACHE_DURATION)
            return result
        else:
            print(
                f"Info: Could not geocode city: '{city_name}'. No location found by Nominatim."
            )
            return None
    except GeocoderTimedOut:
        print(f"Warning: Geocoding service timed out for city: '{city_name}'")
        return None
    except GeocoderUnavailable:
        print(f"Warning: Geocoding service unavailable for city: '{city_name}'")
        return None
    except Exception as e:
        print(
            f"Error: An unexpected error occurred during geocoding for '{city_name}': {e}"
        )
        return None


# --- Weather Data Fetching and Processing Helpers ---


def _fetch_raw_annual_data_from_api(
    latitude: float, longitude: float, year: int
) -> Optional[APIResponseDict]:
    """
    Helper to fetch raw daily weather data for a full year from Open-Meteo.

    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        year: The year for which to fetch data.

    Returns:
        The JSON response data or None on failure.
    """
    # Apply rate limiting
    OPEN_METEO_RATE_LIMITER.wait_if_needed()

    # Create a cache key for this request
    cache_key = f"weather_raw_{latitude}_{longitude}_{year}"

    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    start_date_str = f"{year}-01-01"
    end_date_str = f"{year}-12-31"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "daily": DAILY_METRICS,
        "timezone": TIMEZONE,
    }

    try:
        response = requests.get(
            OPEN_METEO_ARCHIVE_URL, params=params, timeout=API_TIMEOUT_SECONDS
        )
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)

        api_data = response.json()
        # Basic validation of the API response structure
        if not api_data.get("daily") or not isinstance(
            api_data["daily"].get("time"), list
        ):
            print(
                f"Warning: API response for {year} at ({latitude},{longitude}) lacks 'daily' data or 'time' array is not a list."
            )
            return None

        # Cache the raw API data
        cache.set(cache_key, api_data, WEATHER_CACHE_DURATION)
        return api_data

    except requests.exceptions.RequestException as e:
        print(f"API Request Error for {year} at ({latitude},{longitude}): {e}")
        return None
    except (
        ValueError
    ) as e:  # Handles JSON decoding errors if response is not valid JSON
        print(f"API JSON Decode Error for {year} at ({latitude},{longitude}): {e}")
        return None


def _create_and_prepare_daily_dataframe(
    api_data_json: Optional[APIResponseDict],
) -> Optional[pd.DataFrame]:
    """
    Converts raw API JSON data into a prepared Pandas DataFrame for daily weather.

    Args:
        api_data_json: The raw API response JSON.

    Returns:
        A prepared DataFrame or None if input is invalid or processing fails.
    """
    if not api_data_json or "daily" not in api_data_json:
        print("Warning: Invalid or empty API data provided for DataFrame creation.")
        return None

    try:
        # Create DataFrame only with required columns to reduce memory usage
        required_cols = ["time", "temperature_2m_mean", "precipitation_sum"]
        df_data = {col: api_data_json["daily"].get(col, []) for col in required_cols}

        # Check if all required columns exist
        if not all(col in df_data for col in required_cols):
            print(
                f"Warning: DataFrame from API is missing one or more required columns: {required_cols}"
            )
            return None

        # Create DataFrame with optimized approach
        df = pd.DataFrame(df_data)

        # Convert time column to datetime more efficiently
        df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d", errors="coerce")

        # Convert numeric columns with optimized approach
        for col in ["temperature_2m_mean", "precipitation_sum"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Drop rows where essential data became NaN after coercion
        df = df.dropna(subset=["temperature_2m_mean", "precipitation_sum"])

        if df.empty:
            print(
                "Warning: DataFrame became empty after cleaning (dropna). This means no valid daily entries were found for the period."
            )
            return None  # Explicitly return None if no data remains

        # Set index more efficiently
        df = df.set_index("time")
        return df

    except KeyError as e:
        print(f"DataFrame Creation Error: Missing expected key in API data: {e}")
        return None
    except Exception as e:  # Catch any other pandas-related errors
        print(f"DataFrame Creation/Preparation Error: {e}")
        return None


@memoize
def _aggregate_daily_data_to_monthly(
    daily_df: Optional[pd.DataFrame], year: int
) -> MonthlyDataList:
    """
    Aggregates a DataFrame of daily weather data to monthly averages/sums.

    Args:
        daily_df: DataFrame containing daily weather data.
        year: The year for which data is being aggregated.

    Returns:
        A list of dictionaries, one for each month. Returns empty list on error or if no data.
    """
    if daily_df is None or daily_df.empty:
        return []

    try:
        # Use more efficient resampling with vectorized operations
        monthly_stats = daily_df.resample("ME").agg(
            {"temperature_2m_mean": "mean", "precipitation_sum": "sum"}
        )

        # Pre-create the result list with None values
        monthly_results = [
            {"month": m, "avg_temp": None, "total_precip": None} for m in range(1, 13)
        ]

        # Update only the months we have data for
        for date, row in monthly_stats.iterrows():
            month = date.month
            monthly_results[month - 1].update(
                {
                    "avg_temp": (
                        round(row["temperature_2m_mean"], 2)
                        if pd.notnull(row["temperature_2m_mean"])
                        else None
                    ),
                    "total_precip": (
                        round(row["precipitation_sum"], 2)
                        if pd.notnull(row["precipitation_sum"])
                        else None
                    ),
                }
            )

        return monthly_results

    except Exception as e:
        print(f"Error during monthly aggregation: {e}")
        return []


# --- Weather Icon Constants ---
ICON_CLOUD_DRIZZLE = "fas fa-cloud-drizzle"
ICON_CLOUD_RAIN = "fas fa-cloud-rain"
ICON_CLOUD_SHOWERS_HEAVY = "fas fa-cloud-showers-heavy"
ICON_SNOWFLAKE = "fas fa-snowflake"
ICON_BOLT = "fas fa-bolt"

# --- Weather Code to Icon Mapping ---
WEATHER_CODE_ICONS = {
    0: "fas fa-sun",  # Clear sky
    1: "fas fa-sun",  # Mainly clear
    2: "fas fa-cloud-sun",  # Partly cloudy
    3: "fas fa-cloud",  # Overcast
    45: "fas fa-smog",  # Fog
    48: "fas fa-smog",  # Depositing rime fog
    51: ICON_CLOUD_DRIZZLE,  # Light drizzle
    53: ICON_CLOUD_DRIZZLE,  # Moderate drizzle
    55: ICON_CLOUD_DRIZZLE,  # Dense drizzle
    56: ICON_CLOUD_DRIZZLE,  # Light freezing drizzle
    57: ICON_CLOUD_DRIZZLE,  # Dense freezing drizzle
    61: ICON_CLOUD_RAIN,  # Slight rain
    63: ICON_CLOUD_RAIN,  # Moderate rain
    65: ICON_CLOUD_SHOWERS_HEAVY,  # Heavy rain
    66: ICON_CLOUD_RAIN,  # Light freezing rain
    67: ICON_CLOUD_SHOWERS_HEAVY,  # Heavy freezing rain
    71: ICON_SNOWFLAKE,  # Slight snow fall
    73: ICON_SNOWFLAKE,  # Moderate snow fall
    75: ICON_SNOWFLAKE,  # Heavy snow fall
    77: ICON_SNOWFLAKE,  # Snow grains
    80: ICON_CLOUD_RAIN,  # Slight rain showers
    81: ICON_CLOUD_RAIN,  # Moderate rain showers
    82: ICON_CLOUD_SHOWERS_HEAVY,  # Violent rain showers
    85: ICON_SNOWFLAKE,  # Slight snow showers
    86: ICON_SNOWFLAKE,  # Heavy snow showers
    95: ICON_BOLT,  # Thunderstorm
    96: ICON_BOLT,  # Thunderstorm with slight hail
    99: ICON_BOLT,  # Thunderstorm with heavy hail
}

WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


# --- Current Weather Functions ---
def get_current_weather_data(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    Fetches current weather data from Open-Meteo API.
    
    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        
    Returns:
        Dictionary with current weather data or None if failed.
    """
    # Apply rate limiting
    OPEN_METEO_RATE_LIMITER.wait_if_needed()
    
    # Create cache key for current weather (shorter cache duration)
    cache_key = f"current_weather_{latitude}_{longitude}"
    
    # Try to get from cache (shorter duration for current weather)
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_METRICS,
        "timezone": "auto",
        "forecast_days": 1
    }
    
    try:
        response = requests.get(
            OPEN_METEO_CURRENT_URL, params=params, timeout=API_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        
        api_data = response.json()
        
        if not api_data.get("current"):
            print(f"Warning: No current weather data in API response for ({latitude},{longitude})")
            return None
            
        current_data = api_data["current"]
        
        # Extract and process current weather data
        weather_code = current_data.get("weathercode", 0)
        
        result = {
            "temperature": round(current_data.get("temperature_2m", 0), 1),
            "humidity": round(current_data.get("relativehumidity_2m", 0)),
            "wind_speed": round(current_data.get("windspeed_10m", 0), 1),
            "wind_direction": current_data.get("winddirection_10m", 0),
            "weather_code": weather_code,
            "weather_icon": WEATHER_CODE_ICONS.get(weather_code, "fas fa-question"),
            "weather_description": WEATHER_CODE_DESCRIPTIONS.get(weather_code, "Unknown"),
            "temp_unit": api_data.get("current_units", {}).get("temperature_2m", "°C"),
            "wind_unit": api_data.get("current_units", {}).get("windspeed_10m", "km/h"),
            "timestamp": current_data.get("time", "")
        }
        
        # Cache for 10 minutes (current weather changes frequently)
        cache.set(cache_key, result, 600)
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Current weather API request error for ({latitude},{longitude}): {e}")
        return None
    except ValueError as e:
        print(f"Current weather JSON decode error for ({latitude},{longitude}): {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching current weather for ({latitude},{longitude}): {e}")
        return None


def _get_data_for_month(all_monthly_data: List[Dict], month: int) -> Dict[str, Optional[float]]:
    """
    Extract and calculate averages for a specific month from all data points.
    
    Args:
        all_monthly_data: List of all monthly data points
        month: Month number (1-12)
        
    Returns:
        Dictionary with month, avg_temp and total_precip
    """
    # Extract values for this month
    temps = []
    precips = []
    
    for data in all_monthly_data:
        if data["month"] == month:
            if data["avg_temp"] is not None:
                temps.append(data["avg_temp"])
            if data["total_precip"] is not None:
                precips.append(data["total_precip"])
    
    # Calculate averages
    avg_temp = round(sum(temps) / len(temps), 2) if temps else None
    avg_precip = round(sum(precips) / len(precips), 2) if precips else None
    
    return {
        "month": month,
        "avg_temp": avg_temp,
        "total_precip": avg_precip
    }


def get_historical_5year_average_data(
    latitude: float, longitude: float, end_year: int = None, num_years: int = 5
) -> Optional[WeatherDataDict]:
    """
    Fetches and processes historical weather data for multiple years,
    calculating 5-year averages for monthly data.
    
    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        end_year: The last year to include (defaults to current year - 1).
        num_years: Number of years to average (default 5).
        
    Returns:
        Dictionary with 5-year averaged monthly data or None if failed.
    """
    # Set default end year if not provided
    if end_year is None:
        end_year = datetime.now().year - 1
    
    start_year = end_year - num_years + 1
    
    # Check cache first
    cache_key = f"weather_5year_{latitude}_{longitude}_{start_year}_{end_year}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Collect data from all years
    all_data = []
    temp_unit = DEFAULT_TEMP_UNIT
    precip_unit = DEFAULT_PRECIP_UNIT
    
    # Get data for each year in range
    for year in range(start_year, end_year + 1):
        year_data = get_historical_annual_data_by_month(latitude, longitude, year)
        
        # Skip years with no data
        if not year_data or not year_data.get("monthly_data"):
            continue
            
        # Add this year's data to our collection
        all_data.extend(year_data["monthly_data"])
        
        # Use units from first successful response
        if temp_unit == DEFAULT_TEMP_UNIT:
            temp_unit = year_data.get("temp_unit", DEFAULT_TEMP_UNIT)
            precip_unit = year_data.get("precip_unit", DEFAULT_PRECIP_UNIT)
    
    # Return None if no data was collected
    if not all_data:
        print(f"No historical data for {num_years}-year average at ({latitude},{longitude})")
        return None
    
    # Calculate averages for each month
    monthly_averages = [_get_data_for_month(all_data, month) for month in range(1, 13)]
    
    # Create result dictionary
    result = {
        "monthly_data": monthly_averages,
        "temp_unit": temp_unit,
        "precip_unit": precip_unit,
        "year_range": f"{start_year}-{end_year}"
    }
    
    # Cache the result
    cache.set(cache_key, result, WEATHER_CACHE_DURATION * 7)
    
    return result


# --- Main Public Function ---
def get_historical_annual_data_by_month(
    latitude: float, longitude: float, year: int
) -> Optional[WeatherDataDict]:
    """
    Fetches and processes daily historical weather data for an entire year,
    aggregating it into monthly averages for temperature and total precipitation.

    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        year: The year for which to fetch data.

    Returns:
        A dictionary containing 'monthly_data' (list of 12 monthly stats),
        'temp_unit', 'precip_unit'. Returns None if critical failure (e.g., API down).
        'monthly_data' will be an empty list if aggregation fails or no usable data.
    """
    # Create a unique cache key based on parameters
    cache_key = f"weather_data_{latitude}_{longitude}_{year}"

    # Try to get data from cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    raw_api_data = _fetch_raw_annual_data_from_api(latitude, longitude, year)
    if not raw_api_data:
        return (
            None  # Critical failure in fetching data (API error, network issue, etc.)
        )

    daily_df = _create_and_prepare_daily_dataframe(raw_api_data)
    # If daily_df is None here, it means the data from API was unusable or became empty after cleaning.
    # We still want to return the units if possible, but monthly_data will be empty.

    monthly_aggregated_data = []  # Default to empty list
    if daily_df is not None:  # Only attempt aggregation if DataFrame is valid
        monthly_aggregated_data = _aggregate_daily_data_to_monthly(daily_df, year)
    else:
        print(
            f"Info: DataFrame preparation failed or resulted in empty data for {year} at ({latitude},{longitude}). No monthly aggregation performed."
        )

    # Extract units from the raw API data (if available, even if DataFrame prep failed)
    temp_unit = raw_api_data.get("daily_units", {}).get(
        "temperature_2m_mean", DEFAULT_TEMP_UNIT
    )
    precip_unit = raw_api_data.get("daily_units", {}).get(
        "precipitation_sum", DEFAULT_PRECIP_UNIT
    )

    result = {
        "monthly_data": monthly_aggregated_data,  # This list might be empty
        "temp_unit": temp_unit,
        "precip_unit": precip_unit,
    }

    # Store in cache
    cache.set(cache_key, result, WEATHER_CACHE_DURATION)

    return result


# --- Test Block ---
if __name__ == "__main__":
    print("--- Testing Geocoding Function ---")
    city1 = "london"  # Test lowercase
    coords1 = get_coordinates_for_city(city1)
    if coords1:
        print(
            f"Coordinates for '{city1.title()}': Lat={coords1['latitude']}, Lon={coords1['longitude']}, Address: {coords1['address']}"
        )
    else:
        print(f"Could not find coordinates for '{city1.title()}'.")

    city2 = "NonExistentCity123XYZ"
    coords2 = get_coordinates_for_city(city2)
    if coords2:
        print(f"Coordinates for '{city2}': {coords2}")  # Should not happen
    else:
        print(f"Correctly failed to find coordinates for '{city2}'.")

    city3 = ""  # Test empty string
    coords3 = get_coordinates_for_city(city3)
    if coords3:
        print(f"Coordinates for empty city string: {coords3}")  # Should not happen
    else:
        print("Correctly handled empty city string for geocoding.")

    print("\n--- Testing Annual Historical Weather Data ---")
    # Test with valid coordinates (e.g., for London from previous geocoding test)
    if coords1:
        test_lat = coords1["latitude"]
        test_lon = coords1["longitude"]
        test_year = 2022  # A recent full year

        print(
            f"\nFetching annual data for London ({test_lat}, {test_lon}) for {test_year}..."
        )
        annual_data_london = get_historical_annual_data_by_month(
            test_lat, test_lon, test_year
        )

        if annual_data_london:
            print(f"Data received for London, {test_year}:")
            print(f"  Temperature Unit: {annual_data_london['temp_unit']}")
            print(f"  Precipitation Unit: {annual_data_london['precip_unit']}")
            if annual_data_london["monthly_data"]:
                for month_data in annual_data_london["monthly_data"]:
                    print(
                        f"  Month {month_data['month']:02d}: Avg Temp={month_data['avg_temp']}, Total Precip={month_data['total_precip']}"
                    )
            else:
                print(
                    "  Monthly data list is empty. This might be due to data quality or processing issues for this specific year/location."
                )
        else:
            print(
                f"Could not retrieve any annual weather data for London for {test_year} (Critical API or initial processing failure)."
            )

    else:
        print("\nSkipping weather data test as initial geocoding for London failed.")

    # Test with known problematic coordinates or year (e.g., latitude out of bounds)
    print("\nFetching data for invalid coordinates (e.g., on Mars)...")
    invalid_coords_data = get_historical_annual_data_by_month(
        latitude=0, longitude=0, year=2022
    )  # Middle of ocean
    if invalid_coords_data and invalid_coords_data["monthly_data"]:
        print(
            "Data received for (0,0), 2022 (unexpected for invalid location, check API response):"
        )
    elif invalid_coords_data and not invalid_coords_data["monthly_data"]:
        print(
            "API call for (0,0), 2022 was made, units might be present, but no monthly data aggregated (expected for invalid location)."
        )
        print(
            f"  Temp Unit: {invalid_coords_data['temp_unit']}, Precip Unit: {invalid_coords_data['precip_unit']}"
        )
    else:
        print(
            "Correctly failed to retrieve or process data for invalid coordinates (0,0), 2022 (e.g. API returned error)."
        )
