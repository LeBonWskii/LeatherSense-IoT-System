import asyncio
import mysql.connector
from datetime import datetime
from database.models.database import Database
from DAO.ResourceDAO import ResourceDAO
from CoAPClient import CoAPClient
from models import PHSensor, SalinitySensor, SO2Sensor, TempSensor

class PollingDB:

    def __init__(self, types):
        self.db = Database()
        self.connection = self.db.connect()
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
            query = '''
                SELECT MAX(id) 
                FROM telemetry;
            '''
            cursor.execute(query)
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
                query = '''
                    SELECT value, id
                    FROM telemetry
                    WHERE id > %s AND sensor_type = %s
                    ORDER BY id DESC
                    LIMIT 1;
                '''
                cursor.execute(query, (self.last_id, sensor_type))
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
        
        # Manage resources if they are connected
        if resource_status["fans"] is not None:
            await manage_fans(resource_status["fans"])
        if resource_status["pump"] is not None:
            await manage_pump(resource_status["pump"])
        if resource_status["alarm"] is not None:
            await manage_alarm(resource_status["alarm"])
        if resource_status["locker"] is not None:
            await manage_locker(resource_status["locker"])
    
    async def manage_fans(self, resource):
        '''
        Manage the fans resource
        :param resource: The current status of the fans resource
        '''
        if resource == "off":
            # If temperature is too high and SO2 is detected, turn on both fans
            if self.types["temp"].value > self.types["temp"].max and self.types["so2"].value == 1:
                await CoAPClient(resource_status["fans"], "both").run()
            # If temperature is too high, turn on cooling fan
            elif self.types["temp"].value > self.types["temp"].max:
                await CoAPClient(resource_status["fans"], "cooling").run()
            # If SO2 is detected, turn on exhaust fan
            elif self.types["so2"].value == 1:
                await CoAPClient(resource_status["fans"], "exhaust").run()
        
        elif resource == "cooling":
            # If temperature is optimal, turn off the fan
            if self.types["temp"].value < self.types["temp"].max - self.types["temp"].delta and self.types["so2"].value == 0:
                await CoAPClient(resource_status["fans"], "off").run()
            # If temperature is still high and SO2 is detected, turn on also exhaust fan
            elif self.types["temp"].value >= self.types["temp"].max - self.types["temp"].delta and self.types["so2"].value == 1:
                await CoAPClient(resource_status["fans"], "both").run()
            # If temperature is optimal but SO2 is detected, turn on exhaust fan
            elif self.types["temp"].value < self.types["temp"].max - self.types["temp"].delta and self.types["so2"].value == 1:
                await CoAPClient(resource_status["fans"], "exhaust").run()
        
        elif resource == "exhaust":
            # If SO2 is no more detected and temperature is normal, turn off the fan
            if self.types["so2"].value == 0 and self.types["temp"].value < self.types["temp"].max:
                await CoAPClient(resource_status["fans"], "off").run()
            # If SO2 is no more detected but temperature is too high, turn on cooling fan
            elif self.types["so2"].value == 0 and self.types["temp"].value > self.types["temp"].max:
                await CoAPClient(resource_status["fans"], "cooling").run()
            # If SO2 is still detected and temperature is too high, turn on both fans
            elif self.types["so2"].value == 1 and self.types["temp"].value > self.types["temp"].max:
                await CoAPClient(resource_status["fans"], "both").run()

    async def manage_pump(self, resource):
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
                await CoAPClient(resource_status["pump"], "base").run()
            # If pH is too high, turn on the pump to add acid
            elif self.types["ph"].value > self.types["ph"].max:
                await CoAPClient(resource_status["pump"], "acid").run()
            # If pH is stable but salinity is too high, turn on the pump to add pure water
            elif self.types["salinity"].value > self.types["salinity"].max:
                await CoAPClient(resource_status["pump"], "pure").run()
        
        elif resource == "pure":
            # If pH is to low, turn on the pump to add base
            if self.types["ph"].value < self.types["ph"].min:
                await CoAPClient(resource_status["pump"], "base").run()
            # If pH is too high, turn on the pump to add acid
            elif self.types["ph"].value > self.types["ph"].max:
                await CoAPClient(resource_status["pump"], "acid").run()
            # If pH is stable and salinity is optimal, turn off the pump
            elif self.types["salinity"].value < self.types["salinity"].max - self.types["salinity"].delta:
                await CoAPClient(resource_status["pump"], "off").run()
            
        elif resource == "acid":
            # If pH is too low, turn on the pump to add base
            if self.types["ph"].value < self.types["ph"].min:
                await CoAPClient(resource_status["pump"], "base").run()
            # If pH is optimal but salinity is too high, turn on the pump to add pure water
            elif self.types["ph"].value < self.types["ph"].max - self.types["ph"].delta \
                and self.types["salinity"].value > self.types["salinity"].max:
                await CoAPClient(resource_status["pump"], "pure").run()
            # If pH is optimal and salinity is not too high, turn off the pump
            elif self.types["ph"].value < self.types["ph"].max - self.types["ph"].delta \
                and self.types["salinity"].value < self.types["salinity"].max:
                await CoAPClient(resource_status["pump"], "off").run()
            
        elif resource == "base":
            # If pH is too high, turn on the pump to add acid
            if self.types["ph"].value > self.types["ph"].max:
                await CoAPClient(resource_status["pump"], "acid").run()
            # If pH is optimal but salinity is too high, turn on the pump to add pure water
            elif self.types["ph"].value > self.types["ph"].min + self.types["ph"].delta \
                and self.types["salinity"].value > self.types["salinity"].max:
                await CoAPClient(resource_status["pump"], "pure").run()
            # If pH is optimal and salinity is not too high, turn off the pump
            elif self.types["ph"].value > self.types["ph"].min + self.types["ph"].delta \
                and self.types["salinity"].value < self.types["salinity"].max:
                await CoAPClient(resource_status["pump"], "off").run()
    
    async def manage_alarm(self, resource):
        '''
        Manage the alarm resource
        :param resource: The current status of the alarm resource
        '''
        if resource == "off":
            # If salinity is too low, turn on the alarm
            if self.types["salinity"].value < self.types["salinity"].min:
                await CoAPClient(resource_status["alarm"], "on").run()
            
        elif resource == "on":
            # If salinity is optimal, turn off the alarm
            if self.types["salinity"].value > self.types["salinity"].min + self.types["salinity"].delta:
                await CoAPClient(resource_status["alarm"], "off").run()
    
    async def manage_locker(self, resource):
        '''
        Manage the locker resource
        :param resource: The current status of the locker resource
        '''
        if resource == "off":
            # If SO2 is detected, turn on the locker
            if self.types["so2"].value == 1:
                await CoAPClient(resource_status["locker"], "on").run()
        
        elif resource == "on":
            # If SO2 is no more detected, turn off the locker
            if self.types["so2"].value == 0:
                await CoAPClient(resource_status["locker"], "off").run()
    