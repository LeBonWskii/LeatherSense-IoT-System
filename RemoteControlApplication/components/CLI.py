import os
import sys
import time
import datetime
import paho.mqtt.client as mqtt
import json
import threading
from queue import Queue, Empty
import asyncio
import signal
from .PollingDB import PollingDB
from .models.H2SSensor import H2SSensor
from .models.TempSensor import TempSensor
from .models.PHSensor import PHSensor
from .models.SalinitySensor import SalinitySensor
from DAO.ResourceDAO import ResourceDAO

class ShutDownRequest(Exception):
    pass

class CLI:

    def __init__(self):
        self.sensor_map = {
            "H2S": H2SSensor(),
            "temperature": TempSensor(),
            "pH": PHSensor(),
            "salinity": SalinitySensor()
        }
        self.publish_queue = Queue() # queue that allows publisher thread to communicate with main thread and publish data
        self.stop_event = threading.Event()
        self.publisher_thread = threading.Thread(target=self.mqtt_publisher_thread, args=("127.0.0.1", 1883, self.stop_event, self.publish_queue))
        self.pickling_starting_time = None
        self.polling_task = None
        self.polling_db = PollingDB(self.sensor_map)


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

        self.publisher_thread.start()

        try:
            while 1:
                self.commandList()
                command = await asyncio.get_event_loop().run_in_executor(None, input, "COMMAND> ")
                await self.handleCommand(command.lower())
        except KeyboardInterrupt:
            print("\nExiting...")
            self.stop_event.set()
            self.publisher_thread.join()
            if self.pickling_starting_time is not None:
                await self.stop_pickling()
            sys.exit(0)
    
    async def handleCommand(self, command):
        if command == "configure":
            await self.configure()
        elif command == "settings":
            await self.settings()
        elif command == "start pickling" and self.pickling_starting_time is None:
            await self.start_pickling()
        elif command == "stop pickling" and self.pickling_starting_time is not None:
            await self.stop_pickling()
        elif command == "monitor":
            if self.pickling_starting_time is None:
                print("Pickling process is not started yet. Please start the pickling process first.")
                return
            asyncio.get_event_loop().add_signal_handler(signal.SIGINT, self.stop_monitor)
            await self.monitor()
            asyncio.get_event_loop().remove_signal_handler(signal.SIGINT)
        elif command == "help":
            self.help()
        elif command == "exit":
            print("Exiting...")
            self.stop_event.set()  # Imposta l'evento per fermare il thread MQTT.
            self.publisher_thread.join()  # Attendi che il thread MQTT termini.
            if self.pickling_starting_time is not None:
                await self.stop_pickling()
            raise ShutDownRequest()       
            
        else:
            print("Invalid command. Type 'help' for available commands.")

    def commandList(self):
        print("\n\n+----- AVAILABLE COMMANDS ------+")
        print("| 1. configure                  |")
        print("| 2. settings                   |")
        if self.pickling_starting_time is None:
            print("| 3. start pickling             |")
        else:
            print("| 3. stop pickling              |")
        print("| 4. monitor                    |")
        print("| 5. help                       |")
        print("| 6. exit                       |")
        print("+-------------------------------+\n")
    
    async def configure(self):
        self.listOfsensors()
        await self.getsensorvalues()

    @staticmethod
    def listOfsensors():
        print("\n+----- AVAILABLE SENSORS -----+")
        print("| 1. temperature              |")
        print("| 2. pH                       |")
        print("| 3. salinity                 |")
        print("| 4. exit                     |")
        print("+-----------------------------+\n")
        
    async def getsensorvalues(self):
        while 1:
            sensor=await asyncio.get_event_loop().run_in_executor(None, input, "SENSOR> ")

            if sensor in self.sensor_map.keys():
                self.listOfparameters(sensor)
                await self.getparameters(sensor)
                break
            elif sensor == "exit":
                self.commandList()
                break
            else:
                print("Invalid sensor. Please enter a valid sensor or exit.\n")
                self.listOfsensors()
                
    @staticmethod
    def listOfparameters(sensor):
        if sensor == "temperature":
            print("\n+----- AVAILABLE PARAMETERS -----+")
            print("| 1. max                         |")
            print("| 2. delta                       |")
            print("| 3. both                        |")
            print("| 4. exit                        |")
            print("+--------------------------------+\n")
        elif sensor == "pH":
            print("\n+----- AVAILABLE PARAMETERS -----+")
            print("| 1. min                         |")
            print("| 2. max                         |")
            print("| 3. both                        |")
            print("| 4. delta                       |")
            print("| 5. all                         |")
            print("| 6. exit                        |")
            print("+--------------------------------+\n")
        elif sensor == "salinity":
            print("\n+----- AVAILABLE PARAMETERS -----+")
            print("| 1. min                         |")
            print("| 2. max                         |")
            print("| 3. both                        |")
            print("| 4. delta                       |")
            print("| 5. all                         |")
            print("| 6. exit                        |")
            print("+--------------------------------+\n")
    
    async def getparameters(self,sensor):
        while 1:
            parameter=await asyncio.get_event_loop().run_in_executor(None, input, "PARAMETER> ")
            parameter = parameter.lower()
            if sensor == "temperature" and parameter in ["min", "all"]:
                print("Temperature sensor has only two parameters: max and delta. Please enter a valid parameter.\n")
                continue
            elif parameter in ["max", "min", "both", "delta", "all"]:

                print(f"\nActual parameters for {sensor} sensor:")
                if self.sensor_map[sensor].min is not None:
                    print(f"Min Value: {self.sensor_map[sensor].min}")
                print(f"Max Value: {self.sensor_map[sensor].max}")
                print(f"Delta: {self.sensor_map[sensor].delta}\n")

                await self.parametershandler(sensor, parameter)
                break
            elif parameter == "exit":
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
                    
                    if sensor.min is not None and sensor.min>maxvalue:
                        print(f"Invalid input. The maximum value {maxvalue} must be greater than the actual minimum value {sensor.min}.")
                        continue
                    
                    if sensor.type == "temperature" and maxvalue < 0:
                        print(f"Invalid input. The maximum value {maxvalue} for temperature sensor must be greater than 0.")
                        continue
                    
                    if sensor.type == "ph" and maxvalue > 14:
                        print(f"Invalid input. The maximum value {maxvalue} for pH sensor must be less than 14.")
                        continue

                    if sensor.type == "temperature" and maxvalue < sensor.delta:
                        print(f"Invalid input. The maximum value {maxvalue} must be greater than the actual delta value {sensor.delta} for temperature sensor.")
                        continue

                    elif sensor.type != "temperature" and maxvalue<sensor.min+sensor.delta:
                        print(f"Invalid input. The maximum value {maxvalue} must be greater than {sensor.min+sensor.delta}.")
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

                    if sensor.type == "ph" and minvalue < 0:
                        print(f"Invalid input. The minimum value {minvalue} for pH sensor must be greater than 0.")
                        continue

                    if sensor.type == "salinity" and minvalue < 0:
                        print(f"Invalid input. The minimum value {minvalue} for salinity sensor must be greater than 0.")
                        continue

                    if minvalue > sensor.max-sensor.delta:
                        print(f"Invalid input. The minimum value {minvalue} must be less than {sensor.max-sensor.delta}.")
                        continue

                    sensor.min = minvalue
                    self.publish_queue.put((f"params/{sensor.type}", {"min_value":minvalue}))
                    break

                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            elif parameter == "both":
                try:

                    if sensor.type != "temperature":
                        minvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MIN VALUE>: ")
                        minvalue = round(float(minvalue), 2)

                    if sensor.type == "ph" and minvalue < 0:
                        print(f"Invalid input. The minimum value {minvalue} must be greater than 0 for pH sensor.")
                        continue

                    if sensor.type == "salinity" and minvalue < 0:
                        print(f"Invalid input. The minimum value {minvalue} for salinity sensor must be greater than 0.")
                        continue

                    maxvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MAX VALUE>: ")
                    maxvalue = round(float(maxvalue), 2)

                    if sensor.type == "temperature" and maxvalue < 0:
                        print(f"Invalid input. The maximum value {maxvalue} for temperature sensor must be greater than 0.")
                        continue

                    if sensor.type == "ph" and maxvalue > 14:
                        print(f"Invalid input. The maximum value {maxvalue} must be less than 14 for pH sensor.")
                        continue

                    if sensor.type == "temperature":
                        delta = await asyncio.get_event_loop().run_in_executor(None, input, "DELTA> ")
                        delta = round(float(delta), 2)
                    
                    if(sensor.type == "temperature" and delta < 0):
                        print(f"Invalid input. The delta value {delta} must be greater than 0.")
                        continue
  
                    if(sensor.type == "temperature" and delta>maxvalue):
                        print(f"Invalid input. The delta value {delta} must be less or equal than the maximum value {maxvalue} for temperature sensor.")
                        continue
                    
                    elif (sensor.type != "temperature" and minvalue > maxvalue):
                        print(f"Invalid input. The minimum value {minvalue} must be less or equal than the maximum value {maxvalue}.")
                        continue

                    elif(sensor.type != "temperature" and sensor.delta>maxvalue-minvalue):
                        print(f"Invalid input. The resulting delta value {maxvalue-minvalue} must be greater than actual delta value {sensor.delta}.")
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

                    if(delta < 0):
                        print(f"Invalid input. The delta value {delta} must be greater than 0.")
                        continue

                    if(sensor.type == "temperature" and delta>sensor.max):
                        print(f"Invalid input. The delta value {delta} must be less or equal than the actual maximum value {sensor.max} for temperature sensor.")
                        continue

                    elif(sensor.type != "temperature" and delta>sensor.max-sensor.min):
                        print(f"Invalid input. The delta value {delta} must be less than {sensor.max-sensor.min}.")
                        continue

                    sensor.delta = delta
                    self.publish_queue.put((f"params/{sensor.type}", {"delta":delta}))

                    break

                except ValueError:
                    print("Invalid input. Please enter a valid number.")
                    
            elif parameter == "all":
                try:
                    minvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MIN VALUE>: ")
                    minvalue = round(float(minvalue), 2)

                    if sensor.type == "ph" and minvalue < 0:
                        print(f"Invalid input. The minimum value {minvalue} must be greater than 0 for pH sensor.")
                        continue

                    if sensor.type == "salinity" and minvalue < 0:
                        print(f"Invalid input. The minimum value {minvalue} for salinity sensor must be greater than 0.")
                        continue

                    maxvalue = await asyncio.get_event_loop().run_in_executor(None, input, "MAX VALUE>: ")
                    maxvalue = round(float(maxvalue), 2)

                    if minvalue > maxvalue:
                        print(f"Invalid input. The minimum value {minvalue} must be less than the maximum value {maxvalue}.")
                        continue

                    if sensor.type == "ph" and maxvalue > 14:
                        print(f"Invalid input. The maximum value {maxvalue} must be less than 14 for pH sensor.")
                        continue

                    delta = await asyncio.get_event_loop().run_in_executor(None, input, "DELTA>: ")
                    delta = round(float(delta), 2)

                    if(delta < 0):
                        print(f"Invalid input. The delta value {delta} must be greater than 0.")
                        continue

                    if(delta>maxvalue-minvalue):
                        print(f"Invalid input. The delta value {delta} must be less than {maxvalue-minvalue}.")
                        continue

                    sensor.max = maxvalue
                    sensor.min = minvalue
                    sensor.delta = delta
                    self.publish_queue.put((f"params/{sensor.type}", {"max_value":maxvalue, "min_value":minvalue, "delta":delta}))
                    break

                except ValueError:
                    print("Invalid input. Please enter valid numbers.")

    async def start_pickling(self):
        self.pickling_starting_time = datetime.datetime.now()

        # Initialize actuators and start polling data
        self.polling_task = asyncio.create_task(self.polling_db.start())

        # Publish start pickling message to start data sensing
        self.publish_queue.put(("pickling", {"value":"start"}))

        print("\nPickling process STARTED at ", self.pickling_starting_time)
        print("You can monitor the process by typing 'monitor'.")
    
    async def stop_pickling(self):    
        print("\nPickling process STOPPED at ", datetime.datetime.now())
        print("Pickling process age: ", datetime.datetime.now() - self.pickling_starting_time)

        # Stop polling data and turn off actuators
        if self.polling_task is not None:
            await self.polling_db.stop()
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                print("Polling task stopped.")
            self.polling_task = None

        # Publish stop pickling message to avoid useless data sensing
        self.publish_queue.put(("pickling", {"value":"stop"}))

        self.pickling_starting_time = None

    async def settings(self):
        for sensor in self.sensor_map.values():
            if sensor.type != "H2S":
                print(f"{sensor.type.upper()} SENSOR:")
                print(f"\t(Range-based sensor)")
                if sensor.min is not None:
                    print(f"\tMin Value: {sensor.min}")
                else:
                    print("\tMin Value: Not Set")
                print(f"\tMax Value: {sensor.max}")
                if sensor.delta is not None:
                    print(f"\tDelta: {sensor.delta}")
                else:
                    print("\tDelta: Not Set")
        print(f"H2S SENSOR:")
        print(f"\t(Detection-based sensor)")
        print(f"\t0 - No H2S detected")
        print(f"\t1 - H2S detected")
    
    async def monitor(self):
        print("Enter the frequency of monitoring in seconds:")
        frequency = await asyncio.get_event_loop().run_in_executor(None, input, "FREQUENCY> ")
        if not frequency.isdigit():
            frequency = 5
        else:
            frequency = int(frequency)
        print(f"Monitoring sensor values every {frequency} seconds.\nPress Ctrl+C to stop monitoring.")
        self.running = True
        try:
            while self.running:
                resource_status = {
                    "fans": await ResourceDAO.retrieve_information("fans"),
                    "pump": await ResourceDAO.retrieve_information("pump"),
                    "alarm": await ResourceDAO.retrieve_information("alarm"),
                    "locker": await ResourceDAO.retrieve_information("locker")
                }
                print("\nPickling process age: ", datetime.datetime.now() - self.pickling_starting_time)
                print("+-------------------------------+\t+-------------------------------+")
                print("| SENSOR\t| VALUE\t\t|\t| ACTUATOR\t| STATUS\t|")
                print("+---------------+---------------+\t+---------------+---------------+")
                print(f"| Temperature\t| {self.sensor_map['temperature'].value}\t\t|\t| Fans\t\t| " + (('both\t' if resource_status['fans'].status == 'both' else ('off\t' if resource_status['fans'].status == 'off' else resource_status['fans'].status)) if resource_status['fans'] is not None else 'None\t') + "\t|")
                print(f"| pH\t\t| {self.sensor_map['pH'].value}\t\t|\t| Pump\t\t| {resource_status['pump'].status if resource_status['pump'] is not None else 'None'}\t\t|")
                print(f"| Salinity\t| {self.sensor_map['salinity'].value}\t\t|\t| Alarm\t\t| {resource_status['alarm'].status if resource_status['alarm'] is not None else 'None'}\t\t|")
                print(f"| H2S\t\t| " + ('Detected\t' if self.sensor_map['H2S'].value is not None and int(self.sensor_map['H2S'].value) == 1 else ('Not detected\t' if (self.sensor_map['H2S'].value is not None) else 'None\t\t') ) + f"|\t| Locker\t| {resource_status['locker'].status if resource_status['locker'] is not None else 'None'}\t\t|")
                print("+-------------------------------+\t+-------------------------------+")
                await asyncio.sleep(frequency)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
        
    def stop_monitor(self):
        self.running = False

    @staticmethod
    def help():
        print("\n+------------------------- COMMAND EXPLANATION ---------------------------+")
        print("| 1. configure           - Configure ranges for actuator activation.      |")
        print("| 2. settings            - Check the settled ranges.                      |")
        print("| 3. start/stop pickling - Manage the pickling process.                   |")
        print("| 4. monitor             - Monitor the sensor values and actuator status. |")
        print("| 5. help                - Display the description of available commands. |")
        print("| 6. exit                - Exit the CLI application.                      |")
        print("+-------------------------------------------------------------------------+\n")

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
                    for key in data:
                        if isinstance(data[key], float):
                            data[key] = str(data[key]) #convert float values to string for correct cJSON parse
                    payload = json.dumps(data) #convert data to JSON format
                    client.publish(topic, payload, retain = True) #publish data in the topic
                except Empty:
                    continue
        finally:
            client.loop_stop()
            client.disconnect()
            print("MQTT client disconnected.")
