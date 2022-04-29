import appdaemon.plugins.hass.hassapi as hass

#
# Hellow World App
#
# Args:
#

class HelloWorld(hass.Hass):

  def initialize(self):
    self.log("Hello from AppDaemon")

    self.log("You are now ready to run Apps!")

    self.log(f"aaa {self.get_state('sensor.blind_bed_tilt', attribute='status')}")
    # self.call_service("mqtt/publish", topic="aaa", payload="sss" )
    #  self.log(f"Wind speed:  {self.get_state('weather.home', attribute='forecast')}")
    #self.set_state('sensor.blind_bed_tilt',state="100",  attributes={"status":"wind3"})