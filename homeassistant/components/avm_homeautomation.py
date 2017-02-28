"""
Support for FRITZ!DECT devices (AVM Home Automation).

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/avm_homeautomation/
"""

import logging
import asyncio
from datetime import timedelta

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from typing import Optional

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, CONF_USERNAME, CONF_PASSWORD,
    CONF_HOST, TEMP_CELSIUS, CONF_SCAN_INTERVAL)
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = 'avm_homeautomation'
REQUIREMENTS = ['xmltodict==0.10.2']

DISCOVER_SWITCHES = DOMAIN + '.switch'
DISCOVER_CLIMATE = DOMAIN + '.climate'

ATTR_DISCOVER_DEVICES = 'devices'

DATA_AVM_HOMEAUTOMATION = 'data' + DOMAIN

# Standard FRITZ!Box IP
DEFAULT_HOST = 'fritz.box'
# Default FRITZ!Box User Name
# this isn't important as FRITZ!Box uses no user name by default
DEFAULT_USERNAME = ''
# Default Update Interval
DEFAULT_SCAN_INTERVAL = 30

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_HOST, default=DEFAULT_HOST):     cv.string,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD):                                cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
            vol.All(vol.Coerce(int), vol.Range(min=1)),
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

BIT_MASK_THERMOSTAT = (1 << 6)
BIT_MASK_POWERMETER = (1 << 7)
BIT_MASK_TEMPERATURE = (1 << 8)
BIT_MASK_SWITCH = (1 << 9)
BIT_MASK_REPEATER = (1 << 10)

STATE_MANUAL = "manual"

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup(hass, config):
    """Setup the avm_smarthome component."""
    from aiohttp.web_exceptions import HTTPClientError
    host = config[DOMAIN].get(CONF_HOST)
    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    interval = timedelta(seconds=config[DOMAIN].get(CONF_SCAN_INTERVAL))
    # Get aiohttp session
    session = async_get_clientsession(hass)
    # Create pyFBC to communicate with the FRITZ!Box
    fbc = YaFBC(session, host, username, password)
    # Log into FRITZ!Box
    while True:
        try:
            yield from fbc.async_new_session()
        except HTTPClientError as exception:
            _LOGGER.warning("Couldn't log into FRITZ!Box: %s", str(exception))
            # Wait 10 seconds
            yield from asyncio.sleep(timedelta(seconds=fbc.blocktime + 10),
                                     loop=hass.loop)
        else:
            break
    # If login succeeded
    ahab = AvmHomeAutomationBase(hass, config, fbc)

    # Add FRITZ!DECT Actuators
    yield from ahab.async_update_fritz_actuator_dicts(None)

    # Schedule periodic device update
    async_track_time_interval(hass,
                              ahab.async_update_fritz_actuator_dicts,
                              interval)

    @asyncio.coroutine
    def async_shutdown(call):
        """Ensure we logout on shutdown."""
        fbc.async_close_session()

    # Ensure we logout on shutdown
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_shutdown)
    return True


class YaFBC(object):
    """Yet an Async FRITZ!Box Connector for Python."""

    URL_LOGIN = "http://{}/login_sid.lua"
    URL_SWITCH = "http://{}/webservices/homeautoswitch.lua"

    def __init__(self, session, host, user, password):
        """Initialize FB connect."""
        self._aio_session = session
        self._host = host
        self._user = user
        self._password = password
        self._sid = None
        self._rights = None
        self._blocktime = 0
        return

    @property
    def user_rights(self) -> dict:
        """Retun User Right as reported by FRITZ!Box."""
        return self._rights

    @property
    def sid(self) -> str:
        """Return Session ID."""
        return self._sid

    @property
    def blocktime(self) -> int:
        """Return Blocktime, important incase login failed."""
        return self._blocktime or 60

    @asyncio.coroutine
    def async_new_session(self) -> bool:
        """Establish a new session."""
        from aiohttp.web_exceptions import HTTPForbidden
        from xml.etree.ElementTree import fromstring
        import xmltodict
        from hashlib import md5

        res = yield from self.async_fetch_string(
            self.URL_LOGIN.format(self._host))

        # Parse XML document
        dom = fromstring(res)
        sid = dom.findtext('./SID')
        challenge = dom.findtext('./Challenge')

        # Excecute the following only if we havn'T already a valid SID
        if sid == '0000000000000000':
            # Calculate MD5 check sum (response)
            md5_var = md5()
            md5_var.update(challenge.encode('utf-16le'))
            md5_var.update('-'.encode('utf-16le'))
            md5_var.update(self._password.encode('utf-16le'))
            response = challenge + '-' + md5_var.hexdigest()

            # Create params to send to FRITZ!Box
            params = {'username': self._user, 'response': response}
            res = yield from self.async_fetch_string(
                self.URL_LOGIN.format(self._host), params=params)
            dom = fromstring(res)
            sid = dom.findtext('./SID')

            # Extract Right and BlockTime
            from xml.etree import ElementTree as ET
            temp = xmltodict.parse(ET.tostring(dom.find("Rights")))
            self._rights = temp['Rights']

            if sid == '0000000000000000':
                self._blocktime = int(temp['BlockTime'] or 60)
                raise HTTPForbidden()  # 403
            else:
                self._sid = sid
        return True

    @asyncio.coroutine
    def async_close_session(self) -> None:
        """Close the session login."""
        if self._sid is None:
            return
        else:
            yield from self.async_fetch_string(
                self.URL_LOGIN.format(self._host),
                {'sid': self._sid, 'logout': ''}
                )
        self._aio_session = None
        self._sid = None

    @asyncio.coroutine
    def async_execute(self, url, params=None):
        """Fetch file for requests."""
        import async_timeout
        with async_timeout.timeout(10):
            res = yield from self._aio_session.get(url, params=params)
            return res

    @asyncio.coroutine
    def async_fetch_string(self, url, params=None) -> str:
        """Fetch string for requests."""
        from aiohttp.web_exceptions import (
            HTTPBadRequest, HTTPForbidden, HTTPInternalServerError)
        res = yield from self.async_execute(url, params)
        status = res.status
        if status == 200:
            string = yield from res.text()
            return string.strip()
        elif status == 400:
            _LOGGER.error("Status '%s' Bad Request", status)
            raise HTTPBadRequest()
        elif status == 403:
            yield from res.release()
            _LOGGER.debug("Status '%s' Forbidden, try to reconnect", status)
            try:
                if (yield from self.async_new_session()):
                    if 'sid' in params:
                        params['sid'] = self._sid
                    return (yield from self.async_fetch_string(url, params))
            except Exception:
                raise HTTPForbidden()
        elif status == 500:
            yield from res.release()
            _LOGGER.debug("Status '%s' Internal Server", status)
            raise HTTPInternalServerError()
        else:
            yield from res.release()
            _LOGGER.error("Status '%s' Unknown", status)
            raise Exception
        return None

    @asyncio.coroutine
    def async_send_switch_command(self, params, ain=None) -> str:
        """Send command to FRITZ!Box via homeautoswitch.lua."""
        if params is None:
            params = {}
        if self._sid is None:
            raise Exception
        else:
            params.update({'sid': self._sid})
        if ain is not None:
            params.update({'ain': ain})
        url = self.URL_SWITCH.format(str(self._host))
        res = yield from self.async_fetch_string(url, params=params)

        return res

    @asyncio.coroutine
    def async_get_device_xml_as_string(self) -> str:
        """Get the XML file with the device states from FRITZ!Box."""
        from xml.etree.ElementTree import fromstring
        __devices = yield from self.async_send_switch_command(
            {"switchcmd": "getdevicelistinfos"})

        dom = fromstring(__devices)
        return dom


class AvmHomeAutomationBase(object):
    """AvmHomeAutomationBase."""

    def __init__(self, hass, config, fbc):
        """Initialize Component."""
        if DATA_AVM_HOMEAUTOMATION not in hass.data:
            hass.data[DATA_AVM_HOMEAUTOMATION] = {}
        self.hass = hass
        self._config = config
        self._fbc = fbc
        # Devices are stored as
        # {ain: {dict: Dictionary, instance: object}, ...}
        self._fritz_actuator_dicts_xml = dict()
        hass.data[DATA_AVM_HOMEAUTOMATION][DOMAIN] = self
        return

    @asyncio.coroutine
    def async_update_fritz_actuator_dicts(self, event) -> None:
        """Update all the FRITZ!DECT state dicts."""
        new_list = yield from self.async_get_fritz_actuator_dicts()

        new_dicts = new_list['actuators']
        for ain, new_dict in new_dicts.items():
            if ain in self._fritz_actuator_dicts_xml:
                if new_dict != self._fritz_actuator_dicts_xml[ain]['dict']:
                    _LOGGER.debug("Schedule ASYNC Update of '%s'", ain)
                    self._fritz_actuator_dicts_xml[ain]['dict'] = new_dict
                    self._fritz_actuator_dicts_xml[ain]['instance'].\
                        schedule_update_ha_state(force_refresh=False)
            else:
                # Create new entry in central actuator dict
                new_device = {ain: {'dict': new_dict, 'instance': None}}
                self._fritz_actuator_dicts_xml.update(new_device)
                self._load_new_device(new_device)

        for ain in self._fritz_actuator_dicts_xml.keys() - new_dicts.keys():
            _LOGGER.debug("Going to remove: %s", ain)
            if self._fritz_actuator_dicts_xml[ain]['instance'] is not None:
                yield from self._fritz_actuator_dicts_xml[ain]['instance'].\
                  async_remove()
                self._fritz_actuator_dicts_xml.pop(ain, None)

        return

    @asyncio.coroutine
    def async_get_fritz_actuator_dicts(self) -> dict:
        """
        Fetch new xml with actuator states from FRITZ!Box.

        Converts it to a Python dict with AINs as keys.
        """
        import xmltodict
        try:
            devices = yield from self._fbc.async_send_switch_command(
                {"switchcmd": "getdevicelistinfos"})
        except Exception as e:
            _LOGGER.error("Login to FRITZ!Box failed: %s", str(e))
            return
        temp = xmltodict.parse(devices)
        return_val = dict({'actuators': dict(), 'groups': dict()})

        if 'devicelist' in temp:
            for device in temp['devicelist']['device']:
                if '@identifier' in device:
                    ain = device['@identifier']
                    return_val['actuators'].update({ain: device})
            for group in temp['devicelist']['group']:
                if '@identifier' in group:
                    ain = group['@identifier']
                    return_val['groups'].update({ain: group})

        return return_val

    @asyncio.coroutine
    def async_send_switch_command(self, params, ain=None) -> str:
        """Send a switch command to the FRITZ!Box."""
        # Forwards switch commands
        try:
            return (
                yield from self._fbc.async_send_switch_command(params, ain)
                )
        except Exception as e:
            raise e

    def _load_new_device(self, device_list) -> None:
        """Looks up the different device types and loads platform."""
        for component_name, discovery_type in (
                    ('switch', DISCOVER_SWITCHES),
                    ('climate', DISCOVER_CLIMATE)):
            # Get all devices of a specific type
            found_device_list = self._get_devices_by_type(
                device_list, discovery_type)
            # When devices of this type are found
            # they are setup in HA and an event is fired
            if found_device_list:
                # Fire discovery event
                __ain_list = [k for k in found_device_list.keys()]
                _LOGGER.debug("Component '%s' going to add actors '%s'",
                              component_name,
                              ', '.join(__ain_list))
                discovery.load_platform(
                    self.hass,
                    component_name,
                    DOMAIN,
                    {ATTR_DISCOVER_DEVICES: __ain_list},
                    self._config)
        return

    def _get_devices_by_type(self, device_list, discovery_type) -> dict:
        """Returns only devices of a specific type."""
        __new_device_list = {}
        for __ain, __value in device_list.items():
            __bitmask = int(__value['dict']['@functionbitmask'])
            if discovery_type == DISCOVER_SWITCHES:
                if bool((int(__bitmask) & BIT_MASK_SWITCH) ==
                        BIT_MASK_SWITCH):
                    __new_device_list.update({__ain: __value})
            elif discovery_type == DISCOVER_CLIMATE:
                if bool((int(__bitmask) & BIT_MASK_THERMOSTAT) ==
                        BIT_MASK_THERMOSTAT):
                    __new_device_list.update({__ain: __value})
        return __new_device_list


class AvmHomeAutomationDevice(Entity):
    """An abstract class for a AvmHomeAutomationDevice entity."""

    def __init__(self, hass, ain, aha):
        """Initialize the switch."""
        self._aha = aha
        self._ain = ain
        self.hass = hass
        self.units = hass.config.units
        aha._fritz_actuator_dicts_xml[ain]['instance'] = self
        return

    def _validate_schema(self, value):
        """Used to validate the Schema of the dict."""
        SCHEMA_DICT_DEVICE(value)

    @property
    def _dict(self) -> dict:
        return self._aha._fritz_actuator_dicts_xml[self._ain]['dict']

    # Import from Entity
    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

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
        return False

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

    # # Import from Climate (not in the parent list)
    @property
    def current_temperature(self) -> float:
        """Return the current _temperature."""
        if self._dict['temperature']['celsius'] is not None:
            return self.units.temperature(
                float(
                    int(
                        self._dict['temperature']['celsius']
                        )
                    ) / 10.0, TEMP_CELSIUS)
        else:
            return 0.0
