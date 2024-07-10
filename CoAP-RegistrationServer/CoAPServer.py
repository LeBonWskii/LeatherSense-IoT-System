from coapthon.server.coap import CoAP
from resources.Registration import Registration
from database.models.database import Database

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
        self.add_resource("registration/", Registration("Registration"))

    def initialize_resources(self):
        '''
        Initialize resources list in the database
        :return: None
        '''
        print("Initializing resources")

        # Check if database connection is still active
        if not self.connection.is_connected():
            print("Database connection lost")
            return
        
        # Initialize resources list
        try:
            cursor = self.connection.cursor()
            initialize_resources_query = "TRUNCATE TABLE actuator"
            cursor.execute(initialize_resources_query)
            self.connection.commit()
            cursor.close()
        
        # Handle database errors
        except Error as e:
            print(f"Error truncating actuator table: {e}")
    
    def close(self):
        '''
        Close the CoAP server
        :return: None
        '''
        
        # Close CoAP server
        super(CoAPServer, self).close()
        print("CoAP server closed")
