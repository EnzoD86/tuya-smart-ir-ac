"""Compatibility policies for climate devices."""

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import FAN_AUTO, FAN_LOW

from .const import (
    DEFAULT_MIN_TEMP,
    POWER_ON_ALWAYS,
    POWER_ON_NEVER,
    POWER_ON_ONLY_OFF,
)
from .models import TuyaClimateConfig


class ClimateCompatibilityPolicy:
    """Resolve device-specific compatibility behavior from climate configuration."""

    def __init__(self, config: TuyaClimateConfig) -> None:
        """Initialize the policy with parsed climate compatibility options."""
        self._config = config

    @property
    def custom_power_on_button(self) -> str | None:
        """Return the configured custom power-on button entity, if any."""
        return self._config.custom_power_on

    @property
    def has_custom_power_on_button(self) -> bool:
        """Return whether a custom power-on button is configured."""
        return bool(self._config.custom_power_on)

    def should_force_hvac_power_on(self, current_hvac_mode: HVACMode) -> bool:
        """Return whether HVAC commands require an explicit power-on action."""
        return self._should_force_power_on(
            self._config.hvac_power_on, current_hvac_mode
        )

    def should_power_on_before_hvac_command(
        self, current_hvac_mode: HVACMode
    ) -> bool:
        """Return whether turning on needs a separate power-on action."""
        if self._config.custom_power_on:
            return True
        return self.should_force_hvac_power_on(current_hvac_mode)

    def should_force_temperature_power_on(
        self, current_hvac_mode: HVACMode
    ) -> bool:
        """Return whether temperature commands require an explicit power-on action."""
        return self._should_force_power_on(
            self._config.temperature_power_on, current_hvac_mode
        )

    def should_force_fan_power_on(self, current_hvac_mode: HVACMode) -> bool:
        """Return whether fan commands require an explicit power-on action."""
        return self._should_force_power_on(
            self._config.fan_power_on, current_hvac_mode
        )

    def override_temperature(self, target_hvac_mode: HVACMode) -> float | None:
        """Return a compatibility temperature override for the target HVAC mode."""
        if target_hvac_mode is not HVACMode.DRY:
            return None
        if not self._config.dry_min_temperature:
            return None
        return DEFAULT_MIN_TEMP

    def override_fan_mode(self, target_hvac_mode: HVACMode) -> str | None:
        """Return a compatibility fan mode override for the target HVAC mode."""
        if target_hvac_mode is not HVACMode.DRY:
            return None
        if self._config.dry_min_fan:
            return FAN_LOW
        return FAN_AUTO

    @staticmethod
    def _should_force_power_on(
        power_on_setting: str, current_hvac_mode: HVACMode
    ) -> bool:
        """Resolve a power-on option against the climate's current state."""
        if power_on_setting == POWER_ON_ALWAYS:
            return True
        if power_on_setting == POWER_ON_ONLY_OFF:
            return current_hvac_mode is HVACMode.OFF
        if power_on_setting == POWER_ON_NEVER:
            return False
        return False
