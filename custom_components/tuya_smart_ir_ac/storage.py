"""State storage helpers used by the integration."""

from typing import Any

from homeassistant.components.climate import HVACMode


class ClimatePresetStore:
    """Read and write user-configured temperature and fan presets."""

    def __init__(self, presets: dict[str, Any], climate_id: str) -> None:
        """Initialize the store for one climate device."""
        self._presets = presets
        self._climate_id = climate_id

    def get_temperature(self, hvac_mode: HVACMode) -> float | None:
        """Return the configured temperature for an HVAC mode, if present."""
        value = self._presets.get(self._climate_id, {}).get(
            f"temp_{hvac_mode.value}"
        )
        return value if isinstance(value, (int, float)) else None

    def set_temperature(self, hvac_mode: str, value: float) -> None:
        """Store the configured temperature for an HVAC mode."""
        device_presets = self._presets.setdefault(self._climate_id, {})
        device_presets[f"temp_{hvac_mode}"] = value

    def get_fan_mode(self) -> str | None:
        """Return the configured fallback fan mode, if present."""
        value = self._presets.get(self._climate_id, {}).get("fan_preset")
        return value if isinstance(value, str) else None

    def set_fan_mode(self, fan_mode: str) -> None:
        """Store the configured fallback fan mode."""
        device_presets = self._presets.setdefault(self._climate_id, {})
        device_presets["fan_preset"] = fan_mode
