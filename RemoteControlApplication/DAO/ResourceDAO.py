import sys
import asyncio
from mysql.connector import Error
sys.path.append("..")
from database.models.database import Database

class ResourceDAO:
    '''
    This class is used to interact with the database and retrieve information about the actuators.

    Attributes:
        ip (str): The IP address of the actuator.
        resource (str): The resource of the actuator.
        status (str): The status of the actuator.
    '''

    def __init__(self, ip, resource, status=None):
        self.ip = ip
        self.resource = resource
        self.status = status

    @staticmethod
    async def retrieve_information(actuator):


        try:

            database = Database()
            connection = database.connect()
            prefix = "actuator_"
            
            # Initialize resources list
            cursor = connection.cursor()
            query = '''
                SELECT ip_address, status 
                FROM actuator
                WHERE type = %s 
                LIMIT 1;
            '''
            cursor.execute(query, ((prefix + actuator),))
            # Fetch the result
            result = cursor.fetchone()
            cursor.close()
            connection.commit()

            if result is None:
                return None
            else:
                return ResourceDAO(result[0], (prefix + actuator), result[1])
        
        except Error as e:
            print(f"[ResourceDAO] Error: {e}")
            return None
        except asyncio.CancelledError:
            return None
        except Exception as e:
            print(f"[ResourceDAO] Error: {e}")
            return None

    async def update_status(self, new_status):
        if new_status == self.status:
            return

        try:
            
            database = Database()
            connection = database.connect()
            
            cursor = connection.cursor()
            query = '''
                UPDATE actuator
                SET status = %s 
                WHERE ip_address = %s AND type = %s;
            '''
            cursor.execute(query, (new_status, self.ip, self.resource))
            row_changed = cursor.rowcount
            cursor.close()
            connection.commit()

            if row_changed == 0:
                print(f"Error updating the status to {new_status}")
            else:
                self.status = new_status
        
        except Error as e:
            print(f"Cannot connect the database! Error: {e}")
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"Error while updating the status on the DB! Error: {e}")
    
    def get_ip(self):
        return f"[{self.ip}]"

    def get_resource(self):
        return self.resource

    def get_status(self):
        return self.status

    def __str__(self):
        return f"Actuator status{{\n\tip = [{self.ip}],\n\tresource = '{self.resource}',\n\tstatus = '{self.status}'\n}}"
