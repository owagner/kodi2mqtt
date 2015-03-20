#
# Bridge between a Kodi instanc and MQTT.
#
# Written and (C) 2015 by Oliver Wagner <owagner@tellerulam.com>
# Provided under the terms of the MIT license
#
# Requires:
# - Eclipse Paho for Python - http://www.eclipse.org/paho/clients/python/
#

import argparse
import logging
import logging.handlers
import time
import json
import socket
import paho.mqtt.client as mqtt

version="0.1"

hostname=socket.gethostname()

parser = argparse.ArgumentParser(description='Bridge between Kodi and MQTT')
parser.add_argument('--mqtt-host', default='localhost', help='MQTT server address. Defaults to "localhost"')
parser.add_argument('--mqtt-port', default='1883', type=int, help='MQTT server port. Defaults to 1883')
parser.add_argument('--mqtt-topic', default="kodi/"+hostname+"/", help='Topic prefix to be used for subscribing/publishing. Defaults to "kodi/<hostname>/"')
parser.add_argument('--log', help='set log level to the specified value. Defaults to WARNING. Try DEBUG for maximum detail')
parser.add_argument('--syslog', action='store_true', help='enable logging to syslog')
args=parser.parse_args()

if args.log:
    logging.getLogger().setLevel(args.log)
if args.syslog:
    logging.getLogger().addHandler(logging.handlers.SysLogHandler())

topic=args.mqtt_topic
if not topic.endswith("/"):
    topic+="/"

logging.info('Starting kodi2mqtt V%s with topic prefix \"%s\"' %(version, topic))

def processnotify(data):
    try:
        params=json.loads(data)
    except ValueError:
        parts=data.split(None,2)
        params={"title":parts[0],"message":parts[1]}
    sendrpc("GUI.ShowNotification",params,1)

def processcommand(topic,data):
    if topic=="notify":
        processnotify(data)
    else:
        logging.warning("Unknown command "+topic)

def msghandler(mqc,userdata,msg):
    try:
        global topic
        if msg.retain:
            return
        mytopic=msg.topic[len(topic):]
        if mytopic.startswith("command/"):
            processcommand(mytopic[8:],msg.payload)
    except Exception as e:
        logging.warning("Error processing message %s: %s" % (type(e).__name__,e))

def connecthandler(mqc,userdata,rc):
    logging.info("Connected to MQTT broker with rc=%d" % (rc))
    mqc.subscribe(topic+"command/#",qos=0)

def disconnecthandler(mqc,userdata,rc):
    logging.warning("Disconnected from MQTT broker with rc=%d" % (rc))
    time.sleep(5)
    mqc.reconnect()

def publish(suffix,val,more):
    global topic,mqc
    robj={}
    robj["val"]=val
    if more is not None:
        robj.update(more)
    mqc.publish(topic+"status/"+suffix,json.dumps(robj),qos=0,retain=True)

def sendrpc(method,params,id):
    jso={"jsonrpc":"2.0","method":method,"params":params,"id":id}
    txt=json.dumps(jso)
    logging.debug("KODI>>"+txt)
    s.sendall(txt+"\n")

def requeststreamdetails():
    sendrpc("Player.GetItem",{"playerid":activeplayerid,"properties":["title","streamdetails","file"]},3)
    
def requestplaystate():
    sendrpc("Player.GetProperties",{"playerid":activeplayerid,"properties":["speed","currentsubtitle","currentaudiostream","repeat","subtitleenabled"]},5)
    
def requesttime():
    sendrpc("Player.GetProperties",{"playerid":activeplayerid,"properties":["percentage","time","totaltime"]},4)
    
def requestping():
    sendrpc("JSONRPC.Ping",{},1)
    
mqc=mqtt.Client()
mqc.on_message=msghandler
mqc.on_connect=connecthandler
mqc.on_disconnect=disconnecthandler
mqc.will_set(topic+"connected",0,qos=2,retain=True)
mqc.connect(args.mqtt_host,args.mqtt_port,60)
mqc.publish(topic+"connected",1,qos=1,retain=True)

mqc.loop_start()

s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("localhost",9090))
s.settimeout(30)
sendrpc("JSONRPC.SetConfiguration",{ "notifications": { "player": True }},1)
sendrpc("Player.GetActivePlayers",{},2)
mqc.publish(topic+"connected",2,qos=1,retain=True)

activeplayerid=-1
playstate=0

def handleplay(jso):
    global activeplayerid
    activeplayerid=jso["params"]["data"]["player"]["playerid"]
    requeststreamdetails()
    requesttime()

def convtime(timejso):
    return("%02d:%02d:%02d" % (timejso["hours"],timejso["minutes"],timejso["seconds"])) 

def setplaystate(newplaystate):
    playstate=newplaystate
    publish("playstate",playstate,None)

def handleplaystate(jso):
    if not "error" in jso["result"]:
        publish("playstate",1 if jso["result"]["speed"]>0 else 2,{"kodi_playbackdetails":jso["result"]})
    else:
        publish("playstate","0")
    
def handleresponse(jso):
    if jso["id"]==2:
        if len(jso["result"])>0:
            global activeplayerid
            activeplayerid=jso["result"][0]["playerid"]
            requeststreamdetails()
            requesttime()
            requestplaystate()
    elif jso["id"]==3:
        publish("title",jso["result"]["item"]["title"],{"kodi_details":jso["result"]["item"]})
    elif jso["id"]==4:
        if not "error" in jso["result"]:
            publish("progress",round(jso["result"]["percentage"],1),{"kodi_time":convtime(jso["result"]["time"]),"kodi_totaltime":convtime(jso["result"]["totaltime"])})
    elif jso["id"]==5:
         handleplaystate(jso)
         
fh=s.makefile("r",16384)
while True:
    bc=0
    l=bytes()
    while True:
        try:
            ch=s.recv(1)
        except socket.timeout:
            if activeplayerid>=0:
                requesttime()
            else:
                requestping()
            continue
        l+=ch
        if ch=="{":
            bc+=1
        elif ch=="}":
            bc-=1
            if bc==0:
                break;
    jso=json.loads(l.decode("UTF-8"))
    logging.debug("KODI<<%s",jso)
    if "method" in jso:
        if(jso["method"]=="Player.OnPlay"):
            handleplay(jso)
            requestplaystate()
        elif(jso["method"]=="Player.OnPause"):
            requestplaystate()
        elif(jso["method"]=="Player.OnStop"):
            requestplaystate()
    else:
        handleresponse(jso)
