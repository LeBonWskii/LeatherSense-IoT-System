import mysql.connector
from coapthon.server.coap import CoAP
from resources.registration import Registration
from resources.control import Control
import json
from models.database import Database

class CoAPServer(CoAP):

    def __init__(self, host, port):
        '''
        Constructor for CoAPServer

        :param host: Host IP address
        :param port: Port number

        :return: None
        '''

        # Initialize CoAP server
        CoAP.__init__(self, (host, port))
        print("CoAP server start on " + host + ":" + str(port))

        # Initialize database
        self.db = Database()
        self.connection = self.db.connect()
        self.initialize_resources()
        self.add_resource("register/", Registration("Registration"))
        self.add_resource("control/", Control("Control"))

    def initialize_resources(self):
        '''
        Initialize resources list in the database
        :return: None
        '''
        # Check if database connection is still active
        if not self.connection.is_connected():
            print("Database connection lost")
            return
        # Initialize resources list
        try:
            cursor = self.connection.cursor()
            initialize_resources_query = "TRUNCATE TABLE sensor"
            cursor.execute(initialize_resources_query)
            self.connection.commit()
            cursor.close()
        # Handle database errors
        except Error as e:
            print(f"Error truncating sensor table: {e}")
    
    def close(self):
        '''
        Close the CoAP server
        :return: None
        '''
        # Close CoAP server
        super(CoAPServer, self).close()
        print("CoAP server closed")
