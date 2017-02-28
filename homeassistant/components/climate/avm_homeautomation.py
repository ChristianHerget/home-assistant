"""
Support for FRITZ!DECT thermostats (300 and Comet DECT).

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/climate.avm_homeautomation/
"""

import asyncio
import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.climate import (
    STATE_AUTO, STATE_OFF, STATE_ON, ClimateDevice)
from homeassistant.const import (ATTR_TEMPERATURE, TEMP_CELSIUS, STATE_UNKNOWN)
from homeassistant.components.avm_homeautomation import (
    ATTR_DISCOVER_DEVICES, DATA_AVM_HOMEAUTOMATION, DOMAIN,
    AvmHomeAutomationDevice, SCHEMA_DICT_SWITCH, SCHEMA_DICT_POWERMETER,
    SCHEMA_DICT_TEMPERATURE, SCHEMA_DICT_HKR, STATE_MANUAL)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['avm_homeautomation']


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_entities,
                         discovery_info=None):
    """Setup the avm_smarthome switch platform."""
    if discovery_info is None:
        return
    else:
        __ains = discovery_info[ATTR_DISCOVER_DEVICES]

        for __ain in __ains:
            __aha = hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN]
            _LOGGER.debug("Adding device '%s'", __ain)
            yield from async_add_entities(
                [AvmThermostat(hass, __ain, __aha)],
                update_before_add=False)

    return


SCHEMA_DICT_CLIMATE = vol.Schema({
    # Attributes
    vol.Required('@identifier'):      cv.string,
    vol.Required('@id'):              cv.positive_int,
    vol.Required('@functionbitmask'): cv.positive_int,
    vol.Required('@fwversion'):       cv.string,
    vol.Required('@manufacturer'):    cv.string,
    vol.Required('@productname'):     cv.string,
    # Elements
    vol.Required('present'):          cv.boolean,
    vol.Required('name'):             cv.string,
    vol.Remove('switch'):             SCHEMA_DICT_SWITCH,
    vol.Remove('powermeter'):         SCHEMA_DICT_POWERMETER,
    vol.Required('temperature'):      SCHEMA_DICT_TEMPERATURE,
    vol.Required('hkr'):              SCHEMA_DICT_HKR,
    vol.Required('private_updated'):  cv.boolean,
}, extra=vol.ALLOW_EXTRA)

THERMOSTAT_STATES = [STATE_AUTO, STATE_MANUAL, STATE_ON, STATE_OFF]

ATTR_BATTERY_STATE = "Battery"
STATE_BATTERY_OK = "Ok"
STATE_BATTERY_LOW = "Low"

HM_ATTRIBUTE_SUPPORT = {
    'lock':       ['lock', {0: False, 1: True}],
    'devicelock': ['devicelock', {0: False, 1: True}],
    'errorcode':  ['errorcode', {}],
    'batterylow': [ATTR_BATTERY_STATE, {0: STATE_BATTERY_OK,
                                        1: STATE_BATTERY_LOW}],
}


class AvmThermostat(AvmHomeAutomationDevice, ClimateDevice):
    """Representation of a AVM Thermostat."""

    def _validate_schema(self, value):
        """Used to validate the Schema of the dict."""
        SCHEMA_DICT_CLIMATE(value)

    @property
    def unit_of_measurement(self):
        """The unit of measurement to display."""
        return self.hass.config.units.temperature_unit

    @property
    def state(self) -> str:
        """Return the state of the entity."""
        return self.current_operation

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_operation(self):
        """Return the current operation. head, cool idle."""
        _operation = STATE_UNKNOWN
        _target = int(self._dict['hkr']['tsoll'])
        _low = int(self._dict['hkr']['absenk'])
        _high = int(self._dict['hkr']['komfort'])

        if not self.available:
            _operation = STATE_UNKNOWN
        elif (_target == _low) or (_target == _high):
            _operation = STATE_AUTO
        elif _target == 253:
            _operation = STATE_OFF
        elif _target == 254:
            _operation = STATE_ON
        else:
            _operation = STATE_MANUAL

        return _operation

    @property
    def operation_list(self):
        """Return the operation modes list."""
        return THERMOSTAT_STATES

    @property
    def current_temperature(self) -> float:
        """Return the current _temperature."""
        if self._dict['temperature']['celsius'] is not None:
            return float(int(self._dict['temperature']['celsius'])) / 10.0
        else:
            return 0.0

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        __target = int(self._dict['hkr']['tsoll'])

        if __target == 253:
            __target = 0
        elif __target == 254:
            __target = 60

        return float(__target) / 2.0

    @property
    def target_temperature_comfort(self) -> float:
        """Return the highbound target temperature we try to reach."""
        return self._convert_for_display(
            float(int(self._dict['hkr']['komfort'])) / 2.0)

    @property
    def target_temperature_economy(self) -> float:
        """Return the lowbound target temperature we try to reach."""
        return self._convert_for_display(
            float(int(self._dict['hkr']['absenk'])) / 2.0)

    @asyncio.coroutine
    def async_set_temperature(self, **kwargs):
        """Set new target _temperature."""
        temperature = float(kwargs.get(ATTR_TEMPERATURE))

        if self.min_temp <= temperature <= self.max_temp:
            temperature = int(temperature * 2.0)

            yield from self._aha.async_send_switch_command(
                {'switchcmd': 'sethkrtsoll', 'param': str(temperature)},
                self._ain
                )

            self._dict['hkr']['tsoll'] = temperature
            self.schedule_update_ha_state()
        return

    @asyncio.coroutine
    def async_set_operation_mode(self, operation_mode):
        """Set operation mode (auto, cool, heat, off)."""
        if operation_mode == STATE_OFF:
            temperature = 253
        elif operation_mode == STATE_ON:
            temperature = 254
        elif operation_mode == STATE_AUTO:
            temperature = self._dict['hkr']['komfort']
        else:
            return

        yield from self._aha.async_send_switch_command(
            {'switchcmd': 'sethkrtsoll', 'param': str(temperature)},
            self._ain
            )

        self._dict['hkr']['tsoll'] = temperature
        self.schedule_update_ha_state()
        return

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return 8.0

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return 28.0

    @property
    def device_state_attributes(self):
        """Return the optional state attributes."""
        attrs = {}

        # no data available to create
        if not self.available:
            return attrs

        # Add target temperature attributes for auto mode
        attrs.update({"target_temperature_economy":
                      self.target_temperature_economy})
        attrs.update({"target_temperature_comfort":
                      self.target_temperature_comfort})

        # Generate an attributes list
        for node, data in HM_ATTRIBUTE_SUPPORT.items():
            # Is an attributes and exists for this object
            if node in self._dict['hkr']:
                value = data[1].get(
                    int(self._dict['hkr'][node]),
                    str(self._dict['hkr'][node])
                    )
                attrs[data[0]] = value

        return attrs
