import asyncio
from MQTTClient import MQTTClient

async def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    await client.subscribe("sensor/temp_pH_sal")
    await client.subscribe("sensor/h2s")

async def on_message(client, userdata, msg):
    print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")

async def main():
    mqtt_client = MQTTClient()

    mqtt_client.set_on_connect(on_connect)
    mqtt_client.set_on_message(on_message)

    await mqtt_client.connect()

    # Keep the client running
    await mqtt_client.loop_forever()

if __name__ == "__main__":
    asyncio.run(main())
