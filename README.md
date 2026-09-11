# Weather Dashboard

A Streamlit dashboard for monitoring current weather conditions and short-term weather risks across selected locations in the SEE. Data is provided by the [Open-Meteo API](https://open-meteo.com/).

## Features

- Current temperature, condition, wind, humidity, and rainfall
- Six-hour forecasts for rain, precipitation probability, wind gusts, temperature, and weather events
- Alerts for high temperatures, strong wind gusts, heavy rain, high rain probability, and severe weather codes
- Temperature and wind-speed comparison charts
- Detailed weather data table
- Cached API responses to reduce repeated requests

## Requirements

- Python 3.10 or newer
- Internet access for Open-Meteo requests

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.\venv\Scripts\Activate.ps1
```

## Run the dashboard

```bash
streamlit run app.py
```

The dashboard opens in your browser. Select one or more locations to load their current conditions and six-hour forecast data.

## Run tests

```bash
python -m unittest
```

The tests mock the Open-Meteo response, so they do not require network access.

## Project structure

- `app.py` - Streamlit user interface, location list, charts, and data table
- `weather_service.py` - Open-Meteo API client, caching, forecast processing, and alert rules
- `test.py` - Unit tests for forecast processing and alert generation
- `requirements.txt` - Pinned Python dependencies

## Data source

Weather data comes from Open-Meteo's forecast endpoint. No API key is required for the current configuration.
