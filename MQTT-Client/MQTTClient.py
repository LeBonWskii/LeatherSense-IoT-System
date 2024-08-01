import asyncio
import paho.mqtt.client as mqtt

class MQTTClient:
    def __init__(self, broker_address: str = "127.0.0.1", broker_port: int = 1883):
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.client = None
        self.on_connect = None
        self.on_message = None

    async def connect(self):
        self.client = await asyncio.to_thread(self._connect)

    def _connect(self):
        client = mqtt.Client()
        if self.on_connect:
            client.on_connect = self._on_connect_wrapper
        if self.on_message:
            client.on_message = self.on_message
        client.connect(self.broker_address, self.broker_port)
        return client

    async def _on_connect_wrapper(self, client, userdata, flags, rc):
        await asyncio.to_thread(self.on_connect, client, userdata, flags, rc)

    def set_on_connect(self, on_connect):
        self.on_connect = on_connect

    def set_on_message(self, on_message):
        self.on_message = on_message

    async def subscribe(self, topic, qos=0):
        if self.client:
            await asyncio.to_thread(self.client.subscribe, topic, qos)

    async def publish(self, topic, payload, qos=0, retain=False):
        if self.client:
            await asyncio.to_thread(self.client.publish, topic, payload, qos, retain)

    async def loop_forever(self):
        if self.client:
            await asyncio.to_thread(self.client.loop_forever)

    async def disconnect(self):
        if self.client:
            await asyncio.to_thread(self.client.disconnect)
