"""Fake weather platform - current conditions plus daily/hourly forecasts."""
from __future__ import annotations

import random
from datetime import timedelta

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import Component, DEVICE_TYPE_WEATHER, components_for, device_info_for
from .helpers import get_weather_override, set_entity
from .mixins import FakeEntityMixin

TICK = timedelta(minutes=15)
CONDITIONS_CYCLE = ["sunny", "partlycloudy", "cloudy", "rainy", "sunny"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake weather station for each Weather component."""
    async_add_entities(
        FakeWeather(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_WEATHER
    )


class FakeWeather(FakeEntityMixin, WeatherEntity):
    """A simulated weather station that cycles through conditions.

    The "Weather condition" override (see select.py's
    FakeWeatherConditionSelect) lives centrally in hass.data via
    helpers.get_weather_override/set_weather_override, owned entirely by
    that select entity - this entity only ever reads it live, on every
    state/forecast computation, rather than keeping its own copy. That
    used to be two independently-restored copies of the same value with
    no guaranteed order between their restores, which is how the
    override could get silently lost or go stale (e.g. falling back to
    "sunny", the first entry in CONDITIONS_CYCLE) after a restart, or
    fail to show up immediately when changed. Reading one shared value
    removes that whole failure mode.
    """

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_native_pressure_unit = UnitOfPressure.INHG
    _attr_native_wind_speed_unit = UnitOfSpeed.MILES_PER_HOUR
    _attr_native_visibility_unit = UnitOfLength.MILES
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_weather"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_temperature = 72.0
        self._attr_native_apparent_temperature = 74.0
        self._attr_humidity = 45
        self._attr_native_pressure = 29.92
        self._attr_native_wind_speed = 8.0
        self._attr_wind_bearing = 220
        self._attr_native_visibility = 10.0
        self._cycle_index = 0
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "weather_entity", self)
        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @property
    def condition(self) -> str | None:
        return get_weather_override(self.hass, self._component.id) or CONDITIONS_CYCLE[self._cycle_index]

    @callback
    def _tick(self, now) -> None:
        if get_weather_override(self.hass, self._component.id) is None:
            self._cycle_index = (self._cycle_index + 1) % len(CONDITIONS_CYCLE)
        self._attr_native_temperature = round(
            self._attr_native_temperature + random.uniform(-1.5, 1.5), 1
        )
        self._attr_native_apparent_temperature = round(
            self._attr_native_temperature + random.uniform(-2, 2), 1
        )
        self._attr_humidity = max(10, min(95, self._attr_humidity + random.randint(-3, 3)))
        self.async_write_ha_state()

    async def async_forecast_daily(self) -> list[Forecast]:
        base = self._attr_native_temperature
        override = get_weather_override(self.hass, self._component.id)
        return [
            Forecast(
                datetime=(dt_util.utcnow() + timedelta(days=i)).isoformat(),
                native_temperature=round(base + random.uniform(-5, 5), 1),
                native_templow=round(base - 10 + random.uniform(-3, 3), 1),
                condition=override
                or CONDITIONS_CYCLE[(self._cycle_index + i) % len(CONDITIONS_CYCLE)],
                precipitation_probability=random.randint(0, 60),
            )
            for i in range(5)
        ]

    async def async_forecast_hourly(self) -> list[Forecast]:
        base = self._attr_native_temperature
        override = get_weather_override(self.hass, self._component.id)
        return [
            Forecast(
                datetime=(dt_util.utcnow() + timedelta(hours=i)).isoformat(),
                native_temperature=round(base + random.uniform(-3, 3), 1),
                condition=override
                or CONDITIONS_CYCLE[(self._cycle_index + i) % len(CONDITIONS_CYCLE)],
                precipitation_probability=random.randint(0, 40),
            )
            for i in range(24)
        ]
