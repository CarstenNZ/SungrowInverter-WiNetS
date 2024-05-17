#!/usr/local/bin/python3
import asyncio
import logging

from sungrowinverter import SungrowInverter

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

# Change IP Address (192.168.4.2) to suit your inverter 
client = SungrowInverter("192.168.2.156")       # TODO, open client with context and pass

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
result = loop.run_until_complete(client.async_update())

#Get a list data returned from the inverter.
if result:
    print(client.data)
else:
    print("Could not connect to inverter")