kodi2mqtt
=========

  Written and (C) 2015 Oliver Wagner <owagner@tellerulam.com> 
  
  Provided under the terms of the MIT license.


Overview
--------
kodi2mqtt is a Kodi addon which acts as an adapter between a Kodi media center instance and MQTT. 
It publishes Kodi's playback state on MQTT topics, and provides remote control capability also via 
messages to MQTT topics.

It's intended as a building block in heterogenous smart home environments where an MQTT message broker is used as the centralized message bus.
See https://github.com/mqtt-smarthome for a rationale and architectural overview.


Dependencies
------------
* Kodi 14 Helix (or newer)
* Eclipse Paho for Python - http://www.eclipse.org/paho/clients/python/
  (used for MQTT communication)

[![Build Status](https://travis-ci.org/owagner/kodi2mqtt.svg)](https://travis-ci.org/owagner/kodi2mqtt) Automatically built addons can be downloaded from the release page on GitHub at https://github.com/owagner/kodi2mqtt/releases


Topics
------
The addon publishes on the following topics:

* connected: 2 if the addon is currently connected to the broker, 0 otherwise. This topic is set to 0 with a MQTT will.
* status/playbackstate: a JSON-encoded object with the fields
  - "val" for the current playback state with 0=stopped, 1=playing, 2=paused
  - "kodi_playbackdetails": an object with further details about the playback state. This is effectivly the result
    of the JSON-RPC call Player.GetItem with the properties "speed", "currentsubtitle", "currentaudiostream", "repeat"
    and "subtitleenabled"
* status/progress: a JSON-encoded object with the fields
  - "val" is the percentage of progress in playing back the current item
  - "kodi_time": the playback position in the current item
  - "kodi_totaltime": the total length of the current item
* status/title: a JSON-encoded object with the fields
  - "val": the title of the current playback item
  - "kodi_details": an object with further details about the current playback items. This is effectivly the result
    of a JSON-RPC call Player.GetItem with the properties "title", "streamdetails" and "file"
    
  
See also
--------
- Project overview: https://github.com/mqtt-smarthome
  
  
Changelog
---------
Please see service.mqtt/changelog.txt for the change log
  