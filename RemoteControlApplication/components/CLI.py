import os
import sys
import time
import paho.mqtt.client as mqtt
import json
import threading
from queue import Queue, Empty
import asyncio

class ShutDownRequest(Exception):
    pass

class CLI:

    def __init__(self, sensor_map):
        self.sensor_map = sensor_map
        self.publish_queue = Queue() # queue that allows publisher thread to communicate with main thread and publish data
        self.stop_event = threading.Event()
        self.publisher_thread = threading.Thread(target=self.mqtt_publisher_thread, args=("127.0.0.1", 1883, self.stop_event, self.publish_queue))

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

        self.CommandList()

        self.publisher_thread.start()

        try:
            while 1:
                command = await asyncio.get_event_loop().run_in_executor(None, input, "COMMAND> ")
                await self.handleCommand(command.lower())
        
        except KeyboardInterrupt:
            print("SHUTDOWN")
            self.stop_event.set()  # Imposta l'evento per fermare il thread MQTT.
            self.publisher_thread.join()  # Attendi che il thread MQTT termini.
            os._exit(0)
    
    async def handleCommand(self, command):
        if command == "configure":
            await self.configure()
        elif command == "status":
            await self.status()
        elif command == "monitor":
            await self.monitor()
        elif command == "help":
            self.help()
        elif command == "exit":
            print("Exiting...")
            self.stop_event.set()  # Imposta l'evento per fermare il thread MQTT.
            self.publisher_thread.join()  # Attendi che il thread MQTT termini.
            raise ShutDownRequest()       
            
        else:
            print("Invalid command. Type 'help' for available commands.")

    @staticmethod
    def CommandList():
        print("\n|----- AVAILABLE COMMANDS -----|")
        print("| 1. configure                 |")
        print("| 2. status                    |")
        print("| 3. monitor                   |")
        print("| 4. help                      |")
        print("| 5. exit                      |")
        print("|------------------------------|\n")
    
    async def configure(self):
        self.listOfsensors()
        await self.getsensorvalues()

    @staticmethod
    def listOfsensors():
        print("\n|----- AVAILABLE SENSORS -----|\n")
        print("| 1. temperature              |\n")
        print("| 2. pH                       |\n")
        print("| 3. salinity                 |\n")
        print("| 4. exit                     |\n")
        print("|-----------------------------|\n")
        
    async def getsensorvalues(self):
        while 1:
            sensor=await asyncio.get_event_loop().run_in_executor(None, input, "SENSOR> ")
            sensor = sensor.lower()
            if sensor == "temperature":
                sensor = "temp"
            
            if sensor in self.sensor_map.keys():
                self.listOfparameters(sensor)
                await self.getparameters(sensor)
                break
            elif sensor == "exit":
                self.CommandList()
                break
            else:
                print("Invalid sensor. Please enter a valid sensor or exit.\n")
                self.listOfsensors()
                
    @staticmethod
    def listOfparameters(sensor):
        if sensor == "temp":
            print("\n|----- AVAILABLE PARAMETERS -----|\n")
            print("| 1. max                         |\n")
            print("| 2. delta                       |\n")
            print("| 3. both                        |\n")
            print("| 4. exit                        |\n")
            print("|--------------------------------|\n")
        elif sensor == "ph":
            print("\n|----- AVAILABLE PARAMETERS -----|\n")
            print("| 1. max                         |\n")
            print("| 2. min                         |\n")
            print("| 3. both                        |\n")
            print("| 4. delta                       |\n")
            print("| 5. all                         |\n")
            print("| 6. exit                        |\n")
            print("|--------------------------------|\n")
        elif sensor == "salinity":
            print("\n|----- AVAILABLE PARAMETERS -----|\n")
            print("| 1. max                         |\n")
            print("| 2. min                         |\n")
            print("| 3. both                        |\n")
            print("| 4. delta                       |\n")
            print("| 5. all                         |\n")
            print("| 6. exit                        |\n")
            print("|--------------------------------|\n")
    
    async def getparameters(self,sensor):
        while 1:
            parameter=await asyncio.get_event_loop().run_in_executor(None, input, "PARAMETER> ")
            parameter = parameter.lower()
            if sensor == "temp" and parameter in ["min", "both", "all"]:
                print("Temperature sensor has only two parameters: max and delta. Please enter a valid parameter.\n")
                continue
            elif parameter in ["max", "min", "both", "delta", "all"]:
                await self.parametershandler(sensor, parameter)
                break
            elif parameter == "exit":
                self.CommandList()
                break
            else:
                print("Invalid parameter. Please enter a valid parameter or exit.\n")
                self.listOfparameters(sensor)

    async def parametershandler(self,sensor, parameter):
        sensor = self.sensor_map.get(sensor)
        while 1:
            if parameter == "max":
                try:
                    maxvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MAX VALUE> ")
                    maxvalue = round(float(maxvalue), 2)
                    
                    if sensor.min>maxvalue:
                        print(f"Invalid input. The maximum value {maxvalue} must be greater than the actual minimum value {sensor.min}.")
                        continue

                    sensor.max = maxvalue
                    self.publish_queue.put((f"params/{sensor.type}", {"max_value":maxvalue}))
                    break

                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            elif parameter == "min":
                try:
                    minvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MIN VALUE> ")
                    minvalue = round(float(minvalue), 2)
                    if sensor.max<minvalue:
                        print(f"Invalid input. The minimum value {minvalue} must be less than the actual maximum value {sensor.max}.")
                        continue

                    sensor.min = minvalue
                    self.publish_queue.put((f"params/{sensor.type}", {"min_value":minvalue}))
                    break

                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            elif parameter == "both":
                try:
                    maxvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MAX VALUE>: ")
                    maxvalue = round(float(maxvalue), 2)

                    if sensor.type == "temperature":
                        delta = await asyncio.get_event_loop().run_in_executor(None, input, "DELTA> ")
                        delta = round(float(delta), 2)
                    else:    
                        minvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MIN VALUE>: ")
                        minvalue = round(float(minvalue), 2)

                    if(sensor.type== "temperature" and delta>maxvalue):
                        print(f"Invalid input. The delta value {delta} must be less or equal than the maximum value for temperature sensor {maxvalue}.")
                        continue

                    if minvalue > maxvalue:
                        print(f"Invalid input. The minimum value {minvalue} must be less or equal than the maximum value {maxvalue}.")
                        continue

                    sensor.max = maxvalue
                    if(sensor.type == "temperature"):
                        sensor.delta = delta
                        self.publish_queue.put((f"params/{sensor.type}", {"max_value":maxvalue, "delta":delta}))
                    else:
                        sensor.min = minvalue
                        self.publish_queue.put((f"params/{sensor.type}", {"max_value":maxvalue, "min_value":minvalue}))
                    break

                except ValueError:
                    print("Invalid input. Please enter valid numbers.")

            elif parameter == "delta":
                try:
                    delta = await asyncio.get_event_loop().run_in_executor(None, input, "DELTA> ")
                    delta = round(float(delta), 2)

                    if(sensor.type== "temperature" and delta>sensor.max):
                        print(f"Invalid input. The delta value {delta} must be less or equal than the actual maximum value for temperature sensor {sensor.max}.")
                        continue
                    elif(delta>sensor.max-sensor.min):
                        print(f"Invalid input. The delta value {delta} must be less than {sensor.max-sensor.min}.")
                        continue

                    sensor.delta = delta
                    self.publish_queue.put((f"params/{sensor.type}", {"delta":delta}))

                    break

                except ValueError:
                    print("Invalid input. Please enter a valid number.")
                    
            elif parameter == "all":
                try:
                    maxvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MAX VALUE>: ")
                    maxvalue = round(float(maxvalue), 2)
                    minvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MIN VALUE>: ")
                    minvalue = round(float(minvalue), 2)
                    delta = await asyncio.get_event_loop().run_in_executor(None, input, "DELTA>: ")
                    delta = round(float(delta), 2)

                    if minvalue > maxvalue:
                        print(f"Invalid input. The minimum value {minvalue} must be less than the maximum value {maxvalue}.")
                        continue

                    elif(delta>maxvalue-minvalue):
                        print(f"Invalid input. The delta value {delta} must be less than {maxvalue-minvalue}.")
                        continue

                    sensor.max = maxvalue
                    sensor.min = minvalue
                    sensor.delta = delta
                    self.publish_queue.put((f"params/{sensor.type}", {"max_value":maxvalue, "min_value":minvalue, "delta":delta}))
                    break

                except ValueError:
                    print("Invalid input. Please enter valid numbers.")

    @staticmethod
    def help():
        print("\n|--------------------- COMMAND EXPLANATION ---------------------|")
        print("| 1. configure - Configure ranges for actuator activation.      |")
        print("| 2. status    - Check the actuator status.                     |")
        print("| 3. monitor   - Monitor the sensor values.                     |")
        print("| 4. help      - Display the description of available commands. |")
        print("| 5. exit      - Exit the CLI application.                      |")
        print("|---------------------------------------------------------------|\n")


    # Configurazione del client MQTT
    @staticmethod
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
