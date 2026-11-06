"""Preset models and management for climate entities."""

from __future__ import annotations

import copy
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import PRESET_NONE
from homeassistant.config_entries import ConfigEntry

from .const import CONF_GLOBAL_PRESETS, DEFAULT_GLOBAL_PRESETS
from .models import (
    GlobalClimatePresetData,
    GlobalPresetSelectionData,
    GlobalPresets,
    HvacModePresetData,
)

class GlobalPresetManager:
    """Merge, parse, and query shared global climate presets."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize presets from saved options and built-in defaults."""
        self._presets: GlobalPresets = {}
        self.update_from_config_entry(config_entry)

    def update_from_config_entry(self, config_entry: ConfigEntry) -> None:
        """Reload presets from a config entry, applying built-in defaults."""
        saved_presets = config_entry.options.get(CONF_GLOBAL_PRESETS, {})
        merged_presets = copy.deepcopy(DEFAULT_GLOBAL_PRESETS)
        for preset_name, modes in saved_presets.items():
            if preset_name not in merged_presets:
                merged_presets[preset_name] = {}
            merged_presets[preset_name].update(modes)

        parsed_presets: GlobalPresets = {}
        for preset_name, mode_configs in merged_presets.items():
            parsed_modes: dict[HVACMode, GlobalClimatePresetData] = {}
            for raw_mode, config in mode_configs.items():
                hvac_mode = HVACMode(raw_mode)
                temperature = config.get("temp")
                fan_mode = config.get("fan")
                parsed_modes[hvac_mode] = GlobalClimatePresetData(
                    temperature=float(temperature),
                    fan_mode=fan_mode,
                )

            if parsed_modes:
                parsed_presets[preset_name] = parsed_modes

        self._presets = parsed_presets

    def get_preset_selection(
        self,
        preset_name: str,
        hvac_mode: HVACMode,
        current_hvac_mode: HVACMode,
        last_valid_hvac_mode: HVACMode | None,
    ) -> GlobalPresetSelectionData | None:
        """Return the preset settings and HVAC mode applicable to the current state."""
        if preset_name == PRESET_NONE:
            return None

        preset_hvac_mode = self._get_preset_hvac_mode(
            hvac_mode, current_hvac_mode, last_valid_hvac_mode
        )
        preset_settings = self._get_preset_settings(preset_name, preset_hvac_mode)
        if preset_settings is None:
            return None

        return GlobalPresetSelectionData(
            hvac_mode=preset_hvac_mode,
            temperature=preset_settings.temperature,
            fan_mode=preset_settings.fan_mode,
        )

    def get_available_presets(
        self,
        preset_names: list[str],
        hvac_mode: HVACMode,
        current_hvac_mode: HVACMode,
        last_valid_hvac_mode: HVACMode | None,
    ) -> list[str]:
        """Return configured presets available for the climate's current state."""
        mode = self._get_preset_hvac_mode(
            hvac_mode, current_hvac_mode, last_valid_hvac_mode
        )

        available_presets = [
            preset_name
            for preset_name in preset_names
            if self._get_preset_settings(preset_name, mode) is not None
        ]
        return [PRESET_NONE, *available_presets]

    @staticmethod
    def _get_preset_hvac_mode(
        hvac_mode: HVACMode,
        current_hvac_mode: HVACMode,
        last_valid_hvac_mode: HVACMode | None,
    ) -> HVACMode:
        """Return the HVAC mode used to resolve preset settings."""
        if current_hvac_mode is HVACMode.OFF and last_valid_hvac_mode is not None:
            return last_valid_hvac_mode
        return hvac_mode

    def _get_preset_settings(
        self, preset_name: str, hvac_mode: HVACMode
    ) -> GlobalClimatePresetData | None:
        """Return the settings for a preset and HVAC mode, if configured."""
        return self._presets.get(preset_name, {}).get(hvac_mode)

    def get_current_preset(
        self,
        hvac_mode: HVACMode,
        current_hvac_mode: HVACMode,
        temperature: float,
        fan_mode: str,
    ) -> str:
        """Return the preset matching the climate's current state."""
        if current_hvac_mode is HVACMode.OFF:
            return PRESET_NONE

        return (
            self._find_matching_preset(hvac_mode, temperature, fan_mode)
            or PRESET_NONE
        )

    def _find_matching_preset(
        self,
        hvac_mode: HVACMode,
        temperature: float,
        fan_mode: str,
    ) -> str | None:
        """Find the first preset matching the climate's current settings."""
        for preset_name, mode_configs in self._presets.items():
            settings = mode_configs.get(hvac_mode)
            if (
                settings is not None
                and settings.temperature == temperature
                and settings.fan_mode == fan_mode
            ):
                return preset_name
        return None


class HvacModePresetManager:
    """Manage default temperature and fan settings for each climate."""

    def __init__(self) -> None:
        """Initialize an empty HVAC mode preset collection."""
        self._presets: dict[str, HvacModePresetData] = {}

    def get_temperature(
        self, climate_id: str, hvac_mode: HVACMode
    ) -> float | None:
        """Return the configured temperature for a climate and HVAC mode."""
        preset_data = self._presets.get(climate_id)
        return preset_data.temperatures.get(hvac_mode) if preset_data else None

    def set_temperature(
        self, climate_id: str, hvac_mode: HVACMode, value: float
    ) -> None:
        """Store the configured temperature for a climate and HVAC mode."""
        if hvac_mode not in (HVACMode.AUTO, HVACMode.COOL, HVACMode.HEAT):
            raise ValueError(
                f"Unsupported HVAC mode for temperature preset: {hvac_mode}"
            )
        self._get_or_create_preset_data(climate_id).temperatures[hvac_mode] = value

    def get_fan_mode(self, climate_id: str) -> str | None:
        """Return the configured fallback fan mode for a climate."""
        preset_data = self._presets.get(climate_id)
        return preset_data.fan_mode if preset_data else None

    def set_fan_mode(self, climate_id: str, fan_mode: str) -> None:
        """Store the configured fallback fan mode for a climate."""
        self._get_or_create_preset_data(climate_id).fan_mode = fan_mode

    def _get_or_create_preset_data(self, climate_id: str) -> HvacModePresetData:
        """Return a climate's preset data, creating it if needed."""
        return self._presets.setdefault(climate_id, HvacModePresetData())
