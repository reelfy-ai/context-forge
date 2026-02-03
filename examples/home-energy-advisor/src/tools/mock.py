"""Mock tool responses for testing and offline development."""

from datetime import datetime

from src.core.models import (
    CurrentWeather,
    ForecastDay,
    RatePeriod,
    RateSchedule,
    SolarEstimate,
    WeatherForecast,
    WeatherLocation,
)


def mock_weather_forecast(lat: float = 37.7749, lon: float = -122.4194, days: int = 1) -> WeatherForecast:
    """Return realistic mock weather data for San Francisco."""
    forecast_days = []
    for i in range(days):
        forecast_days.append(ForecastDay(
            date=f"2026-01-{21+i:02d}",
            high_f=62 + i * 2,
            low_f=48 + i,
            cloud_cover=20 + i * 10,
            conditions="partly cloudy" if i % 2 == 0 else "mostly sunny",
        ))

    cloud_cover = 20
    solar_hours = round((1 - cloud_cover / 100) * 8.5, 1)

    return WeatherForecast(
        location=WeatherLocation(lat=lat, lon=lon, city="San Francisco"),
        current=CurrentWeather(temp=18.5, cloud_cover=cloud_cover, conditions="partly cloudy"),
        forecast=forecast_days,
        solar_hours=solar_hours,
        timestamp=datetime.now().isoformat(),
        is_fallback=False,
    )


def mock_utility_rates(utility: str = "PG&E", schedule: str | None = None) -> RateSchedule:
    """Return realistic mock TOU rate data for California utilities."""
    rates_db = {
        "PG&E": {
            "E-TOU-C": RateSchedule(
                utility_name="PG&E",
                schedule_name="E-TOU-C",
                periods=[
                    RatePeriod(name="off_peak", start_hour=0, end_hour=16, rate_kwh=0.30, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                    RatePeriod(name="peak", start_hour=16, end_hour=21, rate_kwh=0.49, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                    RatePeriod(name="off_peak", start_hour=21, end_hour=24, rate_kwh=0.30, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                ],
                effective_date="2026-01-01",
            ),
            "EV-TOU-5": RateSchedule(
                utility_name="PG&E",
                schedule_name="EV-TOU-5",
                periods=[
                    RatePeriod(name="off_peak", start_hour=21, end_hour=9, rate_kwh=0.18, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                    RatePeriod(name="peak", start_hour=16, end_hour=21, rate_kwh=0.45, days=["Mon", "Tue", "Wed", "Thu", "Fri"]),
                    RatePeriod(name="partial_peak", start_hour=9, end_hour=16, rate_kwh=0.28, days=["Mon", "Tue", "Wed", "Thu", "Fri"]),
                ],
                effective_date="2026-01-01",
            ),
        },
        "SCE": {
            "TOU-D-PRIME": RateSchedule(
                utility_name="SCE",
                schedule_name="TOU-D-PRIME",
                periods=[
                    RatePeriod(name="off_peak", start_hour=21, end_hour=16, rate_kwh=0.27, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                    RatePeriod(name="peak", start_hour=16, end_hour=21, rate_kwh=0.42, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                ],
                effective_date="2026-01-01",
            ),
        },
        "SDG&E": {
            "EV-TOU-5": RateSchedule(
                utility_name="SDG&E",
                schedule_name="EV-TOU-5",
                periods=[
                    RatePeriod(name="off_peak", start_hour=0, end_hour=6, rate_kwh=0.10, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
                    RatePeriod(name="peak", start_hour=16, end_hour=21, rate_kwh=0.55, days=["Mon", "Tue", "Wed", "Thu", "Fri"]),
                    RatePeriod(name="partial_peak", start_hour=6, end_hour=16, rate_kwh=0.35, days=["Mon", "Tue", "Wed", "Thu", "Fri"]),
                ],
                effective_date="2026-01-01",
            ),
        },
    }

    utility_upper = utility.upper().replace(" ", "")
    for key in rates_db:
        if key.upper().replace(" ", "") == utility_upper:
            utility_data = rates_db[key]
            if schedule and schedule in utility_data:
                return utility_data[schedule]
            return next(iter(utility_data.values()))

    # Default fallback
    return rates_db["PG&E"]["E-TOU-C"]


def mock_solar_estimate(
    lat: float = 37.7749,
    lon: float = -122.4194,
    system_capacity_kw: float = 6.0,
    tilt: float = 20.0,
    azimuth: float = 180.0,
) -> SolarEstimate:
    """Return realistic mock solar production estimate."""
    solrad = 5.2
    efficiency = 0.8
    daily_kwh = system_capacity_kw * solrad * efficiency / 5.0
    annual_kwh = daily_kwh * 365

    monthly_factors = [0.06, 0.07, 0.08, 0.09, 0.10, 0.10, 0.11, 0.10, 0.09, 0.08, 0.06, 0.06]
    monthly_kwh = [round(annual_kwh * f, 1) for f in monthly_factors]

    return SolarEstimate(
        system_capacity_kw=system_capacity_kw,
        ac_annual_kwh=round(annual_kwh, 1),
        monthly_kwh=monthly_kwh,
        solrad_annual=solrad,
        capacity_factor=round(annual_kwh / (system_capacity_kw * 8760), 3),
        is_fallback=False,
    )
