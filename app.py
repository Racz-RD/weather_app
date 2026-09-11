import logging

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st
from weather_service import fetch_weather, get_weather_alerts

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤️", layout="wide")
st.title("🌤️ Weather Dashboard")
st.markdown("Real-time weather data from Open-Meteo")

locations = {
    'Dobanovci': (44.8084, 20.2346),
    'Kraljevo': (43.7295, 20.7113),
    'Nis': (43.3412, 21.8817),
    'Novi Sad': (45.2875, 19.8070),
    'Istčno Sarajevo': (43.8052, 18.3412),
    'Laktaši': (44.8841, 17.3005),
    'Bijeljina': (44.7391, 19.1787),
    'Skoplje': (42.0060, 21.5499),
    'Podgorica': (42.4156, 19.2032),
    'Danilovgrad': (42.5309, 19.1167),
    'Tirana': (41.3700,19.5592),
}

@st.fragment(run_every=900)
def render_dashboard():
    selected_locations = st.multiselect(
        "Selected locations",
        list(locations.keys()),
        default=list(locations.keys()),
    )

    if selected_locations:
        data = []
        errors = []
        for location in selected_locations:
            try:
                data.append(fetch_weather(location, locations[location]))
            except (httpx.HTTPError, KeyError, TypeError, ValueError):
                logger.warning("Could not load weather data for %s", location, exc_info=True)
                errors.append(location)

        if errors:
            for error in errors:
                st.warning(f"Could not load weather data for {error}.")

        if data:
            df = pd.DataFrame(data)
            alerts = {
                row["Location"]: get_weather_alerts(row)
                for _, row in df.iterrows()
            }
            active_alerts = [
                f"{location}: {alert}"
                for location, location_alerts in alerts.items()
                for alert in location_alerts
            ]
            st.subheader("Possible events in the next 6 hours")
            if active_alerts:
                for alert in active_alerts:
                    st.warning(alert)
            else:
                st.success("No extreme weather conditions detected.")

            st.subheader("Current conditions")
            metric_columns = st.columns(min(len(df), 4))
            for index, row in df.iterrows():
                metric_columns[index % len(metric_columns)].metric(
                    row["Location"],
                    f"{row['Temperature (°C)']}°C",
                    f"{row['Condition']} | Humidity: {row['Humidity (%)']}%",
                )

            temperature_column, wind_column = st.columns(2)
            with temperature_column:
                st.subheader("Temperature comparison")
                temperature_chart = px.bar(
                    df,
                    x="Location",
                    y="Temperature (°C)",
                    color="Location",
                )
                st.plotly_chart(temperature_chart, use_container_width=True)

            with wind_column:
                st.subheader("Wind speed comparison")
                wind_chart = px.bar(
                    df,
                    x="Location",
                    y="Wind Speed (km/h)",
                    color="Location",
                )
                st.plotly_chart(wind_chart, use_container_width=True)

            st.subheader("Weather details")
            display_columns = [
                column
                for column in df.columns
                if column != "Next 6h Weather Codes"
            ]
            st.dataframe(
                df[display_columns], use_container_width=True, hide_index=True
            )
    else:
        st.info("Select at least one location to load weather data.")


render_dashboard()