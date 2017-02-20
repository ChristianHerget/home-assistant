'''
Created on 16.02.2017

@author: Christian
'''

import sys

import os
import time
import logging
import asyncio
import xmltodict
from json import dumps

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from functools import partial

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, STATE_UNKNOWN, CONF_USERNAME, CONF_PASSWORD, 
    CONF_PLATFORM, CONF_HOST, CONF_NAME, ATTR_ENTITY_ID, TEMP_CELSIUS)
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval, async_track_time_interval
from homeassistant.config import load_yaml_config_file

from homeassistant.components.climate import (
    PRECISION_TENTHS, ATTR_CURRENT_TEMPERATURE)


DOMAIN = 'avm_homeautomation'
REQUIREMENTS = ['fritzhome==1.0.3']
REQUIREMENTS = ['xmltodict==0.10.2']

#SCAN_INTERVAL_HUB = timedelta(seconds=300)
SCAN_INTERVAL_VARIABLES = timedelta(seconds=15)

DISCOVER_SWITCHES = DOMAIN + '.switch'
DISCOVER_CLIMATE = DOMAIN + '.climate'

ATTR_DISCOVER_DEVICES = 'devices'

DATA_AVM_HOMEAUTOMATION = 'data' + DOMAIN

# Standard FRITZ!Box IP
DEFAULT_HOST = 'fritz.box'
# Standard FRITZ!Box User Name
DEFAULT_USERNAME = "admin"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


SCHEMA_DICT_TEMPERATURE = {
                vol.Required('celsius'): vol.Any(None, vol.Coerce(int)),
                vol.Required('offset'): vol.Any(None, vol.Coerce(int)),
                }

SCHEMA_DICT_HKR = {
                vol.Required('tist'): vol.Any(None, cv.positive_int),
                vol.Required('tsoll'): vol.Any(None, cv.positive_int),
                vol.Required('absenk'): vol.Any(None, cv.positive_int),
                vol.Required('komfort'): vol.Any(None, cv.positive_int),
                vol.Required('lock'): vol.Any(None, cv.positive_int),
                vol.Required('devicelock'): vol.Any(None, cv.positive_int),
                vol.Required('errorcode'): vol.Any(None, cv.positive_int),
                vol.Required('batterylow'): vol.Any(None, cv.positive_int),
                vol.Required('nextchange'): vol.Schema({
                     vol.Required('endperiod'): vol.Any(None, cv.positive_int),
                     vol.Required('tchange'): vol.Any(None, cv.positive_int),
                    }),
                }

SCHEMA_DICT_POWERMETER = {
                vol.Required('power'): vol.Any(None, cv.positive_int),
                vol.Required('energy'): vol.Any(None, cv.positive_int),
                }

SCHEMA_DICT_SWITCH = {
                vol.Required('state'): vol.Any(None, cv.boolean),
                vol.Required('mode'): vol.Any(None, cv.string),
                vol.Required('lock'): vol.Any(None, cv.boolean),
                vol.Required('devicelock'): vol.Any(None, cv.boolean),
                }

SCHEMA_DICT_DEVICE = vol.Schema({
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
            vol.Optional('switch'):           SCHEMA_DICT_SWITCH,
            vol.Optional('powermeter'):       SCHEMA_DICT_POWERMETER,
            vol.Optional('temperature'):      SCHEMA_DICT_TEMPERATURE,
            vol.Optional('hkr'):              SCHEMA_DICT_HKR,
            vol.Required('private_updated'):  cv.boolean,
        }, extra=vol.ALLOW_EXTRA)

ATTR_BATTERY_STATE = "state"

ATTR_BATTERY_STATE_OK = "Ok"
ATTR_BATTERY_STATE_LOW = "Low"

BATTERY_STATES = [ATTR_BATTERY_STATE_OK, ATTR_BATTERY_STATE_LOW]

IDENTIFY_BATTERY_SCHEMA = vol.Schema({
    vol.Required(ATTR_BATTERY_STATE): vol.In(BATTERY_STATES)
})

BIT_MASK_THERMOSTAT    = (1 <<  6)
BIT_MASK_POWERMETER    = (1 <<  7)
BIT_MASK_TEMPERATURE   = (1 <<  8)
BIT_MASK_SWITCH        = (1 <<  9)
BIT_MASK_REPEATER      = (1 << 10)

_LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    """Setup the avm_smarthome component."""
    
    # Log into Fritz Box
    __fritz = AvmHomeAutomationBase(hass, config)
        
    # States are in the format DOMAIN.OBJECT_ID
    #hass.states.set('hello_state.Hello_State', 'Test Text')    
      
    return True

class AvmHomeAutomationBase(object):
    """AvmHomeAutomationBase"""
    def __init__(self, hass, config):
        from fritzhome.fritz import FritzBox
        
        if DATA_AVM_HOMEAUTOMATION not in hass.data:
            hass.data[DATA_AVM_HOMEAUTOMATION] = {}
            
        self.hass   = hass
        self.config = config
        
        host     = config[DOMAIN].get(CONF_HOST)
        username = config[DOMAIN].get(CONF_USERNAME)
        password = config[DOMAIN].get(CONF_PASSWORD)
        
        _LOGGER.debug("Host %s Username %s Password %s ", host, username, password)
        
        # Log into FRITZ!Box
        self.__fritz = FritzBox(host, username, password)
        try:
            self.__fritz.login()
        except Exception:
            _LOGGER.error("Login to FRITZ!Box failed")
            return
        
        # Devices are stored as {ain: {bitmask: functionbitmask, dict: Dictionary, instance: object}, ...}
        self._devices = {}
        
        self._devices_xml = self.get_devices_xml()
        __new_devices = self.get_devices_from_xml()
        
        hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN] = self
        
        self.update_devices(__new_devices)
                
        #_LOGGER.debug(dumps(self._devices, indent=4))
                
                
        # Schedule periodic device update
        #track_time_interval(hass, self._update_device_dicts, SCAN_INTERVAL_VARIABLES)
                
        interval = config.get(SCAN_INTERVAL_VARIABLES) or timedelta(seconds=5)
        async_track_time_interval(hass, self.async_update_device_dicts, interval)

        return
    
    @asyncio.coroutine
    def async_get_devices_xml(self):
        from xml.etree import ElementTree as ET
        try:
            __devices = self.__fritz.homeautoswitch("getdevicelistinfos") 
        except Exception:
            _LOGGER.error("Login to Fritz!Box failed")
            return
            
        return ET.fromstring(__devices)
    
    @asyncio.coroutine
    def async_update_device_dicts(self, event):
        """Update all the SMA sensors."""
        try:
            self._devices_xml = yield from self.async_get_devices_xml()
        except Exception as e:
            return
        else:
            if self._devices_xml is None:
                return
        
        tasks = []
        for __ain in self._devices.keys():
            self._devices[__ain]['dict'] = self._create_device_dict(__ain)
            task = self._devices[__ain]['instance'].async_update_dict()
            if task:
                tasks.append(task)

        if tasks:
            yield from asyncio.wait(tasks, loop=self.hass.loop)
            
        return
            
        
    def _update_device_dicts(self, now):
        """Periodically updates device Dictionaries"""
        self._devices_xml = self.get_devices_xml()
        
        for __ain in self._devices.keys():
            self._devices[__ain]['dict'] = self._create_device_dict(__ain)
            self._devices[__ain]['instance'].update_dict()
            
        return

    
    
    def name(self):
        return __name__ 
        
    def get_devices_xml(self):
        from xml.etree import ElementTree as ET
        try:
            __devices = self.__fritz.homeautoswitch("getdevicelistinfos") 
        except Exception:
            _LOGGER.error("Login to Fritz!Box failed")
            return
            
        return ET.fromstring(__devices)
    
    def get_devices_from_xml(self):
        # Get all devices, but don't create objects
        if self._devices_xml == None:
            self._devices_xml = self.get_devices_xml()
            
        __devices = {}

        for device_xml in self._devices_xml.findall("device"):
            __devices.update({device_xml.attrib['identifier']: {'bitmask': device_xml.attrib['functionbitmask'], 'dict': None, 'instance': None}})
            
        #for device_xml in devices_xml.findall("group"):
        #    __devices.update({device_xml.attrib['identifier']: None})
            
        return __devices
    
    def get_device_xml(self, ain):
        if self._devices_xml == None:
            self._devices_xml = self.get_devices_xml()
        return self._devices_xml.find("device[@identifier='" + ain + "']")
    
    def get_device_dict(self, ain):
        if ain in self._devices.keys():
            if self._devices[ain]['dict'] == None:
                self._devices[ain]['dict'] = self._create_device_dict(ain)
            
            dict = self._devices[ain]['dict']
            if dict == None:
                _LOGGER.error("'%s' has no device dictionary" % ain)
            else:
                self._devices[ain]['private_updated'] = False
                #_LOGGER.debug(dumps(dict, indent=4))
                return dict
        else:
            _LOGGER.error("'%s' not in Device List" % ain)
            
        return None
        
    def update_devices(self, new_device_list):
        """Compares new device list to current device list, adds and Removes devices"""
        __added_devices = {}
        __removed_devices = {}
        
        for __ain in new_device_list.keys() - self._devices.keys():
            __added_devices.update({__ain: new_device_list[__ain]}) 
        
        for __ain in self._devices.keys() - new_device_list.keys():
            __removed_devices.update({__ain: new_device_list[__ain]})
  
        if __added_devices:
            self._devices.update(__added_devices)
            self._load_devices(__added_devices)
            
        if __removed_devices:
            for __ain, __value in __removed_devices.items():
                if __value != None:
                    if __value['instance'] != None:
                        __value['instance'].remove()
                self._devices.pop(__ain, None)

        return
    
    def _load_devices(self, device_list):
        for component_name, discovery_type in (
            ('switch', DISCOVER_SWITCHES),
            ('climate', DISCOVER_CLIMATE)
        ):
            # Get all devices of a specific type
            found_device_list = self._get_devices_by_type(device_list, discovery_type)
            
            # When devices of this type are found
            # they are setup in HA and an event is fired
            if found_device_list:
                # Fire discovery event
                __ain_list = [k for k in found_device_list.keys()]
                _LOGGER.debug( "Component '%s' going to add actors '%s'" % ( component_name, ', '.join(__ain_list)) )
                discovery.load_platform(self.hass, component_name, DOMAIN, {ATTR_DISCOVER_DEVICES: __ain_list}, self.config)
                
        return
    
    def _create_device_dict(self, __ain):
        __device_xml = self.get_device_xml(__ain)
            
        from xml.etree import ElementTree as ET
        temp = xmltodict.parse( ET.tostring( __device_xml ) )
        temp['device']['private_updated'] = True
        
        try:
            SCHEMA_DICT_DEVICE(temp['device'])
        except vol.MultipleInvalid as e:
            _LOGGER.error("Schema validation failed: %s" % str(e))
        else:
            return temp['device']
                
    def _get_devices_by_type(self, device_list, discovery_type):
        """Returns devices of a specific type"""
        __new_device_list = {}
                
        for __ain, __value in device_list.items():
            __bitmask = __value['bitmask']
            if discovery_type == DISCOVER_SWITCHES:
                if bool( (int(__bitmask) & BIT_MASK_SWITCH) == BIT_MASK_SWITCH ) == True:
                    __new_device_list.update({__ain: __value})
            elif discovery_type == DISCOVER_CLIMATE:
                if bool( (int(__bitmask) & BIT_MASK_THERMOSTAT) == BIT_MASK_THERMOSTAT ) == True:
                    __new_device_list.update({__ain: __value})
                    
        return __new_device_list
    
        # bool( (__bitmask & BIT_MASK_THERMOSTAT) == BIT_MASK_THERMOSTAT )
        # bool( (__bitmask & BIT_MASK_POWERMETER) == BIT_MASK_POWERMETER )
        # bool( (__bitmask & BIT_MASK_TEMPERATURE) == BIT_MASK_TEMPERATURE )
        # bool( (__bitmask & BIT_MASK_SWITCH) == BIT_MASK_SWITCH )
        # bool( (__bitmask & BIT_MASK_REPEATER) == BIT_MASK_REPEATER )
                
    def send_switch_command(self, _params, ain=None): 
        """
        Call a switch method.
        Should only be used by internal library functions.
        """
        assert self.__fritz.sid, "Not logged in"
        #            'switchcmd': cmd,
        params = {

            'sid': self.__fritz.sid,
        }
        if ain:
            params['ain'] = ain
        params.update(_params)
        url = self.__fritz.base_url + '/webservices/homeautoswitch.lua'
        response = self.__fritz.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.text.strip()
    
HM_ATTRIBUTE_SUPPORT = {
    'temperature.celsius' : [ATTR_CURRENT_TEMPERATURE, {}],
    'hkr.batterylow': ['Battery', {0: 'High', 1: 'Low'}],
    'powermeter.power': ['Power', {}],
    'powermeter.energy': ['Current', {}],
}

from typing import Optional, List

class AvmHomeAutomationDevice(Entity):
    """An abstract class for a AvmHomeAutomationDevice entity."""
    
    def __init__(self, hass, ain, aha):
        """Initialize the switch."""
                
        self._aha = aha
        self._ain = ain
        
        self._dict = None
        self.update_dict()
        
        self.units = hass.config.units
        
        aha._devices[ain]['instance'] = self
        
        #from json import dumps
        #_LOGGER.debug(dumps(self._dict, indent=4))
                
        return
    
    def update_dict(self):
        """" Get a new dict from the AvmHomeAutomationBase """
        dict = self._aha.get_device_dict(self._ain)
        
        if dict['private_updated'] == True:
            try:
                self._validate_schema(dict)
            except vol.MultipleInvalid as e:
                _LOGGER.error("Schema validation failed: %s" % str(e))
            else:
                self._dict = dict
                self._assumed_state = False
        else:
            # Device dict seems to be somewaht out of date
            self._assumed_state = True                    
        return
    
    def async_update_dict(self):
        """" Get a new dict from the AvmHomeAutomationBase """
        dict = self._aha.get_device_dict(self._ain)
        
        if dict['private_updated'] == True:
            try:
                self._validate_schema(dict)
            except vol.MultipleInvalid as e:
                _LOGGER.error("Schema validation failed: %s" % str(e))
            else:
                self._dict = dict
                self._assumed_state = False
        else:
            # Device dict seems to be somewaht out of date
            self._assumed_state = True                    
        return self.async_update_ha_state() if dict['private_updated'] == True else None
    
    def _validate_schema(self, value):
        SCHEMA_DICT_DEVICE(value)

    ## Import from Entity
    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return True

    @property
    def name(self) -> Optional[str]:
        """Return the name of the entity."""
        return self._dict['name']
            
    @property
    def device_class(self) -> str:
        """Return the class of this device, from component DEVICE_CLASSES."""
        return None
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return None
    
    @property
    def entity_picture(self):
        """Return the entity picture to use in the frontend, if any."""
        return None

    @property
    def hidden(self) -> bool:
        """Return True if the entity should be hidden from UIs."""
        return False

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return None
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(int(self._dict['present']))
    
    @property
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return True
    
    @property
    def force_update(self) -> bool:
        """Return True if state updates should be forced.

        If True, a state change will be triggered anytime the state property is
        updated, not just when the value changes.
        """
        return False
    
    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return int(self._dict['@functionbitmask'])
    
    def update(self):
        """
        Retrieve latest state.
        """
        #self.update_dict()
        
        return
    
    ## Import from Climate (not in the parent list)
    @property
    def current_temperature(self):
        """Return the current _temperature."""
        return self.units.temperature(float(int(self._dict['temperature']['celsius'])) / 10.0, TEMP_CELSIUS)
    