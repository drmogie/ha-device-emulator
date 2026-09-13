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
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import Component, DEVICE_TYPE_WEATHER, WEATHER_AUTO_OPTION, components_for, device_info_for
from .helpers import set_entity
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


class FakeWeather(FakeEntityMixin, WeatherEntity, RestoreEntity):
    """A simulated weather station that cycles through conditions.

    Restores its own condition override on startup (via extra_state_
    attributes) rather than depending on the companion select pushing it
    over after restoring its own value - weather and select are
    different platforms set up concurrently with no guaranteed order, so
    a push-only approach would silently lose the override whenever
    weather happened to finish setting up after the select did.
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
        self._attr_condition = CONDITIONS_CYCLE[0]
        self._cycle_index = 0
        self._override: str | None = None
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "weather_entity", self)

        if (last_state := await self.async_get_last_state()) is not None:
            override = last_state.attributes.get("condition_override")
            if override:
                self._override = override
                self._attr_condition = override

        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Carry the override through restarts - see async_added_to_hass."""
        return {"condition_override": self._override} if self._override else {}

    @callback
    def set_condition_override(self, option: str) -> None:
        """Called by the companion select entity when the user picks a condition."""
        self._override = None if option == WEATHER_AUTO_OPTION else option
        if self._override:
            self._attr_condition = self._override
            self.async_write_ha_state()

    @callback
    def _tick(self, now) -> None:
        if self._override is None:
            self._cycle_index = (self._cycle_index + 1) % len(CONDITIONS_CYCLE)
            self._attr_condition = CONDITIONS_CYCLE[self._cycle_index]
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
        return [
            Forecast(
                datetime=(dt_util.utcnow() + timedelta(days=i)).isoformat(),
                native_temperature=round(base + random.uniform(-5, 5), 1),
                native_templow=round(base - 10 + random.uniform(-3, 3), 1),
                condition=self._override
                or CONDITIONS_CYCLE[(self._cycle_index + i) % len(CONDITIONS_CYCLE)],
                precipitation_probability=random.randint(0, 60),
            )
            for i in range(5)
        ]

    async def async_forecast_hourly(self) -> list[Forecast]:
        base = self._attr_native_temperature
        return [
            Forecast(
                datetime=(dt_util.utcnow() + timedelta(hours=i)).isoformat(),
                native_temperature=round(base + random.uniform(-3, 3), 1),
                condition=self._override
                or CONDITIONS_CYCLE[(self._cycle_index + i) % len(CONDITIONS_CYCLE)],
                precipitation_probability=random.randint(0, 40),
            )
            for i in range(24)
        ]
