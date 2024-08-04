import sys
import os
import json
from coapthon.resources.resource import Resource
from coapthon.server.coap import CoAP
from coapthon.messages.response import Response
from coapthon.messages.request import Request
from coapthon import defines
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from database.models.database import Database
    
''' This module contains the Registration class which is a CoAP resource that handles GET requests for actuator registration. '''

class Registration(Resource):
    '''
    Registration class is a CoAP resource that handles GET requests for actuator registration.
    
    Attributes:
        database: Database object
        connection: Database connection object

    Methods:
        render_POST: Handle GET requests for the resource
        register_actuator: Register an actuator in the database and create an observer for it
        insert_actuator: Insert a new actuator into the database
    '''

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
        self.connection = self.database.connect()
    
    def render_POST(self, request):
        '''
        Handle POST requests for the resource
        :param request: Request object
        :return: Resource object
        '''

        # Parse the payload
        try:
            payload = json.loads(request.payload)
        
        # Handle JSON parsing errors
        except json.JSONDecodeError:
            print("Invalid JSON format")
            self.code = defines.Codes.BAD_REQUEST.number
            self.payload = "Invalid JSON format"
            return self
        
        # Insert actuator into the database
        if "name" in payload and "status" in payload:
            self.code = self.insert_actuator(payload["name"], request.source, payload["status"])
        else:
            print("Invalid payload")
            self.code = defines.Codes.BAD_REQUEST.number

        self.destination = request.source
        return self
    
    def insert_actuator(self, type, ip_port, status):
        '''
        Insert a new actuator into the database
        :param type: Type of sensor
        :param ip_port: IP address and port number of the sensor
        :return: None
        '''
        print(f"Inserting {type} actuator at {ip_port} into the database (initial status: {status})")

        # Insert node info into Actuator table if not already present
        try:
            # Check if database connection is still active
            if self.connection and self.connection.is_connected():
                cursor = self.connection.cursor()

                # Insert actuator into the database or reset status if already present
                insert_node_query = """
                INSERT INTO actuator (ip_address, type, status) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE  ip_address = %s, type = %s, status = %s;
                """
                cursor.execute(insert_node_query, (ip_port[0], type, status, ip_port[0], type, status))   # Starting status is off
                self.connection.commit()

                # Check if the actuator was inserted successfully
                if cursor.rowcount < 0:
                    print("Actuator not inserted")
                    cursor.close()
                    return defines.Codes.INTERNAL_SERVER_ERROR.number
                
                # Return the success response code
                else:
                    cursor.close()
                    return defines.Codes.CREATED.number
                
            # Return internal server error if database connection is lost
            else:
                print("Database connection lost")
                return defines.Codes.INTERNAL_SERVER_ERROR.number
        
        # Handle database errors
        except Exception as e:
            print(f"Error inserting actuator into the database: {e}")
            return defines.Codes.INTERNAL_SERVER_ERROR.number
