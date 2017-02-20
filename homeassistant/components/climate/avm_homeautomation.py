'''
Created on 16.02.2017

@author: Christian
'''
import logging
import voluptuous as vol
from voluptuous.schema_builder import Required, Optional, Remove
import homeassistant.helpers.config_validation as cv

from datetime import timedelta

from homeassistant.components.climate import (
    STATE_AUTO, STATE_OFF, STATE_ON, ClimateDevice,
    PRECISION_HALVES, PRECISION_TENTHS, ATTR_CURRENT_TEMPERATURE, 
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW, ATTR_MAX_TEMP, ATTR_MIN_TEMP, 
    ATTR_OPERATION_MODE)

from homeassistant.const import (
    ATTR_TEMPERATURE, TEMP_CELSIUS, STATE_UNKNOWN, ATTR_WAKEUP)

from homeassistant.components.avm_homeautomation import (
    ATTR_DISCOVER_DEVICES, DATA_AVM_HOMEAUTOMATION, DOMAIN,
    AvmHomeAutomationDevice, SCHEMA_DICT_SWITCH, SCHEMA_DICT_POWERMETER,
    SCHEMA_DICT_TEMPERATURE, SCHEMA_DICT_HKR)

from tkinter.constants import OFF

SCAN_INTERVAL = timedelta(minutes=1)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['avm_homeautomation']

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the avm_smarthome switch platform."""
                
    if discovery_info is None:
        return
    else:
        __ains  = discovery_info[ATTR_DISCOVER_DEVICES]

        for __ain  in __ains:
            __aha = hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN]
            _LOGGER.debug("Adding device '%s'" % __ain)
            add_devices([AvmThermostat(hass, __ain, __aha)], True)
                
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

STATE_MANUAL = "manual"
THERMOSTAT_STATES = [STATE_AUTO, STATE_MANUAL, STATE_ON, STATE_OFF]

class AvmThermostat(AvmHomeAutomationDevice, ClimateDevice):
    """Representation of a AVM Thermostat."""
    
    def _validate_schema(self, value):
        SCHEMA_DICT_CLIMATE(value)
        
    @property
    def unit_of_measurement(self):
        """The unit of measurement to display."""
        return self.hass.config.units.temperature_unit
    
    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attrs = {}
        
        if self.available == True:
            attrs[ATTR_CURRENT_TEMPERATURE] = self.current_temperature
        else:
            attrs[ATTR_CURRENT_TEMPERATURE] = STATE_UNKNOWN
        
        attrs[ATTR_TEMPERATURE]      = self.target_temperature
        attrs[ATTR_TARGET_TEMP_HIGH] = self.target_temperature_high
        attrs[ATTR_TARGET_TEMP_LOW]  = self.target_temperature_low
        attrs[ATTR_OPERATION_MODE]   = self.current_operation
        attrs[ATTR_MAX_TEMP]         = self.max_temp
        attrs[ATTR_MIN_TEMP]         = self.min_temp

        return attrs
            
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
        __operation = STATE_UNKNOWN
        if self.available == False:
            __operation = STATE_UNKNOWN
        elif (self.target_temperature == self.target_temperature_high) or\
            (self.target_temperature == self.target_temperature_low):
            __operation = STATE_AUTO
        else:
            __target = int(self._dict['hkr']['tsoll'])
        
            if __target == 253:
                __operation = STATE_OFF
            elif __target == 254:
                __operation = STATE_ON
            else:
                __operation = STATE_MANUAL

        return __operation

    @property
    def operation_list(self):
        """Return the operation modes list."""
        return THERMOSTAT_STATES
    
    @property
    def target_temperature(self) -> float:
        __target = int(self._dict['hkr']['tsoll'])
        
        if __target == 253:
            __target = 0
        elif __target == 254:
            __target = 60
            
        return self._convert_for_display(float(__target) / 2.0)
    
    @property
    def target_temperature_high(self) -> float:
        return self._convert_for_display(
            float(int(self._dict['hkr']['komfort'])) / 2.0)
        
    @property
    def target_temperature_low(self) -> float:
        return self._convert_for_display(
            float(int(self._dict['hkr']['absenk'])) / 2.0)

    @property
    def temperature(self):
        """Return the _temperature we try to reach."""
        return self.taget_temperature
    
    def set_temperature(self, **kwargs):
        """Set new target _temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        temperature = int(temperature * 2.0)
        self._aha.send_switch_command({'switchcmd': 'sethkrtsoll', 'param': str(temperature)}, self._ain)
        self._dict['hkr']['tsoll'] = temperature
        return
    
    def set_operation_mode(self, operation_mode):
        """Set operation mode (auto, cool, heat, off)."""
        if operation_mode == STATE_OFF:
            temperature = 253
        elif operation_mode == STATE_ON:
            temperature = 254
        elif operation_mode == STATE_AUTO:
            temperature = self._dict['hkr']['komfort']
        else:
            return
        
        self._aha.send_switch_command({'switchcmd': 'sethkrtsoll', 'param': str(temperature)}, self._ain)
        self._dict['hkr']['tsoll'] = temperature
            
        return
    
    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._convert_for_display(8.0)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._convert_for_display(28.0)
    