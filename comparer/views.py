from django.shortcuts import render
import json
from datetime import datetime
from .weather_utils import get_historical_annual_data_by_month, get_coordinates_for_city

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


def _get_initial_context():
    """Initializes and returns the base context dictionary for the view."""
    current_year = datetime.now().year
    return {
        "current_year": current_year,
        "default_selection_year": current_year + DEFAULT_YEAR_OFFSET,
        "selected_year": current_year + DEFAULT_YEAR_OFFSET,
        "form_submitted": False,
        "month_labels_for_chart": MONTH_NAMES,
        "city_data_for_chart": [],
        "error_message": None,
        "submitted_city1": "",
        "submitted_city2": "",
        "city_details_for_display": [],
    }


def _parse_form_input(request_post):
    """
    Parses and validates form inputs from the POST request.
    Returns a tuple: (city1_name, city2_name, selected_year, error_message)
    """
    city1_name = request_post.get("city_name_1", "").strip().title()
    city2_name = request_post.get("city_name_2", "").strip().title()
    error_message = None
    selected_year = None

    try:
        selected_year = int(request_post.get("year"))
    except (ValueError, TypeError):
        error_message = "Invalid year submitted. Please enter a numeric value."
        # Default to a sensible year if conversion fails, to prevent further errors
        selected_year = datetime.now().year + DEFAULT_YEAR_OFFSET

    if not error_message and (not city1_name or not city2_name):
        error_message = "Please enter names for both cities."

    return city1_name, city2_name, selected_year, error_message


def _fetch_and_process_city_weather_data(city_name, year):
    """
    Geocodes a city and fetches its annual historical weather data.
    Returns a dictionary with city details, weather data, or an error message.
    """
    city_processing_result = {
        "name": city_name,
        "address": None,
        "error": None,
        "weather_data_raw": None,  # To hold the direct output from weather_utils
        "temp_unit": "°C",  # Default units
        "precip_unit": "mm",  # Default units
    }

    if not city_name:  # Should be caught by _parse_form_input, but as a safeguard
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
    city_processing_result["temp_unit"] = annual_weather_data.get("temp_unit", "°C")
    city_processing_result["precip_unit"] = annual_weather_data.get("precip_unit", "mm")

    return city_processing_result


def index_view(request):
    context = _get_initial_context()

    if request.method == "POST":
        context["form_submitted"] = True
        city1_name, city2_name, selected_year, form_error = _parse_form_input(
            request.POST
        )

        context["submitted_city1"] = city1_name
        context["submitted_city2"] = city2_name
        context["selected_year"] = selected_year

        if form_error:
            context["error_message"] = form_error
            # context['city_data_for_chart'] is already [] from _get_initial_context
            return render(request, "comparer/index.html", context)

        city1_processed_data = _fetch_and_process_city_weather_data(
            city1_name, selected_year
        )
        city2_processed_data = _fetch_and_process_city_weather_data(
            city2_name, selected_year
        )

        context["city_details_for_display"] = [
            city1_processed_data,
            city2_processed_data,
        ]

        chart_data_for_python_list = []  # Use a different name to avoid confusion
        if city1_processed_data.get("weather_data_raw"):
            chart_data_for_python_list.append(
                {
                    "name": city1_processed_data["name"],
                    "temperatures": [
                        m["avg_temp"] for m in city1_processed_data["weather_data_raw"]
                    ],
                    "precipitations": [
                        m["total_precip"]
                        for m in city1_processed_data["weather_data_raw"]
                    ],
                    "temp_unit": city1_processed_data["temp_unit"],
                    "precip_unit": city1_processed_data["precip_unit"],
                }
            )

        if city2_processed_data.get("weather_data_raw"):
            chart_data_for_python_list.append(
                {
                    "name": city2_processed_data["name"],
                    "temperatures": [
                        m["avg_temp"] for m in city2_processed_data["weather_data_raw"]
                    ],
                    "precipitations": [
                        m["total_precip"]
                        for m in city2_processed_data["weather_data_raw"]
                    ],
                    "temp_unit": city2_processed_data["temp_unit"],
                    "precip_unit": city2_processed_data["precip_unit"],
                }
            )

        # Pass the Python list directly to the context for json_script
        context["city_data_for_chart"] = chart_data_for_python_list

        if not chart_data_for_python_list and not form_error:  # Check the Python list
            all_errors = [
                d["error"] for d in context["city_details_for_display"] if d["error"]
            ]
            if len(all_errors) == 2:
                context["error_message"] = (
                    "Could not generate chart data. Weather data might be unavailable or city names incorrect for both entries."
                )
    # For GET requests, month_labels_for_chart and city_data_for_chart (as []) are already set by _get_initial_context

    return render(request, "comparer/index.html", context)
