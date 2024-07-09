
from mysql.connector import Error
from coapthon.resources.resource import Resource
import json
from models.database import Database
from actuator_data import actuators
    
''' This module contains the Registration class which is a CoAP resource that handles GET requests for actuator registration. '''

class Registration(Resource):
    '''
    Registration class is a CoAP resource that handles GET requests for actuator registration.
    
    Attributes:
        database: Database object
        connection: Database connection object

    Methods:
        render_GET: Handle GET requests for the resource
        register_actuator: Register an actuator in the database and create an observer for it
        insert_actuator: Insert a new actuator into the database
    '''

    COAP_PORT = 5683

    def __init__(self, name="Registration", coap_server=None):
        '''
        Constructor for Registration
        :param name: Name of the resource
        :param coap_server: CoAP server object
        :return: None
        '''
        print("Registration Resource")
        # Initialize the resource
        super(Registration, self).__init__(name, coap_server, visible=True, observable=True, allow_children=True)
        self.payload = "Registration Resource"
        # Initialize the database
        self.database = Database()
        self.connection = self.database.connect_db()
        self.actuators = actuators
    
    def render_GET(self, request):
        '''
        Handle GET requests for the resource
        :param request: Request object
        :return: Resource object
        '''
        print("GET Registration Resource from " + request.source + " with payload " + str(request.payload))
        
        try:
            ip_port = request.source
            actuator_type = request.payload
            # Check if actuator type is valid
            if actuator_type in self.actuators:
                # Register the actuator
                self.register_actuator(actuator_type, ip_port)
                self.payload = "Registration Successful"
            else:
                # Return error message if actuator type is invalid
                print(f"Actuator type {actuator_type} not found")
                self.payload = None
        
        # Handle exceptions
        except Exception as e:
            print(f"Error processing registration: {e}")
            self.payload = None
        
        return self
    
    def register_actuator(self, type, ip_port):
        '''
        Register an actuator in the database and create an observer for it
        :param type: Type of actuator
        :param ip_port: IP address and port number of the actuator
        :return: None
        '''
        print(f"Registering {type} actuator at {ip_port}")

        # Insert the actuator into the database
        self.insert_actuator(type, ip_port)
        print(f"Registered {type} actuator at {ip_port}")
    
    def insert_actuator(self, type, ip_port):
        '''
        Insert a new actuator into the database
        :param type: Type of sensor
        :param ip_port: IP address and port number of the sensor
        :return: None
        '''
        print(f"Inserting {type} actuator at {ip_port} into the database")
        # Insert node info into Actuator table if not already present
        try:
            # Check if database connection is still active
            if self.connection and self.connection.is_connected():
                cursor = self.connection.cursor()
                insert_node_query = """
                INSERT INTO sensor (ip_address, type, status) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE  ip_address = %s, type = %s, status = %s
                """
                cursor.execute(insert_node_query, (ip_port[0], type, 1, ip_port[0], type, 1))
                self.connection.commit()
                cursor.close()
        # Handle database errors
        except Error as e:
            print(f"Error registering actuator: {e}")
