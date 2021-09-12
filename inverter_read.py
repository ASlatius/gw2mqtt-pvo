import asyncio
import goodwe
import logging
import sys
import socket
import paho.mqtt.client as mqttClient
import time
import re
import json
import pvo_api

# Set the appropriate config
LOGLEVEL        = "INFO"

GW_IP_ADDRESS   = "192.168.1.33"
GW_FAMILY       = "DT"  # One of ET, EH, ES, EM, DT, NS, XS, BP or None to detect inverter family automatically
GW_COMM_ADDR    = None  # Usually 0xf7 for ET/EH or 0x7f for DT/D-NS/XS, or None for default value
GW_TIMEOUT      = 1
GW_RETRIES      = 3
GW_INTERVAL     = 10    # Ready every # seconds, keep below 60

MQTT_IP_ADDRESS = "mqtt.domain.lan"     # IP or hostname
MQTT_PORT       = 1883                  # TLS support?
MQTT_USERNAME   = "homedevices"
MQTT_PASSWORD   = "password"
MQTT_STATTOPIC  = "goodwe/status"

PVO_SYSTEMID    = "12345"               # From pvoutput.org
PVO_APIKEY      = "21ef99aab2e79c7380aca48ae0aafe490cc1ff70c"
PVO_INTERVAL    = 5                     # 5/10/15 minutes

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s: %(message)s",
    stream=sys.stderr,
    level=getattr(logging, LOGLEVEL, None),
)

def on_mqttConnect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT broker")
    else:
        logging.error("Unable to connect to MQTT broker")

mqClient = mqttClient.Client("Python")
mqClient.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqClient.on_connect= on_mqttConnect

pvo = pvo_api.PVOutputApi(PVO_SYSTEMID, PVO_APIKEY)
if (PVO_INTERVAL < 300):
    pvo_interval = 300
else:
    pvo_interval = round(PVO_INTERVAL / 300, 0) * 300

e_day_last = 0

while True:
    t = time.localtime()

    # keep MQTT connection
    if (mqClient.is_connected() == False):
        mqClient.connect(MQTT_IP_ADDRESS, MQTT_PORT, 60)
        mqClient.loop_start()
        while (mqClient.is_connected() == False):
            time.sleep(0.1)

    try:
        # fails when the inverter is offline at night
        inverter = asyncio.run(goodwe.connect(GW_IP_ADDRESS, GW_COMM_ADDR, GW_FAMILY, GW_TIMEOUT, GW_RETRIES))

    except Exception as inst:
        # notify offline
        logging.warning("Can't connect, asume offline :: %s", str(inst))

    else:
        # inverter read succesfully
        logging.debug("Model %s, Serial %s, Version %s", inverter.model_name, inverter.serial_number, inverter.software_version)
        response = asyncio.run(inverter.read_runtime_data())
        data = []

        # reads -1 sometimes
        if (response['ppv'] >= 0 and response['e_day'] >= 0):
            e_day_last = response['e_day']
            for sensor in inverter.sensors():
                if (sensor.id_ in response):
                    logging.debug("%s: \t\t %s = %s %s", sensor.id_, str(sensor.name), str(response[sensor.id_]), str(sensor.unit))
                    #if (response[sensor.id_] > 0):
                    mqClient.publish( ("%s/%s" % (MQTT_STATTOPIC, sensor.id_)), json.dumps({
                        "name" : sensor.name,
                        "value" : str(response[sensor.id_]),
                        "unit" : sensor.unit
                    }))

        if (t.tm_min % PVO_INTERVAL == 0) and (t.tm_sec <= GW_INTERVAL):
            # Goodwe is somewhat buggy, sometimes return 0 for total day energy. We don't want to see that in PVOutput
            if (response['e_day'] > 0):
                e_day = response['e_day']
            elif (e_day_last > 0):
                e_day = e_day_last
            else:
                e_day = 0
            logging.info("PVO update - %sW, %skWh, %sV", response['ppv'], e_day, response['vpv1']+response['vpv2'])
            pvo.add_status(response['ppv'], e_day, None, response['vpv1']+response['vpv2'])

    time.sleep(GW_INTERVAL)
