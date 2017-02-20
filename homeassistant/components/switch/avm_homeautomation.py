'''
Created on 16.02.2017

@author: Christian
'''

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from typing import Optional, List

from homeassistant.const import (
    STATE_ON, STATE_OFF, STATE_UNKNOWN, TEMP_CELSIUS)
from homeassistant.components.switch import (SwitchDevice)
from homeassistant.components.avm_homeautomation import (AvmHomeAutomationDevice, 
    ATTR_DISCOVER_DEVICES, DATA_AVM_HOMEAUTOMATION, DOMAIN,
    SCHEMA_DICT_SWITCH, SCHEMA_DICT_POWERMETER, SCHEMA_DICT_TEMPERATURE,
    SCHEMA_DICT_HKR)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['avm_homeautomation']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the avm_smarthome switch platform."""

    if discovery_info is None:
        return
    else:
        __ains  = discovery_info[ATTR_DISCOVER_DEVICES]

        # print(hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN])
        
        for __ain  in __ains:
            __aha = hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN]
            _LOGGER.debug("Adding device '%s'" % __ain)
            add_devices([AvmHomeAutomationDeviceSwitch(hass, __ain, __aha)], True)
    return

ATTR_CURRENT_CONSUMPTION = 'Current Consumption'
ATTR_CURRENT_CONSUMPTION_UNIT = 'W'

ATTR_TOTAL_CONSUMPTION = 'Total Consumption'
ATTR_TOTAL_CONSUMPTION_UNIT = 'kWh'

ATTR_TEMPERATURE = 'Temperature'


SCHEMA_DICT_SWITCH = vol.Schema({
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
            vol.Required('private_updated'):  cv.boolean,
        }, extra=vol.ALLOW_EXTRA)

class AvmHomeAutomationDeviceSwitch(AvmHomeAutomationDevice, SwitchDevice):
    """Representation of a FRITZ!DECT switch."""
    
    def _validate_schema(self, value):
        SCHEMA_DICT_SWITCH(value)
    
    @property
    def current_power_watt(self):
        """Return the current power usage in Watt."""
        return float(int(self._dict['powermeter']['power'])) / 1000.0 # mW to W
    
    @property
    def total_energy_watt_hours(self):
        """Return the energy usage in Watt Hours."""
        return int(self._dict['powermeter']['energy'])
    
    @property
    def total_energy_killo_watt_hours(self):
        """Return the energy usage in Killo Watt Hours."""
        return float(int(self._dict['powermeter']['energy'])) / 1000.0 # Wh to kWh
    
    ## Import from Entity
    @property
    def state(self) -> str:
        """Return the state of the entity."""       
        if self.available == True:
            if self.is_on == True:
                return STATE_ON
            else:
                return STATE_OFF
        else:
            return STATE_UNKNOWN
        
    @property
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return self._assumed_state
    
    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attrs = {}

        attrs[ATTR_CURRENT_CONSUMPTION] = "%.1f %s" % \
            (self.current_power_watt, ATTR_CURRENT_CONSUMPTION_UNIT)
        attrs[ATTR_TOTAL_CONSUMPTION] = "%.3f %s" % \
            (self.total_energy_killo_watt_hours, ATTR_TOTAL_CONSUMPTION_UNIT)
        attrs[ATTR_TEMPERATURE] = "%.1f %s" % (self.current_temperature, self.units.temperature_unit)

        return attrs
    
    ## Import from ToggleEntity
    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        __state = False
        if self._assumed_state == True:
            __state = bool(int(self._aha.send_switch_command({'switchcmd': 'getswitchstate'}, self._ain)))
        else:
            __state = bool(int(self._dict['switch']['state']))
        return __state
        
    def turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self._aha.send_switch_command({'switchcmd': 'setswitchon'}, self._ain)
        self._dict['switch']['state'] = True
        self._assumed_state = True

    def turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self._aha.send_switch_command({'switchcmd': 'setswitchoff'}, self._ain)
        self._dict['switch']['state'] = False
        self._assumed_state = True
            
    ## Import from SwitchDevice
    ## None
    
#     @property
#     def state_attributes(self):
#         """Return the optional state attributes."""
#         data = {}
# 
#         for prop, attr in PROP_TO_ATTR.items():
#             value = getattr(self, prop)
#             if value:
#                 data[attr] = value
# 
#         return data
    
    