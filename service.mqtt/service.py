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
activeplayertype=""
lasttitle=""
lastdetail={}

def sendrpc(method,params):
    res=xbmc.executeJSONRPC(json.dumps({"jsonrpc":"2.0","method":method,"params":params,"id":1}))
    xbmc.log("MQTT: JSON-RPC call "+method+" returned "+res)
    return json.loads(res)

#
# Publishes a MQTT message. The topic is built from the configured
# topic prefix and the suffix. The message itself is JSON encoded,
# with the "val" field set, and possibly more fields merged in.
#
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

#
# Set and publishes the playback state. Publishes more info if
# the state is "playing"
#
def setplaystate(state,detail):
    global activeplayerid,activeplayertype
    if state==1:
        res=sendrpc("Player.GetActivePlayers",{})
        activeplayerid=res["result"][0]["playerid"]        
        activeplayertype=res["result"][0]["type"]
        res=sendrpc("Player.GetProperties",{"playerid":activeplayerid,"properties":["speed","currentsubtitle","currentaudiostream","repeat","subtitleenabled"]})
        publish("playbackstate",state,{"kodi_state":detail,"kodi_playbackdetails":res["result"],"kodi_playerid":activeplayerid,"kodi_playertype":activeplayertype})
        publishdetails()
    else:
        publish("playbackstate",state,{"kodi_state":detail,"kodi_playerid":activeplayerid,"kodi_playertype":activeplayertype})

def convtime(ts):
    return("%02d:%02d:%02d" % (ts/3600,(ts/60)%60,ts%60))

#
# Publishes playback progress
#
def publishprogress():
    global player
    if not player.isPlaying():
        return
    pt=player.getTime()
    tt=player.getTotalTime()
    if pt<0:
        pt=0
    if tt>0:
        progress=(pt*100)/tt
    else:
        progress=0
    state={"kodi_time":convtime(pt),"kodi_totaltime":convtime(tt)}
    publish("progress",round(progress,1),state)

#
# Publish more details about the currently playing item
#
def publishdetails():
    global player,activeplayerid
    global lasttitle,lastdetail
    if not player.isPlaying():
        return
    res=sendrpc("Player.GetItem",{"playerid":activeplayerid,"properties":["title","streamdetails","file","thumbnail","fanart"]})
    if "result" in res:
        newtitle=res["result"]["item"]["title"]
        newdetail={"kodi_details":res["result"]["item"]}
        if newtitle!=lasttitle or newdetail!=lastdetail:
            lasttitle=newtitle
            lastdetail=newdetail
            publish("title",newtitle,newdetail)
    publishprogress()

#
# Notification subclasses
#
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
        
    def onQueueNextItem():
        xbmc.log("MQTT onqn");

#
# Handles commands
#
def processnotify(data):
    try:
        params=json.loads(data)
    except ValueError:
        parts = data.split(None, 1)
        params={"title":parts[0],"message":parts[1]}
    sendrpc("GUI.ShowNotification",params)

def processplay(data):
    try:
        params=json.loads(data)
        sendrpc("Player.Open",params)
    except ValueError:
        player.play(data)

def processplaybackstate(data):
    if data=="0" or data=="stop":
        player.stop()
    elif data=="1" or data=="resume":
        if not player.isPlaying():
            player.pause()
    elif data=="2" or data=="pause":
        if player.isPlaying():
            player.pause()
    elif data=="next":
        player.playnext()
    elif data=="previous":
        player.playprevious()        

def processcommand(topic,data):
    if topic=="notify":
        processnotify(data)
    elif topic=="play":
        processplay(data)
    elif topic=="playbackstate":
        processplaybackstate(data)
    else:
        xbmc.log("MQTT: Unknown command "+topic)

#
# Handles incoming MQTT messages
#
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

#
# Starts connection to the MQTT broker, sets the will
# and subscribes to the command topic
#
def startmqtt():
    global topic,mqc
    mqc=mqtt.Client()
    mqc.on_message=msghandler
    mqc.on_connect=connecthandler
    mqc.on_disconnect=disconnecthandler
    if __addon__.getSetting("mqttanonymousconnection")=='false':
        mqc.username_pw_set(__addon__.getSetting("mqttusername"), __addon__.getSetting("mqttpassword"))
    topic=__addon__.getSetting("mqtttopic")
    if not topic.endswith("/"):
        topic+="/"
    mqc.will_set(topic+"connected",0,qos=2,retain=True)
    xbmc.log("MQTT: Connecting to MQTT broker at %s:%s" % (__addon__.getSetting("mqtthost"),__addon__.getSetting("mqttport")))
    mqc.connect(__addon__.getSetting("mqtthost"),__addon__.getSetting("mqttport"),60)
    mqc.publish(topic+"connected",2,qos=1,retain=True)
    mqc.loop_start()

#
# Addon initialization and shutdown
#
if (__name__ == "__main__"):
    global monitor,player
    xbmc.log('MQTT: MQTT Adapter Version %s started' % __version__)
    monitor=MQTTMonitor()
    player=MQTTPlayer()
    startmqtt()
    while not monitor.waitForAbort(20):
        publishdetails()
    mqc.loop_stop(True)
    
