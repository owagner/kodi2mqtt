#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc,xbmcaddon
import json
from lib import client as mqtt

__addon__      = xbmcaddon.Addon()
__version__    = __addon__.getAddonInfo('version')

def publish(suffix,val,more):
    global topic,mqc
    robj={}
    robj["val"]=val
    if more is not None:
        robj.update(more)
    jsonstr=json.dumps(robj)
    fulltopic=topic+"status/"+suffix
    xbmc.log("MQTT: Publishing @"+fulltopic+": "+jsonstr)
    mqc.publish(fulltopic,jsonstr,qos=0,retain=True)

def setplaystate(state):
    publish("playbackstate",state,None)
    
def publishdetails():
    global player
    if not player.isPlayer():
        return
    state={}
    state["file"]=player.getPlayingFile()
    if player.isPlayingVideo():
        it=player.getVideoInfoTag()
        title=it.getTitle()
        state["file"]=it.getFile()
    elif player.isPlayingAudio():
        it=player.getMusicInfoTag()
        title=it.getTitle()
        state["file"]=it.getFile()
    publish("title",title,{"kodi_details":state})

class MQTTMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        global mqc
        xbmc.log("MQTT: Settings changed, reconnecting broker")
        mqc.loop_stop(True)
        startmqtt()

class MQTTPlayer(xbmc.Player):
    def onPlayBackStarted(self):
        setplaystate(1)

    def onPlayBackPaused(self):
        setplaystate(2)

    def onPlayBackResumed(self):
        setplaystate(1)

    def onPlayBackEnded(self):
        setplaystate(0)
        
    def onPlayBackStopped(self):
        setplaystate(0)
        
def msghandler(mqc,userdata,msg):
    try:
        global topic
        if msg.retain:
            return
        mytopic=msg.topic[len(topic):]
        if mytopic.startswith("command/"):
            processcommand(mytopic[8:],msg.payload)
    except Exception as e:
        xbmc.log("MQTT: Error processing message %s: %s" % (type(e).__name__,e))

def connecthandler(mqc,userdata,rc):
    xbmc.log("MQTT: Connected to MQTT broker with rc=%d" % (rc))
    mqc.subscribe(topic+"command/#",qos=0)

def disconnecthandler(mqc,userdata,rc):
    xbmc.log("MQTT: Disconnected from MQTT broker with rc=%d" % (rc))
    time.sleep(5)
    mqc.reconnect()

def startmqtt():
    global topic,mqc
    mqc=mqtt.Client()
    mqc.on_message=msghandler
    mqc.on_connect=connecthandler
    mqc.on_disconnect=disconnecthandler
    topic=__addon__.getSetting("mqtttopic")
    if not topic.endswith("/"):
        topic+="/"
    mqc.will_set(topic+"connected",0,qos=2,retain=True)
    xbmc.log("MQTT: Connecting to MQTT broker at %s:%s" % (__addon__.getSetting("mqtthost"),__addon__.getSetting("mqttport")))
    mqc.connect(__addon__.getSetting("mqtthost"),__addon__.getSetting("mqttport"),60)
    mqc.publish(topic+"connected",2,qos=1,retain=True)
    mqc.loop_start()

if (__name__ == "__main__"):
    global monitor,player
    xbmc.log('MQTT: MQTT Adapter Version %s started' % __version__)
    monitor=MQTTMonitor()
    player=MQTTPlayer()
    startmqtt()
    monitor.waitForAbort()
    mqc.loop_stop(True)
    