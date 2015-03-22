#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc,xbmcaddon
import json
import threading
import time
from lib import client as mqtt

__addon__      = xbmcaddon.Addon()
__version__    = __addon__.getAddonInfo('version')

activeplayerid=-1

def sendrpc(method,params):
    res=xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}))
    xbmc.log("MQTT: JSON-RPC call "+method+" returned "+res)
    return json.loads(res)

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

def setplaystate(state,detail):
    global activeplayerid
    if state==1:
        res=sendrpc("Player.GetActivePlayers",{})
        activeplayerid=res["result"][0]["playerid"]        
        res=sendrpc("Player.GetProperties",{"playerid":activeplayerid,"properties":["speed","currentsubtitle","currentaudiostream","repeat","subtitleenabled"]})
        publish("playbackstate",state,{"kodi_state":detail,"kodi_playbackdetails":res["result"]})
        publishdetails()
    else:
        publish("playbackstate",state,{"kodi_state":detail})

def convtime(ts):
    return("%02d:%02d:%02d" % (ts/3600,(ts/60)%60,ts%60))
    
def publishprogress():
    global player
    if not player.isPlaying():
        return
    pt=player.getTime()
    tt=player.getTotalTime()
    if pt<0:
        pt=0
    progress=(pt*100)/tt
    state={"kodi_time":convtime(pt),"kodi_totaltime":convtime(tt)}
    publish("progress",round(progress,1),state)

def reportprogress():
    global monitor
    while not monitor.waitForAbort(30):
        publishprogress()

def publishdetails():
    global player,activeplayerid
    if not player.isPlaying():
        return
    res=sendrpc("Player.GetItem",{"playerid":activeplayerid,"properties":["title","streamdetails","file"]})
    publish("title",res["result"]["item"]["title"],{"kodi_details":res["result"]["item"]})
    publishprogress()

class MQTTMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        global mqc
        xbmc.log("MQTT: Settings changed, reconnecting broker")
        mqc.loop_stop(True)
        startmqtt()

class MQTTPlayer(xbmc.Player):
    def onPlayBackStarted(self):
        setplaystate(1,"started")

    def onPlayBackPaused(self):
        setplaystate(2,"paused")

    def onPlayBackResumed(self):
        setplaystate(1,"resumed")

    def onPlayBackEnded(self):
        setplaystate(0,"ended")
        
    def onPlayBackStopped(self):
        setplaystate(0,"stopped")
        
    def onPlayBackSeek(self):
        publishprogress()
        
    def onPlayBackSeek(self):
        publishprogress()
        
    def onPlayBackSeekChapter(self):
        publishprogress()
    
    def onPlayBackSpeedChanged(speed):
        setplaystate(1,"speed")
        
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
    progressthread=threading.Thread(target=reportprogress)
    progressthread.start()
    startmqtt()
    monitor.waitForAbort()
    mqc.loop_stop(True)
    