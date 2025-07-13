import sqlite3
import json
import os

def create_autocomplete_db():
    """
    Reads city data from a JSON file and creates a SQLite database
    for city name autocompletion.
    """
    db_path = os.path.join(os.path.dirname(__file__), '..', 'cities_autocomplete.db')
    json_path = os.path.join(os.path.dirname(__file__), '..', 'city.list.json')

    if os.path.exists(db_path):
        print(f"Database already exists at {db_path}")
        return

    print("Creating city autocomplete database...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create table
    c.execute('''
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY,
            name TEXT,
            state TEXT,
            country TEXT,
            coord_lon REAL,
            coord_lat REAL
        )
    ''')

    # Insert data from JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        cities = json.load(f)
        for city in cities:
            c.execute('''
                INSERT INTO cities (id, name, state, country, coord_lon, coord_lat)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                city.get('id'),
                city.get('name'),
                city.get('state'),
                city.get('country'),
                city.get('coord', {}).get('lon'),
                city.get('coord', {}).get('lat')
            ))

    conn.commit()
    conn.close()
    print("City autocomplete database created successfully.")

if __name__ == '__main__':
    create_autocomplete_db()
