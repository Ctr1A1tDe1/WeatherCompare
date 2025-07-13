"""
Database utilities for city lookup and search using the cities_autocomplete.db
"""
import sqlite3
import os
import unicodedata
from typing import Dict, List, Optional, Union, Any, Tuple
from django.conf import settings
from django.core.cache import cache

# --- Type aliases ---
CoordinatesDict = Dict[str, Union[float, str]]
CityDict = Dict[str, Any]

# --- Cache durations in seconds ---
DB_QUERY_CACHE_DURATION = 86400  # 24 hours for coordinate lookups

def normalize_text(text: str) -> str:
    """
    Converts text to lowercase and removes diacritics (accents).
    
    Args:
        text: The text to normalize
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    try:
        # Normalize to NFD form to separate base characters and diacritics
        nfkd_form = unicodedata.normalize('NFD', str(text).lower())
        # Keep only ASCII characters (removes diacritics)
        ascii_text = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        return ascii_text.strip()
    except Exception as e:
        print(f"Error normalizing text '{text}': {e}")
        return str(text).lower().strip()  # Fallback

def get_db_connection() -> sqlite3.Connection:
    """
    Creates and returns a connection to the cities database.
    
    Returns:
        SQLite database connection
    """
    db_path = os.path.join(settings.BASE_DIR, 'cities_autocomplete.db')
    return sqlite3.connect(db_path)

def get_coordinates_from_db(city_name: str) -> Optional[CoordinatesDict]:
    """
    Looks up a city name in the SQLite database and returns its coordinates.
    
    Args:
        city_name: The name of the city to look up.
        
    Returns:
        Dictionary with latitude, longitude, and formatted address, or None if not found.
    """
    if not city_name:
        print("Warning: Empty city name provided for database lookup.")
        return None
    
    # Create a cache key
    cache_key = f"city_coords_{city_name.lower().strip().replace(' ', '_')}"
    
    # Try to get from cache
    cached_coords = cache.get(cache_key)
    if cached_coords:
        return cached_coords
    
    # Normalize the search term
    search_term = normalize_text(city_name)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First try exact match on name
        cursor.execute(
            """
            SELECT name, country_code, cou_name_en, latitude, longitude, admin1_code
            FROM cities 
            WHERE LOWER(name) = ? 
            ORDER BY population DESC LIMIT 1
            """, 
            (city_name.lower(),)
        )
        
        result = cursor.fetchone()
        
        # If no exact match, try search against search_text
        if not result:
            cursor.execute(
                """
                SELECT name, country_code, cou_name_en, latitude, longitude, admin1_code
                FROM cities 
                WHERE search_text LIKE ? 
                ORDER BY population DESC LIMIT 1
                """, 
                (f"%{search_term}%",)
            )
            result = cursor.fetchone()
            
        conn.close()
        
        if result:
            city_name, country_code, country_name, lat, lon, _ = result
            
            # Format address based on available data
            address_parts = []
            if city_name:
                address_parts.append(city_name)
            if country_name:
                address_parts.append(country_name)
            elif country_code:
                address_parts.append(country_code)
                
            address = ", ".join(address_parts)
            
            result_dict = {
                "latitude": lat,
                "longitude": lon,
                "address": address,
            }
            
            # Cache for future use
            cache.set(cache_key, result_dict, DB_QUERY_CACHE_DURATION)
            return result_dict
        
        print(f"Info: Could not find city '{city_name}' in database.")
        return None
        
    except Exception as e:
        print(f"Error: Database lookup failed for city '{city_name}': {e}")
        return None

def search_cities(query: str, limit: int = 10) -> List[Dict[str, any]]:
    """
    Search for cities matching the given query.
    
    Args:
        query: The search string
        limit: Maximum number of results to return
        
    Returns:
        List of matching city dictionaries
    """
    if not query:
        # Return popular cities for empty queries
        return get_popular_cities(limit)
    
    normalized_query = normalize_text(query)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query by search_text for maximum match flexibility
        cursor.execute(
            """
            SELECT id, name, country_code, cou_name_en, admin1_code, latitude, longitude
            FROM cities 
            WHERE search_text LIKE ? 
            ORDER BY population DESC
            LIMIT ?
            """, 
            (f"%{normalized_query}%", limit)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        cities = []
        for city_id, name, country_code, country_name, admin1, lat, lon in results:
            # Build location label
            location = name
            if country_name:
                location += f", {country_name}"
            elif country_code:
                location += f", {country_code}"
                
            cities.append({
                'id': city_id,
                'name': name,
                'country': country_code or "",
                'latitude': lat,
                'longitude': lon,
                'location': location
            })
            
        return cities
        
    except Exception as e:
        print(f"Error: City search failed for query '{query}': {e}")
        return []

def get_popular_cities(limit: int = 10) -> List[Dict[str, any]]:
    """
    Returns a list of popular cities sorted by population.
    
    Args:
        limit: Maximum number of cities to return
        
    Returns:
        List of city dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, name, country_code, cou_name_en, admin1_code, latitude, longitude
            FROM cities 
            ORDER BY population DESC
            LIMIT ?
            """, 
            (limit,)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        cities = []
        for city_id, name, country_code, country_name, admin1, lat, lon in results:
            # Build location label
            location = name
            if country_name:
                location += f", {country_name}"
            elif country_code:
                location += f", {country_code}"
                
            cities.append({
                'id': city_id,
                'name': name,
                'country': country_code or "",
                'latitude': lat,
                'longitude': lon,
                'location': location
            })
            
        return cities
        
    except Exception as e:
        print(f"Error: Failed to get popular cities: {e}")
        return []
