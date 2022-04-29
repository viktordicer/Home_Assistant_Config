import appdaemon.plugins.hass.hassapi as hass
from enum import Enum
import voluptuous as vol
import datetime 
import voluptuous_helper as vol_help

"""
Blind automation adjust all configured blinds (in the AppDaemon configuration file apps.yaml)
based on the sun elevation, sun azimuth, temperature instide and outside

Arguments:
- enable_automation         - input boolean to disable the automation
- outside_temperature       - outside temperature sensor
- wind_speed                - wind speed sensor
- wind_direction            - wind direction sensor
- max_wind_speed            - max wind speed in km/h (tilt blinds when exceeding max)
- weather                   - weather entity
- winter_max_temperature    - in winter suny day, let sun in if internal temperature is below
- mode                      - normal or wind
- blinds:                   - (required) list of blinds
  - position_id:              - (required) blind position ID
    inside_temperature      - room temperature sensor
    start_at                - do not run before this time (reflects sun azimuth)
    stop_at                 - do not run after this time (reflects sun azimuth)
    min_azimuth             - open if azimuth is smaller than
    max_azimuth             - open if azimuth is greater than

configuration example (in AppDaemon's apps.yaml):

blind_automation:
    module: blind_automation
    class: BlindAutomation
    enable_automation: input_boolean.enable_blind_automation
    outside_temperature: sensor.outside_temperature
    wind_speed: sendor.wind_speed
    wind_direction: sendor.wind_direction
    max_wind_speed: 30.0
    weather: weather.home
    mode:sensor.blind_mode

    blinds:
    - position_id: sensor.blind_child3_position
      inside_temperature: sensor.child3_temperature
      min_azimuth: 40.0
      max_azimuth: 90.0
    - position_id: sensor.blind_child1_position
      inside_temperature: sensor.child1_temperature
      min_azimuth: 40.0
      max_azimuth: 90.0
    - position_id: sensor.blind_kitchen_position
      inside_temperature: sensor.kitchen_temperature
      min_azimuth: 90.0
      max_azimuth: 190.0
    - position_id: sensor.blind_living_position
      inside_temperature: sensor.living_temperature
      min_azimuth: 90.0
      max_azimuth: 190.0
    - position_id: sensor.blind_office_position
      inside_temperature: sensor.office_temperature
      min_azimuth: 190.0
      max_azimuth: 280.0
    - position_id: sensor.blind_bed_position
      inside_temperature: sensor.bed_temperature
      min_azimuth: 190.0
      max_azimuth: 280.0
    - position_id: sensor.blind_child3_position
      inside_temperature: sensor.child3_temperature
      min_azimuth: 260.0
      max_azimuth: 310.0
"""

BLINDS = "blinds"
ENABLE_AUTOMATION = "enable_automation"
OUTSIDE_TEMPERATURE = "outside_temperature"
WIND_SPEED = "wind_speed"
WIND_DIRECTION = "wind_direction"
MAX_WIND_SPEED = "max_wind_speed"
WEATHER= "weather"
MODE = "mode"

ENTITY_ID = "entity_id"
INSIDE_TEMPERATURE = "inside_temperature"
MIN_AZIMUTH = "min_azimuth"
MAX_AZIMUTH = "max_azimuth"

DEFAULT_TILT_WIND_SPEED = 13.0 # m/s - when exceeding this value and blinds tilt = 0 => tilt blinds to 20% 
DEFAULT_MAX_WIND_SPEED = 20.0 # m/s - when exceeding this value => all blinds open 
DEFAULT_MIN_AZIMUTH = 25
DEFAULT_MAX_AZIMUTH = 200

class Mode(Enum):
  SHUT = 1
  TILT_50 = 2
  TILT_100 = 3
  OPEN = 4


class BlindAutomation(hass.Hass):
  def initialize(self):
    self.log("Starting blind automation")
    BLIND_SCHEMA = vol.Schema(
      {
        vol.Required(ENTITY_ID): vol_help.existing_entity_id(self),
        vol.Optional(INSIDE_TEMPERATURE): vol_help.existing_entity_id(self),
        vol.Optional(MIN_AZIMUTH, default=DEFAULT_MIN_AZIMUTH): float,
        vol.Optional(MAX_AZIMUTH, default=DEFAULT_MAX_AZIMUTH): float,
        vol.Optional(MODE): vol_help.existing_entity_id(self),
      }
    )
    APP_SCHEMA = vol.Schema(
      {
        vol.Required("module"): str,
        vol.Required("class"): str,
        vol.Optional(ENABLE_AUTOMATION): vol_help.existing_entity_id(self),
        vol.Optional(OUTSIDE_TEMPERATURE): vol_help.existing_entity_id(self),
        vol.Optional(WIND_SPEED): vol_help.existing_entity_id(self),
        vol.Optional(WIND_DIRECTION): vol_help.existing_entity_id(self),
        vol.Optional(MAX_WIND_SPEED, default=DEFAULT_MAX_WIND_SPEED): float,
        vol.Optional(DEFAULT_TILT_WIND_SPEED, default=13.0):float,
        vol.Optional(WEATHER): vol_help.existing_entity_id(self),
        vol.Required(BLINDS): vol.All(vol_help.ensure_list, [BLIND_SCHEMA]),
      },
      extra= vol.ALLOW_EXTRA,
    )

    try:
      config = APP_SCHEMA(self.args)
    except vol.Invalid as err:
      vol.error(f"Invalid format: {err}", level="ERROR")
      return
    self.__enable_automation = config.get(ENABLE_AUTOMATION)
    self.__outside_temperature = config.get(OUTSIDE_TEMPERATURE)
    self.__wind_speed = config.get(WIND_SPEED)
    self.__wind_direction = config.get(WIND_DIRECTION)
    self.__max_wind_speed = config.get(MAX_WIND_SPEED)
    self.__tilt_wind_speed = config.get(DEFAULT_TILT_WIND_SPEED)
    self.__weather = config.get(WEATHER)
    self.__mode = config.get(MODE)
    
    time = datetime.time(0, 0, 0)
    self.run_minutely(self.wind_calculation, time)

  def wind_calculation(self, kwargs):
    self.log("Wind calculation")
    if self.get_state(self.__enable_automation) == 'on':
      if self.sun_down:
        if self.__is_windy():
          self.send_mqtt("f-30-11011-111")
      if self.__is_extreme_windy():
        self.send_mqtt("f-100-11111-111")
          

  def __is_windy(self) -> bool:
    wind_speed = self.get_state(self.__weather, attribute='wind_speed')
    if self.__tilt_wind_speed < wind_speed <= self.__max_wind_speed:
      return True
    return False
  
  def __is_extreme_windy(self) -> bool:
    wind_speed = self.get_state(self.__weather, attribute='wind_speed')
    if wind_speed > self.__max_wind_speed:
      return True
    return False
  
  def send_mqtt(self,payload):
    self.call_service("mqtt/publish", topic="sensor.blind_all", payload=payload)