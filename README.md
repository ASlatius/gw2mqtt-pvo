# gw2mqtt-pvo
GoodWe inverter readout over UDP to MQTT and PVOutput.org

See the code for all the config options

## Running 
You can run this using systemd by adding the service file below in /etc/systemd/system/gw2mqtt-pvo.service

```
[Unit]
Description=Read GoodWe inverter (UDP) and publish over MQTT and to PVOutput.org

[Service]
WorkingDirectory=/path/to/script
ExecStart=/usr/bin/python3 /path/to/script/gw2mqtt-pvo/inverter_read.py
Restart=always
RestartSec=300
User=arno

[Install]
WantedBy=multi-user.target
```

## Credits
Borrowed quit a bit of code and inspiration from:  
https://github.com/markruys/gw2pvo  
https://github.com/mletenay/home-assistant-goodwe-inverter  
