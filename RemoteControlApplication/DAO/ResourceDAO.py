from database.models.database import Database
from mysql.connector import Error

class ResourceDAO:
    '''
    This class is used to interact with the database and retrieve information about the actuators.

    Attributes:
        ip (str): The IP address of the actuator.
        resource (str): The resource of the actuator.
        status (str): The status of the actuator.
    '''

    prefix = "actuator_"
    _db = Database()
    _connection = db.connect_db()

    def __init__(self, ip, resource, status=None):
        self.ip = ip
        self.resource = "{}{}".format(self.prefix, resource)
        self.status = status

    @staticmethod
    def retrieve_information(actuator):
        try:
            # Check if database connection is still active
            if not _connection.is_connected():
                print("Database connection lost")
                return None
            
            # Initialize resources list
            cursor = _connection.cursor()
            query = '''
                SELECT ip, status 
                FROM actuators 
                WHERE resource = %s 
                LIMIT 1;
            '''
            cursor.execute(query, (resource,))
            _connection.commit()
            cursor.close()

            # Fetch the result
            result = cursor.fetchone()
            if result is None:
                return None
            else:
                return ResourceDAO(result[0], resource, result[1])
        
        except Error as e:
            print(f"[ResourceDAO] Error: {e}")
            return None

    def update_status(self, new_status):
        if new_status == self.status:
            return

        try:
            # Check if database connection is still active
            if not _connection.is_connected():
                print("Database connection lost")
                return None
            
            cursor = _connection.cursor()
            query = '''
                UPDATE actuators 
                SET status = %s 
                WHERE ip = %s AND resource = %s;
            '''
            cursor.execute(query, (new_status, self.ip, self.resource))
            _connection.commit()
            row_changed = cursor.rowcount
            cursor.close()

            if row_changed == 0:
                    raise Exception()
            else:
                self.status = new_status
        
        except Error as e:
            print(f"Cannot connect the database! Error: {e}")
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
