from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from datetime import datetime
import json
import os
import asyncio
import concurrent.futures
from typing import Dict, List, Tuple, Optional, Any, Union
from .weather_utils import (
    get_historical_annual_data_by_month, 
    get_coordinates_for_city,
    get_current_weather_data,
    get_historical_5year_average_data
)

# --- Constants ---
MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
DEFAULT_TEMP_UNIT = "°C"
DEFAULT_PRECIP_UNIT = "mm"

# --- Type aliases ---
ContextDict = Dict[str, Any]
CityProcessingResult = Dict[str, Any]
ChartDataItem = Dict[str, Union[str, List[float]]]
WeatherCardData = Dict[str, Any]


def _get_initial_context() -> ContextDict:
    """
    Initializes and returns the base context dictionary for the view.

    Returns:
        A dictionary with initial context values.
    """
    current_year = datetime.now().year
    
    return {
        "current_year": current_year,
        "form_submitted": False,
        "month_labels_for_chart": MONTH_NAMES,
        "city_data_for_chart": [],
        "weather_cards_data": [],
        "error_message": None,
        "submitted_city1": "",
        "submitted_city2": "",
        "submitted_city3": "",
    }


def _parse_form_input(request_post: Dict) -> Tuple[List[str], Optional[str]]:
    """
    Parses and validates form inputs from the POST request.

    Args:
        request_post: The POST data from the request.

    Returns:
        A tuple containing: (list of city names, error_message)
    """
    error_message = None
    city_names = []
    
    # Process city 1 (always required)
    city1_name = request_post.get("city_name_1", "").strip().title()
    if not city1_name:
        return [], "Please enter a name for City 1."
        
    city_names.append(city1_name)
    
    # Process city 2 (if provided)
    city2_name = request_post.get("city_name_2", "").strip().title()
    if city2_name:
        city_names.append(city2_name)
    
    # Process city 3 (if provided)
    city3_name = request_post.get("city_name_3", "").strip().title()
    if city3_name:
        city_names.append(city3_name)
    
    return city_names, error_message


def _get_wind_direction_text(degrees: float) -> str:
    """
    Convert wind direction degrees to compass direction text.
    
    Args:
        degrees: Wind direction in degrees (0-360)
        
    Returns:
        Compass direction string (e.g., "N", "NE", "SW")
    """
    if degrees is None:
        return "N/A"
    
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    # Normalize degrees to 0-360 range
    degrees = degrees % 360
    
    # Calculate index (16 directions, so 360/16 = 22.5 degrees per direction)
    index = round(degrees / 22.5) % 16
    
    return directions[index]


def _process_city_data(city_name: str) -> Tuple[Optional[WeatherCardData], Optional[ChartDataItem]]:
    """
    Process a single city to get both current weather and historical data.
    
    Args:
        city_name: Name of the city to process
        
    Returns:
        Tuple of (weather_card_data, chart_data) - either can be None if failed
    """
    # Input validation and sanitization
    if not city_name or not isinstance(city_name, str):
        return None, None
    
    # Sanitize city name to prevent injection attacks
    city_name = city_name.strip()[:100]  # Limit length
    if not city_name:
        return None, None
    
    # Get coordinates
    coordinates = get_coordinates_for_city(city_name)
    if not coordinates:
        print(f"Could not find coordinates for '{city_name}'")
        return None, None
    
    latitude = coordinates["latitude"]
    longitude = coordinates["longitude"]
    address = coordinates.get("address", "")
    
    # Initialize result containers
    weather_card_data = None
    chart_data = None
    
    # Get current weather for the card
    try:
        current_weather = get_current_weather_data(latitude, longitude)
        if current_weather:
            # Get current date info
            now = datetime.now()
            day_name = now.strftime("%a")
            day_number = now.strftime("%d")
            
            # Format wind direction
            wind_dir_text = _get_wind_direction_text(current_weather.get("wind_direction", 0))
            wind_speed = current_weather.get("wind_speed", 0)
            wind_unit = current_weather.get("wind_unit", "km/h")
            
            weather_card_data = {
                "name": city_name,
                "address": address,
                "day_date": f"{day_name} {day_number} | Day",
                "temperature": current_weather.get("temperature", 0),
                "temp_unit": current_weather.get("temp_unit", "°C"),
                "humidity": current_weather.get("humidity", 0),
                "wind_speed": wind_speed,
                "wind_direction": wind_dir_text,
                "wind_unit": wind_unit,
                "wind_display": f"{wind_dir_text} {wind_speed} {wind_unit}",
                "weather_icon": current_weather.get("weather_icon", "fas fa-question"),
                "weather_description": current_weather.get("weather_description", "Unknown conditions"),
                "error": None
            }
    except Exception as e:
        print(f"Error fetching current weather for {city_name}: {e}")
        weather_card_data = {
            "name": city_name,
            "address": address,
            "error": f"Could not fetch current weather data for {city_name}"
        }
    
    # Get 5-year historical averages for the chart
    try:
        historical_data = get_historical_5year_average_data(latitude, longitude)
        if historical_data and historical_data.get("monthly_data"):
            year_range = historical_data.get("year_range", "5-Year Average")
            
            chart_data = {
                "name": f"{city_name} ({year_range})",
                "temperatures": [m["avg_temp"] for m in historical_data["monthly_data"]],
                "precipitations": [m["total_precip"] for m in historical_data["monthly_data"]],
                "temp_unit": historical_data.get("temp_unit", DEFAULT_TEMP_UNIT),
                "precip_unit": historical_data.get("precip_unit", DEFAULT_PRECIP_UNIT),
            }
    except Exception as e:
        print(f"Error fetching historical data for {city_name}: {e}")
        # Don't set chart_data, leave it as None
    
    return weather_card_data, chart_data


def _process_cities_concurrently(city_names: List[str]) -> Tuple[List[WeatherCardData], List[ChartDataItem], List[str]]:
    """
    Process multiple cities concurrently for better performance.
    
    Args:
        city_names: List of city names to process
        
    Returns:
        Tuple of (weather_cards_data, chart_data_list, processing_errors)
    """
    weather_cards_data = []
    chart_data_list = []
    processing_errors = []
    
    # Use ThreadPoolExecutor for concurrent processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all city processing tasks
        future_to_city = {
            executor.submit(_process_city_data, city_name): city_name 
            for city_name in city_names
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_city):
            city_name = future_to_city[future]
            try:
                weather_card, chart_data = future.result()
                
                # Add weather card data (even if it has errors)
                if weather_card:
                    weather_cards_data.append(weather_card)
                else:
                    # Create error card if processing completely failed
                    weather_cards_data.append({
                        "name": city_name,
                        "error": f"Could not process data for {city_name}"
                    })
                
                # Add chart data if available
                if chart_data:
                    chart_data_list.append(chart_data)
                else:
                    processing_errors.append(f"No historical data available for {city_name}")
                    
            except Exception as e:
                print(f"Unexpected error processing {city_name}: {e}")
                processing_errors.append(f"Error processing {city_name}")
                weather_cards_data.append({
                    "name": city_name,
                    "error": f"Unexpected error processing {city_name}"
                })
    
    # Sort results to maintain original order
    def get_city_order(item):
        city_name = item.get("name", "").split(" (")[0]  # Remove year range suffix for chart data
        try:
            return city_names.index(city_name)
        except ValueError:
            return len(city_names)  # Put unmatched items at the end
    
    weather_cards_data.sort(key=get_city_order)
    chart_data_list.sort(key=get_city_order)
    
    return weather_cards_data, chart_data_list, processing_errors


def index_view(request):
    """
    Main view function for the weather comparison page.

    Args:
        request: The HTTP request object.

    Returns:
        Rendered HTML response.
    """
    context = _get_initial_context()

    if request.method == "POST":
        context["form_submitted"] = True
        
        # Update context with form values for re-rendering
        context["submitted_city1"] = request.POST.get("city_name_1", "").strip()
        context["submitted_city2"] = request.POST.get("city_name_2", "").strip()
        context["submitted_city3"] = request.POST.get("city_name_3", "").strip()
        
        # Parse form input
        city_names, form_error = _parse_form_input(request.POST)

        if form_error:
            context["error_message"] = form_error
            return render(request, "comparer/index.html", context)

        # Process cities concurrently for better performance
        weather_cards_data, chart_data_list, processing_errors = _process_cities_concurrently(city_names)

        context["weather_cards_data"] = weather_cards_data
        context["city_data_for_chart"] = chart_data_list

        # Set error message if no data could be processed
        if not weather_cards_data and not chart_data_list:
            context["error_message"] = "Could not process any city data. Please check city names and try again."
        elif processing_errors and not chart_data_list:
            context["error_message"] = "Could not generate charts. " + "; ".join(processing_errors)

    return render(request, "comparer/index.html", context)


def city_compare_api(request):
    """
    API endpoint for async weather and chart data loading.
    Accepts POST with city names, returns weather cards and chart data as JSON.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        city_names = data.get("cities", [])
        if not isinstance(city_names, list) or not city_names:
            return JsonResponse({"error": "No cities provided"}, status=400)
        # Limit to 3 cities for safety and capitalize each city name
        city_names = [city.strip().title() for city in city_names[:3] if city.strip()]
        weather_cards_data, chart_data_list, processing_errors = _process_cities_concurrently(city_names)
        return JsonResponse({
            "weather_cards_data": weather_cards_data,
            "city_data_for_chart": chart_data_list,
            "errors": processing_errors,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def _filter_city_data(data, query=None, limit=50):
    """
    Filter city data based on query and limit.
    
    Args:
        data: List of city dictionaries
        query: Optional search query string
        limit: Maximum number of results to return
        
    Returns:
        List of filtered city dictionaries
    """
    filtered_data = []
    
    # Determine which cities to process
    cities_to_process = data if query else data[:limit]
    
    for city in cities_to_process:
        # Stop once we reach the limit
        if len(filtered_data) >= limit:
            break
            
        try:
            # Skip if city doesn't match query
            if query and query not in city['name'].lower():
                continue
                
            # Check if the city name can be encoded in ASCII
            city['name'].encode('ascii')
            
            # Add to filtered results
            filtered_data.append({
                'id': city['id'],
                'name': city['name'],
                'state': city.get('state', ''),
                'country': city['country']
            })
        except (UnicodeEncodeError, KeyError):
            # Skip cities with non-ASCII characters or missing data
            continue
            
    return filtered_data

def city_data_view(request):
    """
    Serve city data for autocomplete functionality with optimized loading.
    
    Args:
        request: The HTTP request object.
        
    Returns:
        JsonResponse with city data.
    """
    try:
        # Path to the city list JSON file
        city_list_path = os.path.join(settings.BASE_DIR, 'city.list.json')
        
        # Check if file exists
        if not os.path.exists(city_list_path):
            return JsonResponse({'error': 'City data file not found'}, status=404)
        
        # Get query parameter for filtering
        query = request.GET.get('q', '').lower().strip()
        limit = int(request.GET.get('limit', 50))  # Limit results for better performance
        
        # Read the file
        with open(city_list_path, 'r', encoding='utf-8') as file:
            data = json.loads(file.read())
        
        # Filter the data
        filtered_data = _filter_city_data(data, query, limit)
                    
        return JsonResponse(filtered_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
