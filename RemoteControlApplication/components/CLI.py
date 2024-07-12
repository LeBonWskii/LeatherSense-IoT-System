import os
import time
import paho.mqtt.client as mqtt
import json
import threading
from queue import Queue, Empty

class CLI:

    def __init__(self, sensor_map):
        self.sensor_map = sensor_map

    async def start(self):

        '''
        This method is used to start the CLI application.
        '''

        print(r'''
            _                  _    _                  ____                          
            | |     ___   __ _ | |_ | |__    ___  _ __ / ___|   ___  _ __   ___   ___ 
            | |    / _ \ / _` || __|| '_ \  / _ \| '__|\___ \  / _ \| '_ \ / __| / _ \
            | |___|  __/| (_| || |_ | | | ||  __/| |    ___) ||  __/| | | |\__ \|  __/
            |_____|\___| \__,_| \__||_| |_| \___||_|   |____/  \___||_| |_||___/ \___|
                                                                                                                                                                                    
        ''')

        CommandList()

        publish_queue = Queue() # queue that allows publisher thread to communicate with main thread and publish data
        stop_event = threading.Event()
        publisher_thread = threading.Thread(target=mqtt_publisher_thread, args=("127.0.0.1", 1883, stop_event, publish_queue))
        publisher_thread.start()

        try:
            while 1:
                command = await asyncio.get_event_loop().run_in_executor(None, input("COMMAND> "))
                await self.handleCommand(command.lower())
        
        except KeyboardInterrupt:
            print("SHUTDOWN")
            stop_event.set()  # Imposta l'evento per fermare il thread MQTT.
            publisher_thread.join()  # Attendi che il thread MQTT termini.
            os._exit(0)
    
    async def handleCommand(self, command):
        if command == "configure":
            await self.configure()
        elif command == "status":
            await self.status()
        elif command == "monitor":
            await self.monitor()
        elif command == "help":
            await self.help()
        elif command == "exit":
            print("Exiting...")
            stop_event.set()  # Imposta l'evento per fermare il thread MQTT.
            publisher_thread.join()  # Attendi che il thread MQTT termini.        
            break
        else:
            print("Invalid command. Type 'help' for available commands.")
    
    def CommandList():
        print("\n|----- AVAILABLE COMMANDS -----|")
        print("| 1. configure                 |")
        print("| 2. status                    |")
        print("| 3. monitor                   |")
        print("| 4. help                      |")
        print("| 5. exit                      |")
        print("|------------------------------|\n")
    
    def configure():
        listOfsensors()
        getsensorvalues()

    def listOfsensors():
        print("\n|----- AVAILABLE SENSORS -----|\n")
        print("| 1. temperature              |\n")
        print("| 2. pH                       |\n")
        print("| 3. salinity                 |\n")
        print("| 4. exit                     |\n")
        print("|-----------------------------|\n")
        
    def getsensorvalues():
        while 1:
            sensor=await asyncio.get_event_loop().run_in_executor(None, input("SENSOR> "))
            sensor = sensor.lower()
            
            if sensor in sensor_map.keys():
                listOfparameters(sensor)
                getparameters(sensor)
                break
            elif sensor == "exit":
                CommandList()
                break
            else:
                print("Invalid sensor. Please enter a valid sensor or exit.\n")
                listOfsensors()

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
    
    def getparameters(sensor):
        while 1:
            parameter=await asyncio.get_event_loop().run_in_executor(None, input("PARAMETER> "))
            parameter = parameter.lower()
            if sensor == "temperature" and parameter in ["min", "both"]:
                print("Temperature sensor has only one parameter: max. Please enter a valid parameter.\n")
                continue
            elif parameter in ["max", "min", "both"]:
                parametershandler(sensor, parameter)
                break
            elif parameter == "exit":
                CommandList()
                break
            else:
                print("Invalid parameter. Please enter a valid parameter or exit.\n")
                listOfparameters(sensor)

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

    def help():
        print("\n|----- COMMAND EXPLANATION -----|")
        print("| 1. configure - Configure ranges for actuator activation.")
        print("| 2. status    - Check the actuator status.")
        print("| 3. monitor   - Monitor the sensor values.")
        print("| 4. help      - Display the description of available commands.")
        print("| 5. exit      - Exit the CLI application.")
        print("|--------------------------------|\n")


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
