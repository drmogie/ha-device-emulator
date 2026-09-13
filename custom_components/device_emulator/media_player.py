"""Fake media player platform - speaker, TV, or receiver, one per component.

The show_as maps straight onto MediaPlayerDeviceClass and picks a
plausible source list. Playback (title/artist/position) is simulated
against a tiny built-in playlist that auto-advances when a "track" ends.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import Component, DEVICE_TYPE_MEDIA_PLAYER, components_for, device_info_for
from .mixins import FakeEntityMixin

TICK = timedelta(seconds=5)

FAKE_TRACKS = [
    ("Sunset Drive", "The Fake Waves", 215),
    ("Night Static", "Neon Circuit", 187),
    ("Coffee & Rain", "Lo-Fi Loom", 240),
]

SOURCE_LISTS = {
    MediaPlayerDeviceClass.TV: ["HDMI 1", "HDMI 2", "HDMI 3", "Cable", "Streaming App"],
    MediaPlayerDeviceClass.SPEAKER: ["Spotify", "Bluetooth", "AirPlay", "Line In"],
    MediaPlayerDeviceClass.RECEIVER: [
        "Blu-ray",
        "Game Console",
        "Cable Box",
        "Streaming Stick",
        "Turntable",
    ],
}

FEATURES = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.SELECT_SOURCE
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake media player for each Media Player component."""
    async_add_entities(
        FakeMediaPlayer(c)
        for c in components_for(entry)
        if c.device_type == DEVICE_TYPE_MEDIA_PLAYER
    )


class FakeMediaPlayer(FakeEntityMixin, MediaPlayerEntity):
    """A simulated speaker, TV, or receiver."""

    _attr_has_entity_name = True
    _attr_supported_features = FEATURES

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        show_as = component.show_as or "speaker"
        self._attr_device_class = MediaPlayerDeviceClass(show_as)
        self._attr_source_list = SOURCE_LISTS[self._attr_device_class]
        self._attr_name = component.label

        self._attr_unique_id = f"{component.id}_media_player"
        self._attr_device_info = device_info_for(component.entry)

        self._attr_state = MediaPlayerState.OFF
        self._attr_volume_level = 0.4
        self._attr_is_volume_muted = False
        self._attr_source = self._attr_source_list[0]
        self._attr_media_position = 0
        self._track_index = 0
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)
        self._sync_track_attrs()

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    def _sync_track_attrs(self) -> None:
        title, artist, duration = FAKE_TRACKS[self._track_index]
        self._attr_media_title = title
        self._attr_media_artist = artist
        self._attr_media_duration = duration
        self._attr_media_content_type = MediaType.MUSIC

    @callback
    def _tick(self, now) -> None:
        if self._attr_state != MediaPlayerState.PLAYING:
            return
        self._attr_media_position += TICK.total_seconds()
        if self._attr_media_position >= (self._attr_media_duration or 0):
            self._track_index = (self._track_index + 1) % len(FAKE_TRACKS)
            self._attr_media_position = 0
            self._sync_track_attrs()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        self._attr_state = MediaPlayerState.IDLE
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        self._attr_state = MediaPlayerState.OFF
        self.async_write_ha_state()

    async def async_media_play(self) -> None:
        self._attr_state = MediaPlayerState.PLAYING
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        self._attr_state = MediaPlayerState.PAUSED
        self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_position = 0
        self.async_write_ha_state()

    async def async_media_next_track(self) -> None:
        self._track_index = (self._track_index + 1) % len(FAKE_TRACKS)
        self._attr_media_position = 0
        self._sync_track_attrs()
        self.async_write_ha_state()

    async def async_media_previous_track(self) -> None:
        self._track_index = (self._track_index - 1) % len(FAKE_TRACKS)
        self._attr_media_position = 0
        self._sync_track_attrs()
        self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        self._attr_source = source
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        self._attr_volume_level = volume
        self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        self._attr_is_volume_muted = mute
        self.async_write_ha_state()
