kodi2mqtt
=========

  Written and (C) 2015 Oliver Wagner <owagner@tellerulam.com> 
  
  Provided under the terms of the MIT license.


Overview
--------
kodi2mqtt is a Kodi addon which acts as an adapter between a Kodi media center instance and MQTT. 
It publishes Kodi's playback state on MQTT topics, and provides remote control capability via 
messages to MQTT topics.

It's intended as a building block in heterogenous smart home environments where an MQTT message broker is used as the centralized message bus.
See https://github.com/mqtt-smarthome for a rationale and architectural overview.


Dependencies
------------
* Kodi 14 Helix (or newer)
* Eclipse Paho for Python - http://www.eclipse.org/paho/clients/python/
  (used for MQTT communication)

  
See also
--------
- Project overview: https://github.com/mqtt-smarthome
  
  
Changelog
---------
Please see kodi2mqtt-addon/changelog.txt for the change log
  