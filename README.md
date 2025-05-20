# WeatherCompare Django App (v0.1.0)

Welcome to my repo. I am an aspiring developer, I orginally made this for my partner for helping her decide on where in the world to visit and when.
Some places are too hot and some are too cold. There is probally something better out there but I wanted to learn about programming and develop as I am teaching myself. Any help or advice is appreciated.

This Project:

Quickly compare historical annual weather (average monthly temperature & precipitation) for two cities using interactive charts.

## Core Features

*   Side-by-side annual weather comparison for two cities.
*   Year selection for historical data.
*   City name input (automatic geocoding).
*   Interactive line (temperature) and bar (precipitation) charts.

## Tech Stack

*   **Backend:** Python, Django
*   **Frontend:** HTML, CSS, JavaScript (with Chart.js)
*   **APIs:** 
    *   Nominatim (OpenStreetMap) for Geocoding
    *   Open-Meteo for Historical Weather Data

---

## Quick Start

### Prerequisites

*   Python 3.9+ & Pip
*   Git
*   Virtual Environment (e.g., `venv`)

### Setup Instructions

1.  **Clone:**
    ```bash
    git clone <https://github.com/Ctr1A1tDe1/WeatherCompare>
    cd WeatherAppProject
    ```

2.  **Virtual Environment:**
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Variables:**
    *   Copy `.env.example` to `.env`:
        ```bash
        # Windows: copy .env.example .env
        # macOS/Linux: cp .env.example .env
        ```
    *   **Edit `.env`** and update `NOMINATIM_USER_AGENT_APP_NAME` and `NOMINATIM_USER_AGENT_EMAIL` with your application name and a valid contact email (required by Nominatim's policy).

5.  **Database Migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Run Server:**
    ```bash
    python manage.py runserver
    ```
    Access at `http://127.0.0.1:8000/`

7.  **Run Tests (Optional):**
    ```bash
    python manage.py test comparer 
    ```

---

## Usage

1.  Open the app in your browser.
2.  Enter two city names and a year.
3.  Click "Compare Weather" to view the charts and data.

---

## Data Sources & Attribution

**Geocoding:** [Nominatim](https://nominatim.openstreetmap.org/) (© OpenStreetMap contributors, ODbL). 
    Adhere to [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).

**Weather Data:** [Open-Meteo API](https://open-meteo.com/en/docs/historical-weather-api) (Non-commercial use, CC BY-NC 4.0).

**Charting:** [Chart.js](https://www.chartjs.org/) (MIT Licensed).

---

## License

This project is licensed under the MIT License.
---
*v0.1.0: Test Build.*