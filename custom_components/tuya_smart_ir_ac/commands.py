import logging

from homeassistant.components.climate import HVACMode
from homeassistant.const import Platform

from .compatibility import ClimateCompatibilityPolicy
from .const import COMMAND_TYPE_MULTIPLE, COMMAND_TYPE_SINGLE
from .models import RuntimeData, TuyaClimateConfig

_LOGGER = logging.getLogger(__package__)


class ClimateCommandHandler:
    """Build and dispatch climate commands using state and compatibility policy."""

    def __init__(
        self,
        runtime_data: RuntimeData,
        config: TuyaClimateConfig,
    ) -> None:
        """Initialize the handler with runtime data and device configuration."""
        self._runtime_data = runtime_data
        self._config = config
        self._compatibility_policy = ClimateCompatibilityPolicy(config)

    async def async_handle_turn_on(self) -> None:
        """Turn on the climate device using its configured power-on behavior."""
        climate_data = self._runtime_data.climate_coordinator.get_climate_data(
            self._config.climate_id
        )
        # Determine whether the HVAC command needs a separate power-on action.
        force_power_on = self._compatibility_policy.should_power_on_before_hvac_command(
            climate_data.current_hvac_mode
        )
        await self._async_dispatch_command(
            climate_data.hvac_mode,
            climate_data.temperature,
            climate_data.fan_mode,
            force_power_on,
        )

    async def async_handle_turn_off(self) -> None:
        """Turn off the climate device."""
        coordinator = self._runtime_data.climate_coordinator
        await coordinator.async_send_power_command(
            self._config.infrared_id, self._config.climate_id, False
        )
        coordinator.update_climate_cache(self._config.climate_id, power=False)

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
        force_power_on = self._compatibility_policy.should_force_hvac_power_on(
            climate_data.current_hvac_mode
        )
        await self._async_dispatch_command(
            hvac_mode, temperature, fan_mode, force_power_on
        )

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
        # Temperature changes may have a different power-on compatibility rule.
        force_power_on = self._compatibility_policy.should_force_temperature_power_on(
            climate_data.current_hvac_mode
        )
        await self._async_dispatch_command(
            target_hvac_mode, temperature, fan_mode, force_power_on
        )

    async def async_handle_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        climate_data = self._runtime_data.climate_coordinator.get_climate_data(
            self._config.climate_id
        )
        # Fan changes may have a different power-on compatibility rule.
        force_power_on = self._compatibility_policy.should_force_fan_power_on(
            climate_data.current_hvac_mode
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

        # Presets use the HVAC power-on compatibility rule.
        force_power_on = self._compatibility_policy.should_force_hvac_power_on(
            climate_data.current_hvac_mode
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
        coordinator = self._runtime_data.climate_coordinator
        climate_data = coordinator.get_climate_data(self._config.climate_id)
        has_custom_power_on_button = self._compatibility_policy.has_custom_power_on_button
        if force_power_on and has_custom_power_on_button:
            # Use the configured button instead of the regular power-on command.
            await self._async_trigger_custom_power_on()
        elif force_power_on:
            await coordinator.async_send_power_command(
                self._config.infrared_id, self._config.climate_id, True
            )

        if self._config.command_type == COMMAND_TYPE_SINGLE:
            hvac_mode_changed = target_mode != climate_data.hvac_mode
            temperature_changed = target_temperature != climate_data.temperature
            fan_mode_changed = target_fan_mode != climate_data.fan_mode

            if fan_mode_changed:
                await coordinator.async_send_fan_mode_command(
                    self._config.infrared_id,
                    self._config.climate_id,
                    target_fan_mode,
                )
            if hvac_mode_changed:
                await coordinator.async_send_hvac_mode_command(
                    self._config.infrared_id, self._config.climate_id, target_mode
                )
            if temperature_changed:
                await coordinator.async_send_temperature_command(
                    self._config.infrared_id,
                    self._config.climate_id,
                    target_temperature,
                )

            if force_power_on or hvac_mode_changed or temperature_changed or fan_mode_changed:
                coordinator.update_climate_cache(
                    self._config.climate_id,
                    power=True,
                    hvac_mode=target_mode if hvac_mode_changed else None,
                    temperature=target_temperature if temperature_changed else None,
                    fan_mode=target_fan_mode if fan_mode_changed else None,
                )
        elif self._config.command_type == COMMAND_TYPE_MULTIPLE:
            await coordinator.async_send_combined_command(
                self._config.infrared_id,
                self._config.climate_id,
                target_mode,
                target_temperature,
                target_fan_mode,
            )

            coordinator.update_climate_cache(
                self._config.climate_id,
                power=True,
                hvac_mode=target_mode,
                temperature=target_temperature,
                fan_mode=target_fan_mode,
            )

    async def _async_trigger_custom_power_on(self) -> None:
        """Press the configured custom power-on button."""
        button_entity_id = self._compatibility_policy.custom_power_on_button
        _LOGGER.debug(
            "Triggering custom power-on button: %s",
            button_entity_id,
        )
        await self._runtime_data.climate_coordinator.hass.services.async_call(
            domain=Platform.BUTTON,
            service="press",
            service_data={"entity_id": button_entity_id},
            blocking=True,
        )

    def _get_hvac_temperature(
        self, hvac_mode: HVACMode, current_temperature: float
    ) -> float:
        """Choose the target temperature for an HVAC mode."""
        # Compatibility may override the temperature for the target HVAC mode.
        override_temperature = self._compatibility_policy.override_temperature(hvac_mode)
        if override_temperature is not None:
            return override_temperature

        if self._config.temperature_hvac_preset_enabled:
            preset_temperature = self._runtime_data.hvac_mode_preset_manager.get_temperature(
                self._config.climate_id, hvac_mode
            )
            if preset_temperature is not None:
                return preset_temperature

        return max(current_temperature, self._config.min_temperature)

    def _get_hvac_fan_mode(
        self, hvac_mode: HVACMode, current_fan_mode: str
    ) -> str:
        """Choose the fan mode for an HVAC mode."""
        # Compatibility may override the fan mode for the target HVAC mode.
        override_fan_mode = self._compatibility_policy.override_fan_mode(hvac_mode)
        if override_fan_mode is not None:
            return override_fan_mode

        if self._config.fan_hvac_preset_enabled:
            preset_fan_mode = self._runtime_data.hvac_mode_preset_manager.get_fan_mode(
                self._config.climate_id
            )
            if preset_fan_mode is not None:
                return preset_fan_mode

        return current_fan_mode
