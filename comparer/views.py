from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from datetime import datetime
import json
import os
from typing import Dict, List, Tuple, Optional, Any, Union
from .weather_utils import get_historical_annual_data_by_month, get_coordinates_for_city

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
DEFAULT_YEAR_OFFSET = -1
DEFAULT_TEMP_UNIT = "°C"
DEFAULT_PRECIP_UNIT = "mm"

# --- Type aliases ---
ContextDict = Dict[str, Any]
CityProcessingResult = Dict[str, Any]
ChartDataItem = Dict[str, Union[str, List[float]]]
CityYearPair = Tuple[str, int]


def _get_initial_context() -> ContextDict:
    """
    Initializes and returns the base context dictionary for the view.

    Returns:
        A dictionary with initial context values.
    """
    current_year = datetime.now().year
    default_year = current_year + DEFAULT_YEAR_OFFSET
    
    return {
        "current_year": current_year,
        "default_selection_year": default_year,
        "form_submitted": False,
        "month_labels_for_chart": MONTH_NAMES,
        "city_data_for_chart": [],
        "error_message": None,
        "submitted_city1": "",
        "submitted_city2": "",
        "submitted_city3": "",
        "year_1": default_year,
        "year_2": default_year,
        "year_3": default_year,
        "enable_city3": False,
        "city_details_for_display": [],
    }


def _parse_form_input(request_post: Dict) -> Tuple[List[CityYearPair], Optional[str]]:
    """
    Parses and validates form inputs from the POST request.

    Args:
        request_post: The POST data from the request.

    Returns:
        A tuple containing: (list of (city_name, year) pairs, error_message)
    """
    error_message = None
    city_year_pairs = []
    current_year = datetime.now().year
    default_year = current_year + DEFAULT_YEAR_OFFSET
    
    # Process city 1 (always required)
    city1_name = request_post.get("city_name_1", "").strip().title()
    if not city1_name:
        return [], "Please enter a name for City 1."
        
    city_year_pairs.append((city1_name, default_year))
    
    # Process city 2 (if provided)
    city2_name = request_post.get("city_name_2", "").strip().title()
    if city2_name:
        city_year_pairs.append((city2_name, default_year))
    
    # Process city 3 (if provided)
    city3_name = request_post.get("city_name_3", "").strip().title()
    if city3_name:
        city_year_pairs.append((city3_name, default_year))
    
    return city_year_pairs, error_message


def _fetch_and_process_city_weather_data(
    city_name: str, year: int
) -> CityProcessingResult:
    """
    Geocodes a city and fetches its annual historical weather data.

    Args:
        city_name: The name of the city to process.
        year: The year for which to fetch weather data.

    Returns:
        A dictionary with city details, weather data, or an error message.
    """
    city_processing_result = {
        "name": city_name,
        "year": year,
        "address": None,
        "error": None,
        "weather_data_raw": None,  # To hold the direct output from weather_utils
        "temp_unit": DEFAULT_TEMP_UNIT,  # Default units
        "precip_unit": DEFAULT_PRECIP_UNIT,  # Default units
    }

    if not city_name:
        city_processing_result["error"] = "City name was empty."
        return city_processing_result

    coordinates = get_coordinates_for_city(city_name)
    if not coordinates:
        city_processing_result["error"] = (
            f"Could not find coordinates for '{city_name}'. Please check the name."
        )
        return city_processing_result

    city_processing_result["address"] = coordinates.get("address")

    annual_weather_data = get_historical_annual_data_by_month(
        coordinates["latitude"], coordinates["longitude"], year
    )

    if not annual_weather_data or not annual_weather_data.get("monthly_data"):
        city_processing_result["error"] = (
            f"Could not retrieve annual weather data for {city_name} for {year}."
        )
        return city_processing_result

    city_processing_result["weather_data_raw"] = annual_weather_data["monthly_data"]
    city_processing_result["temp_unit"] = annual_weather_data.get(
        "temp_unit", DEFAULT_TEMP_UNIT
    )
    city_processing_result["precip_unit"] = annual_weather_data.get(
        "precip_unit", DEFAULT_PRECIP_UNIT
    )

    return city_processing_result


def _prepare_chart_data(city_result: CityProcessingResult) -> Optional[ChartDataItem]:
    """
    Prepares chart data from city processing result.

    Args:
        city_result: The result from _fetch_and_process_city_weather_data.

    Returns:
        A dictionary with chart data or None if no weather data is available.
    """
    if not city_result.get("weather_data_raw"):
        return None

    return {
        "name": f"{city_result['name']} ({city_result['year']})",
        "temperatures": [m["avg_temp"] for m in city_result["weather_data_raw"]],
        "precipitations": [m["total_precip"] for m in city_result["weather_data_raw"]],
        "temp_unit": city_result["temp_unit"],
        "precip_unit": city_result["precip_unit"],
    }


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
        city_year_pairs, form_error = _parse_form_input(request.POST)

        if form_error:
            context["error_message"] = form_error
            return render(request, "comparer/index.html", context)

        # Process cities
        processed_cities = []
        chart_data_list = []

        for city_name, year in city_year_pairs:
            city_result = _fetch_and_process_city_weather_data(city_name, year)
            processed_cities.append(city_result)

            chart_data = _prepare_chart_data(city_result)
            if chart_data:
                chart_data_list.append(chart_data)

        context["city_details_for_display"] = processed_cities
        context["city_data_for_chart"] = chart_data_list

        if not chart_data_list and not form_error:
            all_errors = [d["error"] for d in processed_cities if d["error"]]
            if len(all_errors) == len(city_year_pairs):
                context["error_message"] = (
                    "Could not generate chart data. Weather data might be unavailable or city names incorrect."
                )

    return render(request, "comparer/index.html", context)


def city_data_view(request):
    """
    Serve city data for autocomplete functionality.
    
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
        
        # Read the file in chunks to handle large file size
        with open(city_list_path, 'r', encoding='utf-8') as file:
            # Read only the first 5000 cities for performance
            # In a production environment, you would implement proper pagination
            # or use a database instead of reading from a file
            data = json.loads(file.read())[:5000]
            
        # Filter out cities with non-ASCII characters that might cause display issues
        filtered_data = []
        for city in data:
            try:
                # Check if the city name can be encoded in ASCII
                city['name'].encode('ascii')
                filtered_data.append({
                    'id': city['id'],
                    'name': city['name'],
                    'state': city.get('state', ''),
                    'country': city['country']
                })
            except UnicodeEncodeError:
                # Skip cities with non-ASCII characters
                continue
                
        return JsonResponse(filtered_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
