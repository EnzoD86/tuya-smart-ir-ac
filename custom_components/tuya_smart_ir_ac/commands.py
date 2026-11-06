import logging

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import FAN_AUTO, FAN_LOW
from homeassistant.const import Platform

from .const import (
    DEFAULT_MIN_TEMP,
    POWER_ON_ALWAYS,
    POWER_ON_NEVER,
    POWER_ON_ONLY_OFF,
)
from .models import RuntimeData, TuyaClimateConfig

_LOGGER = logging.getLogger(__package__)


class ClimateCommandHandler:
    """Apply HVAC command rules using explicit services, configuration and state."""

    def __init__(
        self,
        runtime_data: RuntimeData,
        config: TuyaClimateConfig,
    ) -> None:
        """Initialize the handler with runtime data and device configuration."""
        self._runtime_data = runtime_data
        self._config = config

    async def async_handle_turn_on(self) -> None:
        """Turn on the climate device using its configured power-on behavior."""
        climate_data = self._runtime_data.climate_coordinator.get_climate_data(
            self._config.climate_id
        )
        force_power_on = (
            True
            if self._config.custom_power_on
            else self._requires_power_on(
                self._config.hvac_power_on, climate_data.current_hvac_mode
            )
        )
        await self._async_dispatch_command(
            climate_data.hvac_mode,
            climate_data.temperature,
            climate_data.fan_mode,
            force_power_on,
        )

    async def async_handle_turn_off(self) -> None:
        """Turn off the climate device."""
        await self._runtime_data.climate_coordinator.async_turn_off(
            self._config.infrared_id, self._config.climate_id
        )

    async def async_handle_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode and its corresponding target settings."""
        if hvac_mode is HVACMode.OFF:
            await self.async_handle_turn_off()
            return

        climate_data = self._runtime_data.climate_coordinator.get_climate_data(
            self._config.climate_id
        )
        temperature = self._get_hvac_temperature(hvac_mode, climate_data.temperature)
        fan_mode = self._get_hvac_fan_mode(hvac_mode, climate_data.fan_mode)
        force_power_on = self._requires_power_on(
            self._config.hvac_power_on, climate_data.current_hvac_mode
        )
        await self._async_dispatch_command(hvac_mode, temperature, fan_mode, force_power_on)

    async def async_handle_set_temperature(
        self,
        temperature: float,
        hvac_mode: HVACMode | None = None,
    ) -> None:
        """Set the target temperature, optionally changing the HVAC mode."""
        if hvac_mode is HVACMode.OFF:
            await self.async_handle_turn_off()
            return

        climate_data = self._runtime_data.climate_coordinator.get_climate_data(
            self._config.climate_id
        )
        target_hvac_mode = hvac_mode if hvac_mode is not None else climate_data.hvac_mode
        fan_mode = self._get_hvac_fan_mode(target_hvac_mode, climate_data.fan_mode)
        force_power_on = self._requires_power_on(
            self._config.temperature_power_on, climate_data.current_hvac_mode
        )
        await self._async_dispatch_command(
            target_hvac_mode, temperature, fan_mode, force_power_on
        )

    async def async_handle_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        climate_data = self._runtime_data.climate_coordinator.get_climate_data(
            self._config.climate_id
        )
        force_power_on = self._requires_power_on(
            self._config.fan_power_on, climate_data.current_hvac_mode
        )
        await self._async_dispatch_command(
            climate_data.hvac_mode,
            climate_data.temperature,
            fan_mode,
            force_power_on,
        )

    async def async_handle_set_preset_mode(
        self,
        preset_mode: str,
        last_valid_preset_hvac_mode: HVACMode | None,
    ) -> None:
        """Apply the selected global preset to the current or last active mode."""
        preset_manager = self._runtime_data.global_preset_manager
        climate_data = self._runtime_data.climate_coordinator.get_climate_data(
            self._config.climate_id
        )
        preset_selection = preset_manager.get_preset_selection(
            preset_mode,
            climate_data.hvac_mode,
            climate_data.current_hvac_mode,
            last_valid_preset_hvac_mode,
        )
        if preset_selection is None:
            return

        force_power_on = self._requires_power_on(
            self._config.hvac_power_on, climate_data.current_hvac_mode
        )
        await self._async_dispatch_command(
            preset_selection.hvac_mode,
            preset_selection.temperature,
            preset_selection.fan_mode,
            force_power_on,
        )

    async def _async_dispatch_command(
        self,
        target_mode: HVACMode,
        target_temperature: float,
        target_fan_mode: str,
        force_power_on: bool,
    ) -> None:
        """Dispatch the selected settings, including any required power-on action."""
        if force_power_on:
            if self._config.custom_power_on:
                await self._async_trigger_custom_power_on()
            else:
                await self._runtime_data.climate_coordinator.async_turn_on_with_hvac_mode(
                    self._config.infrared_id,
                    self._config.climate_id,
                    target_mode,
                    target_temperature,
                    target_fan_mode,
                )
                return

        await self._runtime_data.climate_coordinator.async_set_hvac_mode(
            self._config.infrared_id,
            self._config.climate_id,
            target_mode,
            target_temperature,
            target_fan_mode,
        )

    async def _async_trigger_custom_power_on(self) -> None:
        """Press the configured custom power-on button."""
        custom_power_on = self._config.custom_power_on
        _LOGGER.debug("Triggering custom power-on button: %s", custom_power_on)
        await self._runtime_data.climate_coordinator.hass.services.async_call(
            domain=Platform.BUTTON,
            service="press",
            service_data={"entity_id": custom_power_on},
            blocking=True,
        )

    def _get_hvac_temperature(
        self, hvac_mode: HVACMode, current_temperature: float
    ) -> float:
        """Choose the target temperature for an HVAC mode."""
        if self._config.use_preset_temperature:
            preset_temperature = (
                self._runtime_data.hvac_mode_preset_manager.get_temperature(
                    self._config.climate_id, hvac_mode
                )
            )
            if preset_temperature is not None:
                return preset_temperature

        if hvac_mode is HVACMode.DRY and self._config.dry_min_temperature:
            return DEFAULT_MIN_TEMP

        return max(current_temperature, self._config.min_temperature)

    def _get_hvac_fan_mode(
        self, hvac_mode: HVACMode, current_fan_mode: str
    ) -> str:
        """Choose the fan mode for an HVAC mode."""
        if hvac_mode is HVACMode.DRY:
            return FAN_LOW if self._config.dry_min_fan else FAN_AUTO

        if self._config.use_preset_fan:
            preset_fan_mode = (
                self._runtime_data.hvac_mode_preset_manager.get_fan_mode(
                    self._config.climate_id
                )
            )
            if preset_fan_mode is not None:
                return preset_fan_mode

        return current_fan_mode

    @staticmethod
    def _requires_power_on(power_on_setting: str, previous_mode: HVACMode) -> bool:
        """Determine whether the device must be explicitly powered on."""
        if power_on_setting == POWER_ON_NEVER:
            return False
        if power_on_setting == POWER_ON_ALWAYS:
            return True
        return power_on_setting == POWER_ON_ONLY_OFF and previous_mode is HVACMode.OFF