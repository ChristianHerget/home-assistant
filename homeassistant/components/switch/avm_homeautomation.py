"""
Support for FRITZ!DECT switches.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/switch.avm_homeautomation/
"""

import asyncio
import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.const import (STATE_ON, STATE_OFF, STATE_UNKNOWN)
from homeassistant.components.switch import (SwitchDevice)
from homeassistant.components.climate import (STATE_AUTO)
from homeassistant.components.avm_homeautomation import (
    AvmHomeAutomationDevice, ATTR_DISCOVER_DEVICES, DATA_AVM_HOMEAUTOMATION,
    DOMAIN, SCHEMA_DICT_SWITCH, SCHEMA_DICT_POWERMETER,
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

        # print(hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN])

        for __ain in __ains:
            __aha = hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN]
            _LOGGER.debug("Adding device '%s'", __ain)
            yield from async_add_entities(
                [AvmHomeAutomationDeviceSwitch(hass, __ain, __aha)],
                update_before_add=False
                )
    return


ATTR_CURRENT_CONSUMPTION = 'Current Consumption'
ATTR_CURRENT_CONSUMPTION_UNIT = 'W'

ATTR_TOTAL_CONSUMPTION = 'Total Consumption'
ATTR_TOTAL_CONSUMPTION_UNIT = 'kWh'

ATTR_TEMPERATURE = 'Temperature'


VAL_SCHEMA_DICT_SWITCH = vol.Schema({
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
    vol.Required('switch'):           SCHEMA_DICT_SWITCH,
    vol.Required('powermeter'):       SCHEMA_DICT_POWERMETER,
    vol.Optional('temperature'):      SCHEMA_DICT_TEMPERATURE,
    vol.Remove('hkr'):                SCHEMA_DICT_HKR,
}, extra=vol.ALLOW_EXTRA)

HM_ATTRIBUTE_SUPPORT = {
    'mode':       ['mode', {'auto': STATE_AUTO, 'manuell': STATE_MANUAL}],
    'lock':       ['lock', {'0': False, '1': True}],
    'devicelock': ['devicelock', {'0': False, '1': True}],
}


class AvmHomeAutomationDeviceSwitch(AvmHomeAutomationDevice, SwitchDevice):
    """Representation of a FRITZ!DECT switch."""

    @property
    def current_power_watt(self) -> float:
        """Return the current power usage in Watt."""
        # mW to W
        return float(int(self._dict['powermeter']['power'])) / 1000.0

    @property
    def total_energy_watt_hours(self) -> int:
        """Return the energy usage in Watt Hours."""
        return int(self._dict['powermeter']['energy'])

    @property
    def total_energy_killo_watt_hours(self) -> float:
        """Return the energy usage in Killo Watt Hours."""
        # Wh to kWh
        return float(int(self._dict['powermeter']['energy'])) / 1000.0

    # # Import from Entity
    @property
    def state(self) -> str:
        """Return the state of the entity."""
        if self.available:
            if self.is_on:
                return STATE_ON
            else:
                return STATE_OFF
        else:
            return STATE_UNKNOWN

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attrs = {}

        # no data available to create
        if not self.available:
            return attrs

        attrs[ATTR_CURRENT_CONSUMPTION] = "%.1f %s" % \
            (self.current_power_watt, ATTR_CURRENT_CONSUMPTION_UNIT)
        attrs[ATTR_TOTAL_CONSUMPTION] = "%.3f %s" % \
            (self.total_energy_killo_watt_hours, ATTR_TOTAL_CONSUMPTION_UNIT)
        attrs[ATTR_TEMPERATURE] = "%.1f" % self.current_temperature

        # Generate an attributes list
        for node, data in HM_ATTRIBUTE_SUPPORT.items():
            # Is an attributes and exists for this object
            if node in self._dict['switch']:
                value = data[1].get(
                    self._dict['switch'][node],
                    str(self._dict['switch'][node])
                    )
                attrs[data[0]] = value

        return attrs

    # # Import from ToggleEntity
    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return bool(int(self._dict['switch']['state']))

    @asyncio.coroutine
    def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        yield from self._aha.async_send_switch_command(
            {'switchcmd': 'setswitchon'}, self._ain)
        self._dict['switch']['state'] = True
        self.schedule_update_ha_state()

    @asyncio.coroutine
    def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        yield from self._aha.async_send_switch_command(
            {'switchcmd': 'setswitchoff'}, self._ain)
        self._dict['switch']['state'] = False
        self.schedule_update_ha_state()

    # # Import from SwitchDevice
    # # None
