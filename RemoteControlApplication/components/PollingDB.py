import asyncio
import mysql.connector
from datetime import datetime
from database.models.database import Database
from DAO.ResourceDAO import ResourceDAO
from CoapClient import CoapClient
from models import PHSensor, SalinitySensor, SO2Sensor, TempSensor

class PollingDB:

    def __init__(self, types):
        self.db = Database()
        asyncio.initiate_id()
        self.types = types

    async def start(self):
        '''
        Start the polling of the database
        '''
        while True:
            await self.polling()
            await asyncio.sleep(1)
    
    async def initiate_id(self):
        '''
        Initiate the last id of the telemetry table
        '''
        try:
            cursor = self.db.connect().cursor()
            cursor.execute("SELECT MAX(id) FROM telemetry")
            result = cursor.fetchall()
            cursor.close()
            self.last_id = result[0][0]
        except mysql.connector.Error as e:
            print(f"Error: {e}")


    async def polling(self):
        '''
        Poll the database for the latest sensor values
        '''
        # Check if database connection is still active
        if not self.connection.is_connected():
            print("Database connection lost")
            return
        
        # Poll the database for the latest sensor values
        try:
            new_id = self.last_id
            cursor = self.connection.cursor()
            for sensor_type in self.types:
                query = f"SELECT value, id FROM telemetry WHERE id > {self.last_id} and type = '{sensor_type}' ORDER BY id DESC LIMIT 1"
                cursor.execute(query)
                result = cursor.fetchall()
                if result:
                    self.types[sensor_type].value = result[0][0]
                    print(f"[PoolingDB]\t{sensor_type}: {result[0][0]}")
                    if new_id < result[0][1]:
                        new_id = result[0][1]
            cursor.close()
        except mysql.connector.Error as e:
            print(f"Error: {e}")
        
        # Check values
        if new_id > self.last_id:
            self.last_id = new_id
            await self.check_values()
    
    async def check_values(self):
        '''
        Check the values of the sensors and manage the resources accordingly
        '''
        # Retrieve resource status
        resource_status = {
            "fans": ResourceDAO.retrieve_information("fans"),
            "pump": ResourceDAO.retrieve_information("pump"),
            "alarm": ResourceDAO.retrieve_information("alarm"),
            "locker": ResourceDAO.retrieve_information("locker")
        }
        
        # Manage resources
        manage_fans(resource_status["fans"])
        manage_pump(resource_status["pump"])
        manage_alarm(resource_status["alarm"])
        manage_locker(resource_status["locker"])
    
    def manage_fans(self, resource):
        '''
        Manage the fans resource
        :param resource: The current status of the fans resource
        '''
        if resource == "off":
            # If temperature is too high and SO2 is detected, turn on both fans
            if self.types["temp"].value > self.types["temp"].max and self.types["so2"].value == 1:
                CoapClient(resource_status["fans"], "both").start()
            # If temperature is too high, turn on cooling fan
            elif self.types["temp"].value > self.types["temp"].max:
                CoapClient(resource_status["fans"], "cooling").start()
            # If SO2 is detected, turn on exhaust fan
            elif self.types["so2"].value == 1:
                CoapClient(resource_status["fans"], "exhaust").start()
        
        elif resource == "cooling":
            # If temperature is optimal, turn off the fan
            if self.types["temp"].value < self.types["temp"].max - self.types["temp"].delta and self.types["so2"].value == 0:
                CoapClient(resource_status["fans"], "off").start()
            # If temperature is still high and SO2 is detected, turn on also exhaust fan
            elif self.types["temp"].value >= self.types["temp"].max - self.types["temp"].delta and self.types["so2"].value == 1:
                CoapClient(resource_status["fans"], "both").start()
            # If temperature is optimal but SO2 is detected, turn on exhaust fan
            elif self.types["temp"].value < self.types["temp"].max - self.types["temp"].delta and self.types["so2"].value == 1:
                CoapClient(resource_status["fans"], "exhaust").start()
        
        elif resource == "exhaust":
            # If SO2 is no more detected and temperature is normal, turn off the fan
            if self.types["so2"].value == 0 and self.types["temp"].value < self.types["temp"].max:
                CoapClient(resource_status["fans"], "off").start()
            # If SO2 is no more detected but temperature is too high, turn on cooling fan
            elif self.types["so2"].value == 0 and self.types["temp"].value > self.types["temp"].max:
                CoapClient(resource_status["fans"], "cooling").start()
            # If SO2 is still detected and temperature is too high, turn on both fans
            elif self.types["so2"].value == 1 and self.types["temp"].value > self.types["temp"].max:
                CoapClient(resource_status["fans"], "both").start()

    def manage_pump(self, resource):
        '''
        Manage the pump resource.
        We give priority to the pH value over the salinity value, 
        as pH can influence the overall salinity while depending on the type of salt used
        the opposite can be avoided.

        :param resource: The current status of the pump resource
        '''
        if resource == "off":
            # If pH is too low, turn on the pump to add base
            if self.types["ph"].value < self.types["ph"].min:
                CoapClient(resource_status["pump"], "base").start()
            # If pH is too high, turn on the pump to add acid
            elif self.types["ph"].value > self.types["ph"].max:
                CoapClient(resource_status["pump"], "acid").start()
            # If pH is stable but salinity is too high, turn on the pump to add pure water
            elif self.types["salinity"].value > self.types["salinity"].max:
                CoapClient(resource_status["pump"], "pure").start()
        
        elif resource == "pure":
            # If pH is to low, turn on the pump to add base
            if self.types["ph"].value < self.types["ph"].min:
                CoapClient(resource_status["pump"], "base").start()
            # If pH is too high, turn on the pump to add acid
            elif self.types["ph"].value > self.types["ph"].max:
                CoapClient(resource_status["pump"], "acid").start()
            # If pH is stable and salinity is optimal, turn off the pump
            elif self.types["salinity"].value < self.types["salinity"].max - self.types["salinity"].delta:
                CoapClient(resource_status["pump"], "off").start()
            
        elif resource == "acid":
            # If pH is too low, turn on the pump to add base
            if self.types["ph"].value < self.types["ph"].min:
                CoapClient(resource_status["pump"], "base").start()
            # If pH is optimal but salinity is too high, turn on the pump to add pure water
            elif self.types["ph"].value < self.types["ph"].max - self.types["ph"].delta \
                and self.types["salinity"].value > self.types["salinity"].max:
                CoapClient(resource_status["pump"], "pure").start()
            # If pH is optimal and salinity is not too high, turn off the pump
            elif self.types["ph"].value < self.types["ph"].max - self.types["ph"].delta \
                and self.types["salinity"].value < self.types["salinity"].max:
                CoapClient(resource_status["pump"], "off").start()
            
        elif resource == "base":
            # If pH is too high, turn on the pump to add acid
            if self.types["ph"].value > self.types["ph"].max:
                CoapClient(resource_status["pump"], "acid").start()
            # If pH is optimal but salinity is too high, turn on the pump to add pure water
            elif self.types["ph"].value > self.types["ph"].min + self.types["ph"].delta \
                and self.types["salinity"].value > self.types["salinity"].max:
                CoapClient(resource_status["pump"], "pure").start()
            # If pH is optimal and salinity is not too high, turn off the pump
            elif self.types["ph"].value > self.types["ph"].min + self.types["ph"].delta \
                and self.types["salinity"].value < self.types["salinity"].max:
                CoapClient(resource_status["pump"], "off").start()
    
    def manage_alarm(self, resource):
        '''
        Manage the alarm resource
        :param resource: The current status of the alarm resource
        '''
        if resource == "off":
            # If salinity is too low, turn on the alarm
            if self.types["salinity"].value < self.types["salinity"].min:
                CoapClient(resource_status["alarm"], "on").start()
            
        elif resource == "on":
            # If salinity is optimal, turn off the alarm
            if self.types["salinity"].value > self.types["salinity"].min + self.types["salinity"].delta:
                CoapClient(resource_status["alarm"], "off").start()
    
    def manage_locker(self, resource):
        '''
        Manage the locker resource
        :param resource: The current status of the locker resource
        '''
        if resource == "off":
            # If SO2 is detected, turn on the locker
            if self.types["so2"].value == 1:
                CoapClient(resource_status["locker"], "on").start()
        
        elif resource == "on":
            # If SO2 is no more detected, turn off the locker
            if self.types["so2"].value == 0:
                CoapClient(resource_status["locker"], "off").start()

    