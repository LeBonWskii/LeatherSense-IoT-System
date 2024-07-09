from mysql.connector import Error
from coapthon.resources.resource import Resource
from models.database import Database
from actuator_data import actuators
import json

''' This module contains the Control class which is a CoAP resource that handles GET requests for actuator control. '''


class Control(Resource):
    '''
    Control class is a CoAP resource that handles GET requests for actuator control.

    Attributes:
        database: Database object
        connection: Database connection object

    Methods:
        render_GET: Handle GET requests for the resource
        fetch_actuator_from_db: Fetch actuator details from the database
    '''

    def __init__(self, name="Control"):
        '''
        Constructor for Control
        :param name: Name of the resource
        :return: None
        '''
        print("Control Resource")
        # Initialize the resource
        super(Control, self).__init__(name)
        self.payload = "Control Resource"
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
        print("GET Control Resource: " + request.source + " with payload " + str(request.payload))
        
        # Fetch actuator details from the database
        try:
            ip_port = request.source
            type = request.uri_query  # The actuator type is passed as query parameter

            if actuator_type in self.actuators:
                self.fetch_actuator_from_db(actuator_type)
                self.payload = "Control Successful"
            else:
                print(f"Actuator type {actuator_type} not found")
                self.payload = None
        
        # Handle errors
        except (Error, json.JSONDecodeError) as e:
            print(f"Error processing control request: {e}")
            self.payload = None
        
        return self
    
    def fetch_actuator_from_db(self, type):
        '''
        Fetch actuator details from the database
        :param type: Actuator type
        :return: None
        '''
        print(f"Fetching actuator data for type: {type}")

        # Check if database connection is active
        if not self.connection.is_connected():
            self.payload = None
            print("Database connection lost, Payload: None")
            return self
        
        # Fetch actuator details from the database
        try:
            cursor = self.connection.cursor()
            select_actuator_query = """
            SELECT ip_address, type, status
            FROM sensor
            WHERE type = %s
            """
            cursor.execute(select_actuator_query, (type,))
            actuator_data = cursor.fetchall()
            cursor.close()

            # Prepare response
            if actuator_data:
                for row in actuator_data:
                    ip_address, type, status = row
                    if status == 1:
                        response = {
                            "actuator": type,
                            "ip_address": ip_address
                        }
                        self.payload = json.dumps(response, separators=(',', ':'))
                        print(f"Payload: {self.payload}")
            
            # If no actuator found
            else:
                self.payload = None
                print(f"No actuator found for type: {type}. Payload: {self.payload}")
        
        # Handle errors
        except Error as e:
            self.payload = None
            print(f"Error retrieving actuator data: {e}, Payload: {self.payload}")
