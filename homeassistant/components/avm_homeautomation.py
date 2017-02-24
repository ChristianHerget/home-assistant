'''
Created on 16.02.2017

@author: Christian
'''

import logging
import asyncio
<<<<<<< HEAD
=======
import xmltodict
from json import dumps
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
<<<<<<< HEAD
from typing import Optional

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, CONF_USERNAME, CONF_PASSWORD, 
    CONF_HOST, ATTR_ENTITY_ID, TEMP_CELSIUS, CONF_SCAN_INTERVAL)
from homeassistant.helpers import discovery
from homeassistant.helpers.aiohttp_client import async_get_clientsession
=======

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, CONF_USERNAME, CONF_PASSWORD, 
    CONF_HOST, ATTR_ENTITY_ID, TEMP_CELSIUS)
from homeassistant.helpers import discovery
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

DOMAIN = 'avm_homeautomation'
REQUIREMENTS = ['xmltodict==0.10.2']

<<<<<<< HEAD
DISCOVER_SWITCHES = DOMAIN + '.switch'
DISCOVER_CLIMATE  = DOMAIN + '.climate'

ATTR_DISCOVER_DEVICES   = 'devices'
=======
SCAN_INTERVAL_VARIABLES = timedelta(seconds=15)

DISCOVER_SWITCHES = DOMAIN + '.switch'
DISCOVER_CLIMATE = DOMAIN + '.climate'

ATTR_DISCOVER_DEVICES = 'devices'

>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
DATA_AVM_HOMEAUTOMATION = 'data' + DOMAIN

# Standard FRITZ!Box IP
DEFAULT_HOST = 'fritz.box'
<<<<<<< HEAD
# Default FRITZ!Box User Name, this isn't important as FRITZ!Box uses no username by default
DEFAULT_USERNAME = ''
# Default Update Interval
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_HOST,          default=DEFAULT_HOST):     cv.string,
        vol.Optional(CONF_USERNAME,      default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD):                                cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): 
            vol.All(vol.Coerce(int), vol.Range(min=1)),
    }),
}, extra=vol.ALLOW_EXTRA)

=======
# Standard FRITZ!Box User Name
DEFAULT_USERNAME = 'admin'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
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
                vol.Optional('devicelock'): vol.Any(None, cv.positive_int),
                vol.Optional('errorcode'): vol.Any(None, cv.positive_int),
                vol.Optional('batterylow'): vol.Any(None, cv.positive_int),
                vol.Optional('nextchange'): vol.Schema({
                     vol.Optional('endperiod'): vol.Any(None, cv.positive_int),
                     vol.Optional('tchange'): vol.Any(None, cv.positive_int),
                    }),
                }

SCHEMA_DICT_POWERMETER = {
                vol.Required('power'): vol.Any(None, cv.positive_int),
                vol.Required('energy'): vol.Any(None, cv.positive_int),
                }

SCHEMA_DICT_SWITCH = {
                vol.Required('state'): vol.Any(None, cv.boolean),
                vol.Optional('mode'): vol.Any(None, cv.string),
                vol.Optional('lock'): vol.Any(None, cv.boolean),
                vol.Optional('devicelock'): vol.Any(None, cv.boolean),
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

BIT_MASK_THERMOSTAT    = (1 <<  6)
BIT_MASK_POWERMETER    = (1 <<  7)
BIT_MASK_TEMPERATURE   = (1 <<  8)
BIT_MASK_SWITCH        = (1 <<  9)
BIT_MASK_REPEATER      = (1 << 10)

_LOGGER = logging.getLogger(__name__)

@asyncio.coroutine
def async_setup(hass, config):
    """Setup the avm_smarthome component."""
<<<<<<< HEAD
=======
    import aiohttp
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
    
    host     = config[DOMAIN].get(CONF_HOST)
    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
<<<<<<< HEAD
    interval = config[DOMAIN].get(CONF_SCAN_INTERVAL)
        
    # Get aiohttp session
    session = async_get_clientsession(hass)
=======
    interval = config.get(SCAN_INTERVAL_VARIABLES) or timedelta(seconds=30)
    
    _LOGGER.debug("Host: %s Username: %s Password: %s ", host, username, password)
    
    # Create async http session
    session = aiohttp.ClientSession(loop=hass.loop)
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
    
    # Create pyFBC to communicate with the FRITZ!Box
    fbc = pyFBC(session, host, username, password)
    
    # Log into FRITZ!Box
<<<<<<< HEAD
    while True: 
        try:
            yield from fbc.new_session()
        except Exception as e:
            _LOGGER.warning("Couldn't log into FRITZ!Box: %s" % str(e))
            # Wait 10 seconds
            yield from asyncio.sleep(60, loop=hass.loop)
        else:
            break
        
    # If login succeeded
    ahab = AvmHomeAutomationBase(hass, config, fbc)
    # Get initial device list from FRITZ!Box
    new_devices = yield from ahab.async_get_devices_from_xml()
    # Add new devices to list and call platform(s)
    ahab.update_devices(new_devices)
    # Schedule periodic device update
    async_track_time_interval(hass, ahab.async_update_device_dicts, interval)
    
    # Ensure we logout on shutdown
    @asyncio.coroutine
    def async_shutdown(call):
        fbc.async_close_session()
    
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_shutdown)
    
    return True
=======
    if (yield from fbc.new_session()) == True:
        # If login succeeded
        ahab = AvmHomeAutomationBase(hass, config, fbc)
        # Get initial device list from FRITZ!Box
        new_devices = yield from ahab.async_get_devices_from_xml()
        # Add new devices to list and call platform(s)
        ahab.update_devices(new_devices)
        # Schedule periodic device update
        async_track_time_interval(hass, ahab.async_update_device_dicts, interval)
        
        return True
    
    return False
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72

class pyFBC(object):
    """Python FRITZ!Box Connect"""
    
    def __init__(self, session, host, user, password):
        self._aio_session = session
        self._host        = host
        self._user        = user
        self._password    = password
        self._aha_sid     = None
        self._rights      = None        
        
        self.URL_LOGIN  = "http://{}/login_sid.lua"
        self.URL_SWITCH = "http://{}/webservices/homeautoswitch.lua"
        
        return
<<<<<<< HEAD
            
    @asyncio.coroutine
    def new_session(self):
        """Establish a new session."""
        from aiohttp.web_exceptions import HTTPForbidden
        from xml.etree.ElementTree import fromstring
        import xmltodict
=======
    
    def __del__(self):
        self.close_session()
        
    @asyncio.coroutine
    def new_session(self):
        """Establish a new session."""
        from xml.etree.ElementTree import fromstring
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
        from hashlib import md5
        
        res = yield from self._fetch_string(self.URL_LOGIN.format(self._host))
        dom = fromstring(res)
        sid = dom.findtext('./SID')
        challenge = dom.findtext('./Challenge')
        
        if sid == '0000000000000000':
            md5_var = md5()
            md5_var.update(challenge.encode('utf-16le'))
            md5_var.update('-'.encode('utf-16le'))
            md5_var.update(self._password.encode('utf-16le'))
            response = challenge + '-' + md5_var.hexdigest()
            
            params = {'username': self._user,'response': response}
            
            res = yield from self._fetch_string(self.URL_LOGIN.format(self._host), params=params)
            dom = fromstring(res)
            sid = dom.findtext('./SID')
            
            from xml.etree import ElementTree as ET
            temp = xmltodict.parse( ET.tostring( dom.find("Rights") ) )
            self._rights = temp['Rights']
            
            #print(dumps(self._rights, indent=4))
            
        if sid == '0000000000000000':
<<<<<<< HEAD
            raise HTTPForbidden() # 403
=======
            raise BaseException('access denied')
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
        
        self._aha_sid = sid
        
        return True
    
    @asyncio.coroutine
<<<<<<< HEAD
    def async_close_session(self):
=======
    def close_session(self):
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
        """Close the session login."""
        if self._aha_sid is None:
            return
        else:
            yield from self._fetch_string(self.URL_LOGIN.format(self._host), {'sid': self._aha_sid, 'logout':''})
        self._aio_session
        self._sha_sid = None
        
        
    @asyncio.coroutine
    def _execute(self, url, params=None):
        """Fetch file for requests."""
        import async_timeout
        
        with async_timeout.timeout(10):
            res = yield from self._aio_session.get(url, params=params)
            return res
        
    @asyncio.coroutine
    def _fetch_string(self, url, params=None):
        """Fetch string for requests."""
<<<<<<< HEAD
        from aiohttp.web_exceptions import (
            HTTPBadRequest, HTTPForbidden, HTTPInternalServerError)
        
        res = yield from self._execute(url, params)
=======
        res = yield from self._execute(url, params)

>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
        status = res.status
        
        if status == 200:
            string = yield from res.text()
            return string.strip()
        elif status == 400:
            _LOGGER.error("Status '%s' Bad Request" % status)
<<<<<<< HEAD
            raise HTTPBadRequest()
=======
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
        elif status == 403:
            yield from res.release()
            _LOGGER.debug("Status '%s' Forbidden, try to reconnect" % status)
            try:
                if (yield from self.new_session()) == True:
                    if 'sid' in params:
                        params['sid'] = self._aha_sid
                    return (yield from self._fetch_string(url, params))
<<<<<<< HEAD
            except Exception:
                raise HTTPForbidden()
        elif status == 500:
            yield from res.release()
            _LOGGER.debug("Status '%s' Internal Server" % status)
            raise HTTPInternalServerError()
=======
            except Exception as e:
                raise e
        elif status == 500:
            yield from res.release()
            _LOGGER.debug("Status '%s' Internal Server" % status)
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
        else:
            yield from res.release()
            _LOGGER.error("Status '%s' Unknown" % status)
            raise Exception
        
        return 'Inval'
<<<<<<< HEAD
=======

>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
    
    @asyncio.coroutine
    def send_switch_command(self, params, ain=None):
        if params == None:
            params = {}
        
        if self._aha_sid == None:
            raise Exception
        else:
            params.update({'sid': self._aha_sid})
        
        if ain != None:
            params.update({'ain': ain})
        
        url = self.URL_SWITCH.format(str(self._host))
        
        try:
            res = yield from self._fetch_string(url, params=params)
        except Exception as e:
            raise e
        else:
            return res
    
    @asyncio.coroutine
    def get_device_xml_as_string(self):
        from xml.etree.ElementTree import fromstring
        try:
            __devices = yield from self.send_switch_command({"switchcmd": "getdevicelistinfos"})
        except Exception as e:
            raise e
            return None
        else:
            dom = fromstring(__devices)
            return dom

class AvmHomeAutomationBase(object):
    """AvmHomeAutomationBase"""
    
    def __init__(self, hass, config, fbc):      
        if DATA_AVM_HOMEAUTOMATION not in hass.data:
            hass.data[DATA_AVM_HOMEAUTOMATION] = {}
            
        self._hass   = hass
        self._config = config
        self._fbc    = fbc
                        
        self._devices_xml = None
        # Devices are stored as {ain: {bitmask: functionbitmask, dict: Dictionary, instance: object}, ...}
        ## todo: remove bitmask, as it is in dict
        self._devices = {}
        
        hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN] = self

        return
    
    def __del__(self):
        pass#self._conn.close()
                    
    @asyncio.coroutine
    def async_update_device_dicts(self, event):
        """Update all the FRITZ!DECT stuff"""

        try:
            self._devices_xml = yield from self.async_get_devices_xml()
        except Exception as e:
            _LOGGER.error("async_get_devices_xml failed: %s" % str(e))
            return
        else:
            if self._devices_xml is None:
                return
        
        tasks = []
        for __ain in self._devices.keys():
            _LOGGER.debug("ASYNC Update: %s" % __ain)
            self._devices[__ain]['dict'] = self._create_device_dict(__ain)
            task = self._devices[__ain]['instance'].async_update_dict()
            if task:
                tasks.append(task)

        if tasks:
            yield from asyncio.wait(tasks, loop=self._hass.loop)
            
        return
                
    @asyncio.coroutine
    def async_get_devices_xml(self):
        from xml.etree import ElementTree as ET
        try:
            devices = yield from self._fbc.send_switch_command({"switchcmd": "getdevicelistinfos"}) 
        except Exception as e:
            _LOGGER.error("Login to FRITZ!Box failed: %s" % str(e))
            return
            
        return ET.fromstring(devices)
            
    @asyncio.coroutine
    def async_get_devices_from_xml(self):
        # Get all devices, but don't create objects
        if self._devices_xml == None:
            self._devices_xml = yield from self.async_get_devices_xml()
            
        devices = {}

        for device_xml in self._devices_xml.findall("device"):
            devices.update({device_xml.attrib['identifier']: {'bitmask': device_xml.attrib['functionbitmask'], 'dict': None, 'instance': None}})
            
        #for device_xml in devices_xml.findall("group"):
        #    devices.update({device_xml.attrib['identifier']: None})
            
        return devices
    
    @asyncio.coroutine
    def async_send_switch_command(self, params, ain=None):
        # Forwards switch commands
        try:
            return self._fbc.send_switch_command(params, ain)
        except Exception as e:
            raise e
    
    def get_device_xml(self, ain):
        if self._devices_xml == None:
            raise Exception
        else:
            return self._devices_xml.find("device[@identifier='" + ain + "']")
    
    def get_device_dict(self, ain):
        if ain in self._devices.keys():
            if self._devices[ain]['dict'] == None:
                self._devices[ain]['dict'] = self._create_device_dict(ain)
            
            __dict = self._devices[ain]['dict']
            if dict == None:
                _LOGGER.error("'%s' has no device dictionary" % ain)
            else:
                self._devices[ain]['private_updated'] = False
                #_LOGGER.debug(dumps(dict, indent=4))
                return __dict
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
            # Add new devices to central dictdevice list (dict)
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
                discovery.load_platform(self._hass, component_name, DOMAIN, {ATTR_DISCOVER_DEVICES: __ain_list}, self._config)
                
        return
    
    def _create_device_dict(self, __ain):
<<<<<<< HEAD
        from xml.etree import ElementTree as ET
        import xmltodict
        __device_xml = self.get_device_xml(__ain)
            
=======
        __device_xml = self.get_device_xml(__ain)
            
        from xml.etree import ElementTree as ET
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72
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
<<<<<<< HEAD
=======
    
        # bool( (__bitmask & BIT_MASK_THERMOSTAT) == BIT_MASK_THERMOSTAT )
        # bool( (__bitmask & BIT_MASK_POWERMETER) == BIT_MASK_POWERMETER )
        # bool( (__bitmask & BIT_MASK_TEMPERATURE) == BIT_MASK_TEMPERATURE )
        # bool( (__bitmask & BIT_MASK_SWITCH) == BIT_MASK_SWITCH )
        # bool( (__bitmask & BIT_MASK_REPEATER) == BIT_MASK_REPEATER )

from typing import Optional
>>>>>>> 86eb1ebf935324ca9d008d83e44137680c241c72

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
        __dict = self._aha.get_device_dict(self._ain)
        
        if __dict['private_updated'] == True:
            try:
                self._validate_schema(__dict)
            except vol.MultipleInvalid as e:
                _LOGGER.error("Schema validation failed: %s" % str(e))
            else:
                self._dict = __dict
                self._assumed_state = False
        else:
            # Device dict seems to be somewaht out of date
            self._assumed_state = True                    
        return
    
    def async_update_dict(self):
        """" Get a new dict from the AvmHomeAutomationBase """
        __dict = self._aha.get_device_dict(self._ain)
        
        if __dict['private_updated'] == True:
            try:
                self._validate_schema(__dict)
            except vol.MultipleInvalid as e:
                _LOGGER.error("Schema validation failed: %s" % str(e))
            else:
                self._dict = __dict
                self._assumed_state = False
        else:
            # Device dict seems to be somewaht out of date
            self._assumed_state = True                    
        return self.async_update_ha_state() if __dict['private_updated'] == True else None
    
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
    
    @asyncio.coroutine
    def async_update(self):
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
    