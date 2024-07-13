import paho.mqtt.client as mqtt
import json
import datetime
from threading import Thread
import sys
import os

current_path = os.path.dirname(os.path.abspath(__file__)) 
database_path = os.path.join(current_path, "../database")  
sys.path.append(database_path)  

from models.database import Database

# Inizializza la connessione al database utilizzando la classe Database singleton
db_instance = Database()
connection = db_instance.connect()

cursor = connection.cursor()

query = "INSERT INTO telemetry (timestamp, type, value) VALUES (%s, %s, %s)"

def on_connect_temp_ph_sal(client, userdata, flags, rc): 
    print("Connected with result code " + str(rc))
    client.subscribe("sensor/temp_pH_sal")

def on_connect_so2(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("sensor/so2")

def on_message(client, userdata, msg):
    print(msg.topic + " " + msg.payload.decode("utf-8", "ignore"))
    data = json.loads(msg.payload.decode("utf-8", "ignore"))

    current_time = datetime.datetime.now()

    if msg.topic == "sensor/temp_pH_sal":
            temperature = float(data["temperature"].replace(',', '.'))
            pH = float(data["pH"].replace(',', '.'))
            salinity = float(data["salinity"].replace(',', '.'))

            cursor.execute(query, (current_time, "temperature", temperature))
            cursor.execute(query, (current_time, "pH", pH))
            cursor.execute(query, (current_time, "salinity", salinity))
    elif msg.topic == "sensor/so2":
        cursor.execute(query, (current_time, "SO2", data["so2"]))

    connection.commit()

def mqtt_client(topic):
    client = mqtt.Client()
    if topic == "sensor/temp_pH_sal":
        client.on_connect = on_connect_temp_ph_sal
    elif topic == "sensor/so2":
        client.on_connect = on_connect_so2
    client.on_message = on_message

    client.connect("127.0.0.1", 1883, 60)
    client.loop_forever()

def main():
    Thread(target=mqtt_client, args=("sensor/temp_pH_sal",)).start()
    Thread(target=mqtt_client, args=("sensor/so2",)).start()

if __name__ == "__main__":
    main()
