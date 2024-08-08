import sys
import asyncio
import mysql.connector
from datetime import datetime
from DAO.ResourceDAO import ResourceDAO
from .CoAPClient import CoAPClient
from .models import PHSensor, SalinitySensor, H2SSensor, TempSensor
sys.path.append("..")
from database.models.database import Database

class PollingDB:

    def __init__(self, types):
        self.db = Database()
        self.connection = self.db.connect()
        self.types = types
        self.running = False
        self.stopping = False

    async def start(self):
        '''
        Start the polling of the database
        '''
        self.initiate_id()
        self.initialize_sensors()
        await self.initialize_actuators()
        self.running = True
        self.stopping = False
        while self.running:
            await self.polling()
            await asyncio.sleep(1)
    
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

    def initialize_sensors(self):
        '''
        Initialize the sensors
        '''
        self.types["temperature"].value = None
        self.types["pH"].value = None
        self.types["salinity"].value = None
        self.types["H2S"].value = None
    
    async def initialize_actuators(self):
        '''
        Initialize the actuators
        '''
        # Retrieve resource status
        resource_status = {
            "fans": await ResourceDAO.retrieve_information("fans"),
            "pump": await ResourceDAO.retrieve_information("pump"),
            "alarm": await ResourceDAO.retrieve_information("alarm"),
            "locker": await ResourceDAO.retrieve_information("locker")
        }
        # Initialize actuators if they are connected
        if resource_status["fans"] is not None:
            await CoAPClient(resource_status["fans"], "off").run()
        if resource_status["pump"] is not None:
            await CoAPClient(resource_status["pump"], "off").run()
        if resource_status["alarm"] is not None:
            await CoAPClient(resource_status["alarm"], "off").run()
        if resource_status["locker"] is not None:
            await CoAPClient(resource_status["locker"], "off").run()
        
    async def stop(self):
        '''
        Stop the polling of the database and turn off all actuators
        '''
        self.stopping = True

        # Retrieve resource status
        resource_status = {
            "fans": await ResourceDAO.retrieve_information("fans"),
            "pump": await ResourceDAO.retrieve_information("pump"),
            "alarm": await ResourceDAO.retrieve_information("alarm"),
            "locker": await ResourceDAO.retrieve_information("locker")
        }
        
        # Turn off pump and alarm
        if resource_status["pump"] is not None and resource_status["pump"].status != "off":
            await CoAPClient(resource_status["pump"], "off").run()
            print("Water pump turned off.")
        if resource_status["alarm"] is not None and resource_status["alarm"].status != "off":
            await CoAPClient(resource_status["alarm"], "off").run()
            print("Alarm turned off.")

        # Turn off the locker if it is connected only if H2S is no more detected, otherwise keep it on
        if resource_status["locker"] is not None:
            if self.types["H2S"].value is not None and int(self.types["H2S"].value) == 1:
                print("H2S still detected, waiting for it to be no more detected before turning off locker...")
                # Mantaining air fans active to drain the gas                
                if resource_status["fans"] is not None:
                    print("Draining H2S using air fans...")
                    if resource_status["fans"].status != "exhaust":
                        await CoAPClient(resource_status["fans"], "exhaust").run()
                # Periodically checking H2S presence
                while self.types["H2S"].value is not None and int(self.types["H2S"].value) == 1:
                    await asyncio.sleep(1)
                print("H2S no more detected, turning off locker!")
            await CoAPClient(resource_status["locker"], "off").run()
            print("Locker turned off.")
            if resource_status["fans"] is not None:
                await CoAPClient(resource_status["fans"], "off").run()
                print("Air fans turned off.")
        else:
            if resource_status["fans"] is not None and resource_status["fans"].status != "off":
                await CoAPClient(resource_status["fans"], "off").run()
                print("Air fans turned off.")

        self.initialize_sensors()

        self.running = False

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
            if self.stopping:
                await self.check_H2S()
            else:
                await self.check_values()
    
    async def check_H2S(self):
        '''
        Check the H2S value and manage the locker resource accordingly
        '''
        # Retrieve resource status
        resource_status = {
            "locker": await ResourceDAO.retrieve_information("locker")
        }
        # Manage locker if it is connected
        if resource_status["locker"] is not None:
            await self.manage_locker(resource_status["locker"])
    
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
                if self.types["H2S"].value == 1:
                    await CoAPClient(resource, "exhaust").run()
                return
            if self.types["H2S"].value is None:
                if self.types["temperature"].value > self.types["temperature"].max:
                    await CoAPClient(resource, "cooling").run()
                return

            # If temperature is too high and H2S is detected, turn on both fans
            if self.types["temperature"].value > self.types["temperature"].max and self.types["H2S"].value == 1:
                await CoAPClient(resource, "both").run()
            # If temperature is too high, turn on cooling fan
            elif self.types["temperature"].value > self.types["temperature"].max:
                await CoAPClient(resource, "cooling").run()
            # If H2S is detected, turn on exhaust fan
            elif self.types["H2S"].value == 1:
                await CoAPClient(resource, "exhaust").run()
        
        elif resource.status == "cooling":
            if self.types["temperature"].value is None:
                if self.types["H2S"].value == 1:
                    await CoAPClient(resource, "exhaust").run()
                else:
                    await CoAPClient(resource, "off").run()
                return
            if self.types["H2S"].value is None:
                if self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta:
                    await CoAPClient(resource, "off").run()
                return

            # If temperature is optimal, turn off the fan
            if self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta and self.types["H2S"].value == 0:
                await CoAPClient(resource, "off").run()
            # If temperature is still high and H2S is detected, turn on also exhaust fan
            elif self.types["temperature"].value >= self.types["temperature"].max - self.types["temperature"].delta and self.types["H2S"].value == 1:
                await CoAPClient(resource, "both").run()
            # If temperature is optimal but H2S is detected, turn on exhaust fan
            elif self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta and self.types["H2S"].value == 1:
                await CoAPClient(resource, "exhaust").run()
        
        elif resource.status == "exhaust":
            if self.types["temperature"].value is None:
                if self.types["H2S"].value == 0 or self.types["H2S"].value is None:
                    await CoAPClient(resource, "off").run()
                return
            if self.types["H2S"].value is None:
                if self.types["temperature"].value > self.types["temperature"].max:
                    await CoAPClient(resource, "cooling").run()
                return

            # If H2S is no more detected and temperature is normal, turn off the fan
            if self.types["H2S"].value == 0 and self.types["temperature"].value < self.types["temperature"].max:
                await CoAPClient(resource, "off").run()
            # If H2S is no more detected but temperature is too high, turn on cooling fan
            elif self.types["H2S"].value == 0 and self.types["temperature"].value > self.types["temperature"].max:
                await CoAPClient(resource, "cooling").run()
            # If H2S is still detected and temperature is too high, turn on both fans
            elif self.types["H2S"].value == 1 and self.types["temperature"].value > self.types["temperature"].max:
                await CoAPClient(resource, "both").run()
        
        elif resource.status == "both":
            if self.types["temperature"].value is None:
                if self.types["H2S"].value == 0 or self.types["H2S"].value is None:
                    await CoAPClient(resource, "off").run()
                return
            if self.types["H2S"].value is None:
                if self.types["temperature"].value > self.types["temperature"].max - self.types["temperature"].delta:
                    await CoAPClient(resource, "cooling").run()
                else:
                    await CoAPClient(resource, "off").run()
                return

            # If H2S is no more detected but temperature is still high, keep on the cooling fan
            if self.types["H2S"].value == 0 and self.types["temperature"].value > self.types["temperature"].max - self.types["temperature"].delta:
                await CoAPClient(resource, "cooling").run()
            # If H2S is no more detected and temperature is optimanl, turn off both fans
            elif self.types["H2S"].value == 0 and self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta:
                await CoAPClient(resource, "off").run()
            # If temperature is optimal but H2S is still detected, turn on exhaust fan
            elif self.types["H2S"].value == 1 and self.types["temperature"].value < self.types["temperature"].max - self.types["temperature"].delta:
                await CoAPClient(resource, "exhaust").run()

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
            if self.types["H2S"].value is None:
                return

            # If H2S is detected, turn on the locker
            if int(self.types["H2S"].value) == 1:
                await CoAPClient(resource, "on").run()
        
        elif resource.status == "on":
            if self.types["H2S"].value is None:
                await CoAPClient(resource, "off").run()
                return

            # If H2S is no more detected, turn off the locker
            if int(self.types["H2S"].value) == 0:
                await CoAPClient(resource, "off").run()
    