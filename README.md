# WeatherCompare (Proof of Concept)

WeatherCompare is a Django-based web application that allows users to compare weather data between different cities. This is a proof of concept and is not intended for production use.

## Core Features

- Compare weather data between cities
- Autocomplete search for city names
- Responsive web interface

## Tech Stack

- Backend: Django 5.2.1
- Database: SQLite (for development)
- Frontend: HTML, CSS, JavaScript


## Setup and Installation

### Prerequisites

- Python 3.8+
- pip
- git

### Step 1: Clone the Repository

```bash
git clone https://github.com/Ctr1A1tDe1/WeatherCompare.git
cd WeatherCompare
```

### Step 2: Create and Activate a Virtual Environment

```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

### Step 3: Install Dependencies

Make sure you are in the root dir in cmd
```bash
pip install -r requirements.txt
```

### Step 4: Generate a New SECRET_KEY

```bash
python manage.py generatesecretkey
```

This will output a new secret key. Copy it and create a `.env` file in the project root with the following content:

```
SECRET_KEY=your_generated_secret_key_here
```

### Step 5: Create the City Autocomplete Database

```bash
python dbscript/create_autocomplete_db.py
```

### Step 6: Run Django Migrations

```bash
python manage.py migrate
```

### Step 7: Run the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

## Contributing

Please read `CONTRIBUTING.md` for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the `LICENCE.md` file for details.
