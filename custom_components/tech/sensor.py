"""Platform for sensor integration."""
import logging
from homeassistant.components import sensor
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import TEMP_CELSIUS, PERCENTAGE
from homeassistant.helpers.entity import Entity
from . import assets
from .entity import TileEntity
from .const import (
    DOMAIN,
    TYPE_TEMPERATURE,
    TYPE_TEMPERATURE_CH,
    TYPE_FAN,
    TYPE_VALVE,
    TYPE_FUEL_SUPPLY,
    TYPE_TEXT,
    VALVE_SENSOR_RETURN_TEMPERATURE,
    VALVE_SENSOR_SET_TEMPERATURE,
    VALVE_SENSOR_CURRENT_TEMPERATURE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""
    _LOGGER.debug("Setting up entry for sensors")
    api = hass.data[DOMAIN][config_entry.entry_id]
    controllers = config_entry.data["controllers"]
    _LOGGER.debug("Number of controllers: %s", len(controllers))
    
    
    for controller in controllers:
        controller_udid = controller["udid"]
        _LOGGER.debug("Controller UDID: %s", controller_udid)

        data = await api.module_data(controller_udid)
        tiles = data['tiles']
        _LOGGER.debug("Controller UDID Tiles: %s", tiles)

        entities = []
        for t in tiles:
            tile = tiles[t]
            if tile["visibility"] == False:
                continue
            if tile["type"] == TYPE_TEMPERATURE:
                entities.append(TileTemperatureSensor(tile, api, controller_udid))
            if tile["type"] == TYPE_TEMPERATURE_CH:
                entities.append(TileWidgetSensor(tile, api, controller_udid))
            if tile["type"] == TYPE_FAN:
                entities.append(TileFanSensor(tile, api, controller_udid))
            if tile["type"] == TYPE_VALVE:
                entities.append(TileValveSensor(tile, api, controller_udid))
                #TODO: this class _init_ definition needs to be fixed. See comment below.
                #entities.append(TileValveTemperatureSensor(tile, api, controller_udid, VALVE_SENSOR_RETURN_TEMPERATURE))
                #entities.append(TileValveTemperatureSensor(tile, api, controller_udid, VALVE_SENSOR_SET_TEMPERATURE))
                #entities.append(TileValveTemperatureSensor(tile, api, controller_udid, VALVE_SENSOR_CURRENT_TEMPERATURE))
            if tile["type"] == TYPE_FUEL_SUPPLY:
                entities.append(TileFuelSupplySensor(tile, api, controller_udid))
            if tile["type"] == TYPE_TEXT:
                 entities.append(TileTextSensor(tile, api, controller_udid))
        _LOGGER.debug("Controller Entities: %s", entities)
        async_add_entities(entities)

        zones = data['zones']

        battery_devices = filter(lambda deviceIndex: is_battery_operating_device(zones[deviceIndex]), zones)
        battery_entities = []
        for bd in battery_devices:
            battery_device = battery_devices[bd]
            battery_entities.append(TechBatterySensor(battery_device, api, controller_udid))
        async_add_entities(battery_entities)

        async_add_entities(
            [
                ZoneTemperatureSensor(
                    zones[zone],
                    api,
                    controller_udid,
                )
                for zone in zones
            ],
            True,
        )

def is_battery_operating_device(device) -> bool:
    return device['zone']['batteryLevel'] is not None

class TechBatterySensor(SensorEntity):
    """Representation of a Tech battery sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device, api, controller_udid):
        """Initialize the Tech battery sensor."""
        _LOGGER.debug("Init TechBatterySensor... ")
        self._controller_udid = _controller_udid
        self._api = api
        self._id = device["zone"]["id"]
        self.update_properties(device)

    def update_properties(self, device):
        self._name = device["description"]["name"]
        self._attr_native_value = device["zone"]["batteryLevel"]

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return "{}_battery".format(self._id)

    @property
    def name(self):
        """Return the name of the device."""
        return "{} battery".format(self._name)

    async def async_update(self):
        """Call by the Tech device callback to update state."""
        _LOGGER.debug(
            "Updating Tech battery sensor: %s, udid: %s, id: %s",
            self._name,
            self._controller_udid,
            self._id,
        )
        device = await self._api.get_zone(self._controller_udid, self._id)
        self.update_properties(device)


class ZoneSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, device, api, controller_udid):
        """Initialize the sensor."""
        _LOGGER.debug("Init ZoneSensor...")
        self._controller_udid = controller_udid
        self._api = api
        self._id = device["zone"]["id"]
        self._model = assets.get_text(1686)
        self.update_properties(device)
        
    def update_properties(self, device):
        self._name = device["description"]["name"]
        if device["zone"]["setTemperature"] is not None:
            self._target_temperature = device["zone"]["setTemperature"] / 10
        else:
            self._target_temperature = None
        if device["zone"]["currentTemperature"] is not None:
            self._temperature = device["zone"]["currentTemperature"] / 10
        else:
            self._temperature = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Tech",
            "model": self._model
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._temperature

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    async def async_update(self):
        device = await self._api.get_zone(self._controller_udid, self.unique_id)
        self.update_properties(device)


class ZoneTemperatureSensor(ZoneSensor):
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + " Temperature"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._temperature


class TileSensor(TileEntity, Entity):
    """Representation of a TileSensor."""

    def __init__(self, device, api, controller_udid):
        """Initialize the tile sensor."""
        super().__init__(device, api, controller_udid)


class TileTemperatureSensor(TileSensor):
    def __init__(self, device, api, controller_udid):
        TileSensor.__init__(self, device, api, controller_udid)

    @property
    def device_class(self):
        return sensor.DEVICE_CLASS_TEMPERATURE

    @property
    def unit_of_measurement(self):
        return TEMP_CELSIUS

    def get_state(self, device):
        return device["params"]["value"] / 10


class TileFuelSupplySensor(TileSensor):
    def __init__(self, device, api, controller_udid):
        TileSensor.__init__(self, device, api, controller_udid)

    @property
    def device_class(self):
        return sensor.DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        return PERCENTAGE

    def get_state(self, device):
        return device["params"]["percentage"]


class TileFanSensor(TileSensor):
    def __init__(self, device, api, controller_udid):
        TileSensor.__init__(self, device, api, controller_udid)
        self._attr_icon = assets.get_icon_by_type(device["type"])

    @property
    def unit_of_measurement(self):
        return PERCENTAGE

    def get_state(self, device):
        return device["params"]["gear"]


class TileTextSensor(TileSensor):
    def __init__(self, device, api, controller_udid):
        TileSensor.__init__(self, device, api, controller_udid)
        self._name = assets.get_text(device["params"]["headerId"])
        self._attr_icon = assets.get_icon(device["params"]["iconId"])

    def get_state(self, device):
        return assets.get_text(device["params"]["statusId"])


class TileWidgetSensor(TileSensor):
    def __init__(self, device, api, controller_udid):
        TileSensor.__init__(self, device, api, controller_udid)
        self._name = assets.get_text(device["params"]["widget2"]["txtId"])

    @property
    def device_class(self):
        return sensor.DEVICE_CLASS_TEMPERATURE

    @property
    def unit_of_measurement(self):
        return TEMP_CELSIUS

    def get_state(self, device):
        return device["params"]["widget2"]["value"] / 10


class TileValveSensor(TileSensor):
    def __init__(self, device, api, controller_udid):
        TileSensor.__init__(self, device, api, controller_udid)
        self._attr_icon = assets.get_icon_by_type(device["type"])
        name = assets.get_text_by_type(device["type"])
        self._name = f"{name} {device['params']['valveNumber']}"

    @property
    def unit_of_measurement(self):
        return PERCENTAGE

    def get_state(self, device):
        return device["params"]["openingPercentage"]

# TODO: this sensor's ID assignment needs to be fixed as base on such ID
#  tech api doesn't return value and we get KeyError
#
# class TileValveTemperatureSensor(TileSensor):
#     def __init__(self, device, api, controller_udid, valve_sensor):
#         self._state_key = valve_sensor["state_key"]
#         sensor_name = assets.get_text(valve_sensor["txt_id"])
#         TileSensor.__init__(self, device, api, controller_udid)
#         self._id = f"{self._id}_{self._state_key}"
#         name = assets.get_text_by_type(device["type"])
#         self._name = f"{name} {device['params']['valveNumber']} {sensor_name}"

#     @property
#     def device_class(self):
#         return sensor.DEVICE_CLASS_TEMPERATURE

#     @property
#     def unit_of_measurement(self):
#         return TEMP_CELSIUS

#     def get_state(self, device):
#         state = device["params"][self._state_key]
#         if state > 100:
#             state = state / 10
#         return state
