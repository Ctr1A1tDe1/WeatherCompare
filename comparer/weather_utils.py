import requests
import pandas as pd
from datetime import datetime, timedelta

def get_historical_monthly_weather(latitude, longitude, year, month):
    """
    Fetches historical weather data for a given location, year, and month,
    then calculates monthly average temperature and total precipitation.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        year (int): The year for which to fetch data.
        month (int): The month (1-12) for which to fetch data.

    Returns:
        dict: A dictionary containing 'avg_temp' and 'total_precip',
              or None if data fetching fails or data is incomplete.
    """
    # Determine the start and end dates for the specified month
    start_date_str = f"{year}-{month:02d}-01"
    
    # To get the end date, we find the first day of the next month and subtract one day
    if month == 12:
        end_date_str = f"{year}-12-31"
    else:
        next_month_start = datetime(year, month + 1, 1)
        end_of_month = next_month_start - timedelta(days=1)
        end_date_str = end_of_month.strftime('%Y-%m-%d')

    # Open-Meteo API endpoint for historical weather
    # We'll request daily average temperature and daily precipitation sum
    # Docs: https://open-meteo.com/en/docs/historical-weather-api
    api_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "daily": "temperature_2m_mean,precipitation_sum", # Daily mean temp, daily precip sum
        "timezone": "GMT" # Use GMT for consistency, can be adjusted
    }

    print(f"Requesting URL: {requests.Request('GET', api_url, params=params).prepare().url}") # For debugging

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()

        if not data.get("daily") or not data["daily"].get("time"):
            print("API response does not contain 'daily' data or 'time' array.")
            return None

        # Use pandas to easily calculate monthly aggregates
        df = pd.DataFrame(data["daily"])
        
        # Ensure the dataframe is not empty and has the required columns
        if df.empty or 'temperature_2m_mean' not in df.columns or 'precipitation_sum' not in df.columns:
            print("DataFrame is empty or missing required columns.")
            return None

        # Convert relevant columns to numeric, coercing errors to NaN
        df['temperature_2m_mean'] = pd.to_numeric(df['temperature_2m_mean'], errors='coerce')
        df['precipitation_sum'] = pd.to_numeric(df['precipitation_sum'], errors='coerce')

        # Drop rows with NaN values that might have resulted from coercion if API returned non-numeric strings
        df.dropna(subset=['temperature_2m_mean', 'precipitation_sum'], inplace=True)

        if df.empty:
            print("DataFrame became empty after dropping NaN values. Check API data quality.")
            return None

        # Calculate monthly average temperature and total precipitation
        avg_temp = df['temperature_2m_mean'].mean()
        total_precip = df['precipitation_sum'].sum()
        
        # Get units from the response for clarity
        temp_unit = data.get('daily_units', {}).get('temperature_2m_mean', '°C')
        precip_unit = data.get('daily_units', {}).get('precipitation_sum', 'mm')

        return {
            "month_year": f"{month:02d}-{year}",
            "avg_temp": round(avg_temp, 2),
            "total_precip": round(total_precip, 2),
            "temp_unit": temp_unit,
            "precip_unit": precip_unit,
            "data_points_collected": len(df) # Number of days with valid data
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None
    except KeyError as e:
        print(f"Key error when parsing API response: {e}. Data might be structured differently than expected.")
        print(f"Received data: {data}") # Log the received data for inspection
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Example of how to use this function (for testing purposes)
if __name__ == "__main__":
    # Example: London, UK coordinates
    london_lat = 51.5074
    london_lon = 0.1278
    
    # Test for January 2023
    print("\n--- Testing for Jan 2023, London ---")
    weather_data_jan = get_historical_monthly_weather(london_lat, london_lon, 2023, 1)
    if weather_data_jan:
        print(f"Weather for {weather_data_jan['month_year']}:")
        print(f"  Avg Temp: {weather_data_jan['avg_temp']} {weather_data_jan['temp_unit']}")
        print(f"  Total Precip: {weather_data_jan['total_precip']} {weather_data_jan['precip_unit']}")
        print(f"  Days with data: {weather_data_jan['data_points_collected']}")
    else:
        print("Could not retrieve weather data for Jan 2023.")

    # Test for a more recent completed month, e.g., April 2024
    # (Ensure this month has passed fully when you run it for accurate aggregation)
    current_date = datetime.now()
    # Let's get data for two months ago to ensure it's complete
    target_date = current_date - timedelta(days=60) 
    recent_year = target_date.year
    recent_month = target_date.month

    print(f"\n--- Testing for {recent_month:02d}-{recent_year}, London ---")
    weather_data_recent = get_historical_monthly_weather(london_lat, london_lon, recent_year, recent_month)
    if weather_data_recent:
        print(f"Weather for {weather_data_recent['month_year']}:")
        print(f"  Avg Temp: {weather_data_recent['avg_temp']} {weather_data_recent['temp_unit']}")
        print(f"  Total Precip: {weather_data_recent['total_precip']} {weather_data_recent['precip_unit']}")
        print(f"  Days with data: {weather_data_recent['data_points_collected']}")
    else:
        print(f"Could not retrieve weather data for {recent_month:02d}-{recent_year}.")