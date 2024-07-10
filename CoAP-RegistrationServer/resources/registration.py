
from coapthon.resources.resource import Resource
from coapthon.server.coap import CoAP
from coapthon.messages.response import Response
from coapthon.messages.request import Request
from coapthon import defines
import json
from mysql.connector import Error
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
    
    def render_POST(self, request):
        '''
        Handle POST requests for the resource
        :param request: Request object
        :return: Resource object
        '''
        print("POST Registration Resource: " + request.source + " with payload " + str(request.payload))

        response = Response()

        # Parse the payload
        try:
            payload = json.loads(request.payload)
        
        # Handle JSON parsing errors
        except json.JSONDecodeError:
            response.code = defines.Codes.BAD_REQUEST.number
            response.payload = "Invalid JSON format"
            return response
        
        # Insert actuator into the database
        if "name" in payload and "status" in payload:
            response.code = self.insert_actuator(payload["name"], request.source)
        else:
            response.code = defines.Codes.BAD_REQUEST.number
        
        return response
    
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

                # Insert actuator into the database or reset status if already present
                insert_node_query = """
                INSERT INTO actuator (ip_address, type, status) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE  ip_address = %s, type = %s, status = %s
                """
                cursor.execute(insert_node_query, (ip_port[0], type, "off", ip_port[0], type, "off"))   # Starting status is off
                self.connection.commit()
                cursor.close()

                # Check if the actuator was inserted successfully
                if cursor.rowcount < 1:
                    return defines.Codes.INTERNAL_SERVER_ERROR.number
                
                # Return the success response code
                else:
                    return defines.Codes.CREATED.number
                cursor.close()
            
            # Return internal server error if database connection is lost
            else:
                return defines.Codes.INTERNAL_SERVER_ERROR.number
        
        # Handle database errors
        except Error as e:
            print(f"Error inserting actuator into the database: {e}")
            return defines.Codes.INTERNAL_SERVER_ERROR.number
