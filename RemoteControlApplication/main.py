import os
import time
from database.models.database import Database
from models.observer import ObserveSensor
from mysql.connector import Error
from coapthon.client.helperclient import HelperClient
import paho.mqtt.client as mqtt
import json
import threading
from resources.sensorsClass import Sensor
from queue import Queue, Empty

temperature_sensor = Sensor("temperature",None,25)
ph_sensor = Sensor("ph",2.8,3)
salinity_sensor = Sensor("salinity",2,3)

sensor_map = {
    "temperature": temperature_sensor,
    "ph": ph_sensor,
    "salinity": salinity_sensor
}

# Configurazione del client MQTT
def mqtt_publisher_thread(broker_address, broker_port, stop_event, publish_queue):
    client = mqtt.Client()
    client.connect(broker_address, broker_port, 60)
    client.loop_start()
    try:
        while not stop_event.is_set():
            try:
                topic, data = publish_queue.get(timeout=1) #obtain data from queue, timeout needed to check if stop_event is set
                payload = json.dumps(data) #convert data to JSON format
                client.publish(topic, payload) #publish data in the topic
                print(f"Data published to {topic}: {payload}")
            except Empty:
                continue
    finally:
        client.loop_stop()
        client.disconnect()
        print("MQTT client disconnected.")

def listOfcommands():
    print("\n|----- AVAILABLE COMMANDS -----|\n")
    print("| 1. exit                        |\n")
    print("| 2. setparams                   |\n")
    print("| 3. help                        |\n")
    print("|--------------------------------|\n")

def listOfsensors():
    print("\n|----- AVAILABLE SENSORS -----|\n")
    print("| 1. temperature              |\n")
    print("| 2. pH                       |\n")
    print("| 3. salinity                 |\n")
    print("| 4. exit                     |\n")
    print("|-----------------------------|\n")

def listOfparameters(sensor):
    if sensor == "temperature":
        print("\n|----- AVAILABLE PARAMETERS -----|\n")
        print("| 1. max                         |\n")
        print("| 2. exit                        |\n")
        print("|--------------------------------|\n")
    elif sensor == "pH":
        print("\n|----- AVAILABLE PARAMETERS -----|\n")
        print("| 1. max                         |\n")
        print("| 2. min                         |\n")
        print("| 3. both                        |\n")
        print("| 4. exit                        |\n")
        print("|--------------------------------|\n")
    elif sensor == "salinity":
        print("\n|----- AVAILABLE PARAMETERS -----|\n")
        print("| 1. max                         |\n")
        print("| 2. min                         |\n")
        print("| 3. both                        |\n")
        print("| 4. exit                        |\n")
        print("|--------------------------------|\n")

def parametershandler(sensor, parameter):
    sensor = sensor_map.get(sensor)
    while 1:
        if parameter == "max":
            try:
                maxvalue = float(input("MAX VALUE>: "))
                maxvalue = round(maxvalue, 2)
                
                if not sensor.validate_value(max_value=maxvalue):
                    print(f"Invalid input. The maximum value {maxvalue} must be greater than the actual minimum value {sensor.get_min_value()}.")
                    continue

                sensor.set_parameters(max_value=maxvalue)
                publish_queue.put((f"params/{sensor.sensor_type}", {"max_value":maxvalue}))
                break

            except ValueError:
                print("Invalid input. Please enter a valid number.")

        elif parameter == "min":
            try:
                minvalue = float(input("MIN VALUE>: "))
                minvalue = round(minvalue, 2)
                if not sensor.validate_value(min_value=minvalue):
                    print(f"Invalid input. The minimum value {minvalue} must be less than the actual maximum value {sensor.get_max_value()}.")
                    continue

                sensor.set_parameters(min_value=minvalue)
                publish_queue.put((f"params/{sensor.sensor_type}", {"min_value":minvalue}))
                break

            except ValueError:
                print("Invalid input. Please enter a valid number.")

        elif parameter == "both":
            try:
                maxvalue = float(input("MAX VALUE>: "))
                maxvalue = round(maxvalue, 2)
                minvalue = float(input("MIN VALUE>: "))
                minvalue = round(minvalue, 2)   

                if minvalue > maxvalue:
                    print(f"Invalid input. The minimum value {minvalue} must be less than the maximum value {maxvalue}.")
                    continue

                sensor.set_parameters(max_value=maxvalue, min_value=minvalue)
                publish_queue.put((f"params/{sensor.sensor_type}", {"max_value":maxvalue, "min_value":minvalue}))
                break

            except ValueError:
                print("Invalid input. Please enter valid numbers.")

        


    

            
def getparameters(sensor):
    while 1:
        parameter=input("PARAMETER>: ")
        parameter = parameter.lower()
        if sensor == "temperature" and parameter in ["min", "both"]:
            print("Temperature sensor has only one parameter: max. Please enter a valid parameter.\n")
            continue
        elif parameter in ["max", "min", "both"]:
            parametershandler(sensor, parameter)
            break
        elif parameter == "exit":
            listOfcommands()
            break
        else:
            print("Invalid parameter. Please enter a valid parameter or exit.\n")
            listOfparameters(sensor)
    

def getsensorvalues():
    while 1:
        sensor=input("SENSOR>: ")
        sensor = sensor.lower()
        if sensor in sensor_map.keys():
            listOfparameters(sensor)
            getparameters(sensor)
            break
        elif sensor == "exit":
            listOfcommands()
            break
        else:
            print("Invalid sensor. Please enter a valid sensor or exit.\n")
            listOfsensors()

if __name__ == "__main__":

    print(r'''
  _                  _    _                  ____                          
 | |     ___   __ _ | |_ | |__    ___  _ __ / ___|   ___  _ __   ___   ___ 
 | |    / _ \ / _` || __|| '_ \  / _ \| '__|\___ \  / _ \| '_ \ / __| / _ \
 | |___|  __/| (_| || |_ | | | ||  __/| |    ___) ||  __/| | | |\__ \|  __/
 |_____|\___| \__,_| \__||_| |_| \___||_|   |____/  \___||_| |_||___/ \___|
                                                                                                                                                                           
''')

    listOfcommands()

    publish_queue = Queue() # queue that allows publisher thread to communicate with main thread and publish data
    stop_event = threading.Event()
    publisher_thread = threading.Thread(target=mqtt_publisher_thread, args=("127.0.0.1", 1883, stop_event, publish_queue))
    publisher_thread.start()

    try:
        while 1:
            command = input("COMMAND> ")
            command = command.lower()

            if command == "help":
                listOfcommands()
            elif command == "exit":
                print("Exiting...")
                stop_event.set()  # Imposta l'evento per fermare il thread MQTT.
                publisher_thread.join()  # Attendi che il thread MQTT termini.
                break
            elif command == "setparams":
                listOfsensors()
                getsensorvalues()
            else:
                print("Invalid command. Type 'help' for available commands.\n")

    except KeyboardInterrupt:
        print("SHUTDOWN")
        stop_event.set()  # Imposta l'evento per fermare il thread MQTT.
        publisher_thread.join()  # Attendi che il thread MQTT termini.
        os._exit(0)