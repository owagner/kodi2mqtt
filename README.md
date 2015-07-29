MQTT addon for Kodi
===================

  Written and (C) 2015 Oliver Wagner <owagner@tellerulam.com> 
  
  Provided under the terms of the MIT license.


Overview
--------
This is a Kodi addon which acts as an adapter between a Kodi media center instance and MQTT. 
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


Settings
--------
The addon has three settings:

* the MQTT broker's host name or IP address (defaults to 127.0.0.1)
* the MQTT broker's port. This defaults to 1883, which is the MQTT standard port for unencrypted connections.
* the topic prefix which to use in all published and subscribed topics. Defaults to "kodi/".


Topics
------
The addon publishes on the following topics (prefixed with the configured topic prefix):

* connected: 2 if the addon is currently connected to the broker, 0 otherwise. This topic is set to 0 with a MQTT will.
* status/playbackstate: a JSON-encoded object with the fields
  - "val" for the current playback state with 0=stopped, 1=playing, 2=paused
  - "kodi_playbackdetails": an object with further details about the playback state. This is effectivly the result
    of the JSON-RPC call Player.GetItem with the properties "speed", "currentsubtitle", "currentaudiostream", "repeat"
    and "subtitleenabled"
  - "kodi_playerid": the ID of the active player
  - "kodi_playertype": the type of the active player (e.g. "video")
* status/progress: a JSON-encoded object with the fields
  - "val" is the percentage of progress in playing back the current item
  - "kodi_time": the playback position in the current item
  - "kodi_totaltime": the total length of the current item
* status/title: a JSON-encoded object with the fields
  - "val": the title of the current playback item
  - "kodi_details": an object with further details about the current playback items. This is effectivly the result
    of a JSON-RPC call Player.GetItem with the properties "title", "streamdetails" and "file"

The addon listens to the following topics (prefixed with the configured topic prefix):

* command/notify: Either a simple string, or a JSON encoded object with the fields "message" and "title". Shows 
  a popup notification in Kodi
* command/play: Either a simple string which is a filename or URL, or a JSON encoded object which  correspondents
  to the Player.Open() JSON_RPC call
* command/playbackstate: A simple string or numeric with the values:
  - "0" or "stop" to stop playback
  - "1" or "resume" to resume playback (when paused)
  - "2" or "pause" to stop playback (when playing)
  - "next" to play the next track
  - "previous" to play the previous track


See also
--------
- JSON-RPC API v6 in Kodi: http://kodi.wiki/view/JSON-RPC_API/v6
- Project overview: https://github.com/mqtt-smarthome
  
  
Changelog
---------
Please see service.mqtt/changelog.txt for the change log
  