import sys
import asyncio
import mysql.connector
from datetime import datetime
from DAO.ResourceDAO import ResourceDAO
from .CoAPClient import CoAPClient
from .models import PHSensor, SalinitySensor, SO2Sensor, TempSensor
sys.path.append("..")
from database.models.database import Database

class PollingDB:

    def __init__(self, types):
        self.db = Database()
        self.connection = self.db.connect()
        self.initiate_id()
        self.types = types

    async def start(self):
        '''
        Start the polling of the database
        '''
        while True:
            await self.polling()
            await asyncio.sleep(2)
    
    def initiate_id(self):
        '''
        Initiate the last id of the telemetry table
        '''
        try:
            cursor = self.connection.cursor()
            query = '''
                SELECT MAX(id) 
                FROM telemetry;
            '''
            cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()

            # If there are no data, set the last id to 0
            if result[0][0] is None:
                self.last_id = -1
            else:
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
            query = '''
                SELECT t.type, t.value, t.id
                FROM telemetry t
                JOIN (
                    SELECT type, MAX(id) AS max_id
                    FROM telemetry
                    WHERE id > %s
                    GROUP BY type
                ) AS max_table
                ON t.type = max_table.type AND t.id = max_table.max_id
                ORDER BY t.id DESC;
            '''
            cursor.execute(query, (self.last_id,))
            result = cursor.fetchall()
            cursor.close()
            self.connection.commit()
            for row in result:
                self.types[row[0]].value = row[1]
                new_id = max(new_id, row[2])
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
            "fans": await ResourceDAO.retrieve_information("fans"),
            "pump": await ResourceDAO.retrieve_information("pump"),
            "alarm": await ResourceDAO.retrieve_information("alarm"),
            "locker": await ResourceDAO.retrieve_information("locker")
        }
        # Manage resources if they are connected
        if resource_status["fans"] is not None:
            await self.manage_fans(resource_status["fans"])
        if resource_status["pump"] is not None:
            await self.manage_pump(resource_status["pump"])
        if resource_status["alarm"] is not None:
            await self.manage_alarm(resource_status["alarm"])
        if resource_status["locker"] is not None:
            await self.manage_locker(resource_status["locker"])
    
    async def manage_fans(self, resource):
        '''
        Manage the fans resource
        :param resource: The current status of the fans resource
        '''
        if resource.status == "off":
            if self.types["temperature"].value is None:
                if self.types["SO2"].value == 1:
                    await CoAPClient(resource, "exhaust").run()
                return
            if self.types["SO2"].value is None:
                if self.types["temperature"].value > self.types["temperature"].max:
                    await CoAPClient(resource, "cooling").run()
                return

            # If temperature is too high and SO2 is detected, turn on both fans
            if self.types["temperature"].value > self.types["temperature"].max and self.types["SO2"].value == 1:
                await CoAPClient(resource, "both").run()
            # If temperature is too high, turn on cooling fan
            elif self.types["temperature"].value > self.types["temperature"].max:
                await CoAPClient(resource, "cooling").run()
            # If SO2 is detected, turn on exhaust fan
            elif self.types["SO2"].value == 1:
                await CoAPClient(resource, "exhaust").run()
        
        elif resource.status == "cooling":
            if self.types["temperature"].value is None:
                if self.types["SO2"].value == 1:
                    await CoAPClient(resource, "exhaust").run()
                else:
                    await CoAPClient(resource, "off").run()
                return
            if self.types["SO2"].value is None:
                if self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta:
                    await CoAPClient(resource, "off").run()
                return

            # If temperature is optimal, turn off the fan
            if self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta and self.types["SO2"].value == 0:
                await CoAPClient(resource, "off").run()
            # If temperature is still high and SO2 is detected, turn on also exhaust fan
            elif self.types["temperature"].value >= self.types["temperature"].max - self.types["temperature"].delta and self.types["SO2"].value == 1:
                await CoAPClient(resource, "both").run()
            # If temperature is optimal but SO2 is detected, turn on exhaust fan
            elif self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta and self.types["SO2"].value == 1:
                await CoAPClient(resource, "exhaust").run()
        
        elif resource.status == "exhaust":
            if self.types["temperature"].value is None:
                if self.types["SO2"].value == 0 or self.types["SO2"].value is None:
                    await CoAPClient(resource, "off").run()
                return
            if self.types["SO2"].value is None:
                if self.types["temperature"].value > self.types["temperature"].max:
                    await CoAPClient(resource, "cooling").run()
                return

            # If SO2 is no more detected and temperature is normal, turn off the fan
            if self.types["SO2"].value == 0 and self.types["temperature"].value < self.types["temperature"].max:
                await CoAPClient(resource, "off").run()
            # If SO2 is no more detected but temperature is too high, turn on cooling fan
            elif self.types["SO2"].value == 0 and self.types["temperature"].value > self.types["temperature"].max:
                await CoAPClient(resource, "cooling").run()
            # If SO2 is still detected and temperature is too high, turn on both fans
            elif self.types["SO2"].value == 1 and self.types["temperature"].value > self.types["temperature"].max:
                await CoAPClient(resource, "both").run()

    async def manage_pump(self, resource):
        '''
        Manage the pump resource.
        We give priority to the pH value over the salinity value, 
        as pH can influence the overall salinity while depending on the type of salt used
        the opposite can be avoided.

        :param resource: The current status of the pump resource
        '''
        if resource.status == "off":
            if self.types["pH"].value is None:
                if self.types["salinity"].value is not None \
                and self.types["salinity"].value > self.types["salinity"].max:
                    await CoAPClient(resource, "pure").run()
                return
            if self.types["salinity"].value is None:
                if self.types["pH"].value < self.types["pH"].min:
                    await CoAPClient(resource, "base").run()
                elif self.types["pH"].value > self.types["pH"].max:
                    await CoAPClient(resource, "acid").run()
                return

            # If pH is too low, turn on the pump to add base
            if self.types["pH"].value < self.types["pH"].min:
                await CoAPClient(resource, "base").run()
            # If pH is too high, turn on the pump to add acid
            elif self.types["pH"].value > self.types["pH"].max:
                await CoAPClient(resource, "acid").run()
            # If pH is stable but salinity is too high, turn on the pump to add pure water
            elif self.types["salinity"].value > self.types["salinity"].max:
                await CoAPClient(resource, "pure").run()
        
        elif resource.status == "pure":
            if self.types["pH"].value is None:
                if self.types["salinity"].value is None \
                or (self.types["salinity"].value is not None \
                and self.types["salinity"].value < self.types["salinity"].max - self.types["salinity"].delta):
                    await CoAPClient(resource, "off").run()
                return
            if self.types["salinity"].value is None:
                if self.types["pH"].value < self.types["pH"].min:
                    await CoAPClient(resource, "base").run()
                elif self.types["pH"].value > self.types["pH"].max:
                    await CoAPClient(resource, "acid").run()
                return

            # If pH is to low, turn on the pump to add base
            if self.types["pH"].value < self.types["pH"].min:
                await CoAPClient(resource, "base").run()
            # If pH is too high, turn on the pump to add acid
            elif self.types["pH"].value > self.types["pH"].max:
                await CoAPClient(resource, "acid").run()
            # If pH is stable and salinity is optimal, turn off the pump
            elif self.types["salinity"].value < self.types["salinity"].max - self.types["salinity"].delta:
                await CoAPClient(resource, "off").run()
            
        elif resource.status == "acid":
            if self.types["pH"].value is None:
                if self.types["salinity"].value is None \
                or (self.types["salinity"].value is not None \
                and self.types["salinity"].value < self.types["salinity"].max):
                    await CoAPClient(resource, "off").run()
                return
            if self.types["salinity"].value is None:
                if self.types["pH"].value < self.types["pH"].min:
                    await CoAPClient(resource, "base").run()
                elif self.types["pH"].value < self.types["pH"].max - self.types["pH"].delta:
                    await CoAPClient(resource, "off").run()
                return

            # If pH is too low, turn on the pump to add base
            if self.types["pH"].value < self.types["pH"].min:
                await CoAPClient(resource, "base").run()
            # If pH is optimal but salinity is too high, turn on the pump to add pure water
            elif self.types["pH"].value < self.types["pH"].max - self.types["pH"].delta \
                and self.types["salinity"].value > self.types["salinity"].max:
                await CoAPClient(resource, "pure").run()
            # If pH is optimal and salinity is not too high, turn off the pump
            elif self.types["pH"].value < self.types["pH"].max - self.types["pH"].delta \
                and self.types["salinity"].value < self.types["salinity"].max:
                await CoAPClient(resource, "off").run()
            
        elif resource.status == "base":
            if self.types["pH"].value is None:
                if self.types["salinity"].value is None \
                or (self.types["salinity"].value is not None \
                and self.types["salinity"].value < self.types["salinity"].max):
                    await CoAPClient(resource, "off").run()
                return
            if self.types["salinity"].value is None:
                if self.types["pH"].value > self.types["pH"].max:
                    await CoAPClient(resource, "acid").run()
                elif self.types["pH"].value < self.types["pH"].min + self.types["pH"].delta:
                    await CoAPClient(resource, "off").run()
                return

            # If pH is too high, turn on the pump to add acid
            if self.types["pH"].value > self.types["pH"].max:
                await CoAPClient(resource, "acid").run()
            # If pH is optimal but salinity is too high, turn on the pump to add pure water
            elif self.types["pH"].value > self.types["pH"].min + self.types["pH"].delta \
                and self.types["salinity"].value > self.types["salinity"].max:
                await CoAPClient(resource, "pure").run()
            # If pH is optimal and salinity is not too high, turn off the pump
            elif self.types["pH"].value > self.types["pH"].min + self.types["pH"].delta \
                and self.types["salinity"].value < self.types["salinity"].max:
                await CoAPClient(resource, "off").run()
    
    async def manage_alarm(self, resource):
        '''
        Manage the alarm resource
        :param resource: The current status of the alarm resource
        '''
        if resource.status == "off":
            if self.types["salinity"].value is None:
                return

            # If salinity is too low, turn on the alarm
            if self.types["salinity"].value < self.types["salinity"].min:
                await CoAPClient(resource, "on").run()
            
        elif resource.status == "on":
            if self.types["salinity"].value is None:
                await CoAPClient(resource, "off").run()
                return
            
            # If salinity is optimal, turn off the alarm
            if self.types["salinity"].value > self.types["salinity"].min + self.types["salinity"].delta:
                await CoAPClient(resource, "off").run()
    
    async def manage_locker(self, resource):
        '''
        Manage the locker resource
        :param resource: The current status of the locker resource
        '''
        if resource.status == "off":
            if self.types["SO2"].value is None:
                return

            # If SO2 is detected, turn on the locker
            if int(self.types["SO2"].value) == 1:
                await CoAPClient(resource, "on").run()
        
        elif resource.status == "on":
            if self.types["SO2"].value is None:
                await CoAPClient(resource, "off").run()
                return

            # If SO2 is no more detected, turn off the locker
            if int(self.types["SO2"].value) == 0:
                await CoAPClient(resource, "off").run()
    