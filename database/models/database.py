import mysql.connector
from mysql.connector import Error
import json
import os

# Get the absolute path of the directory of the current file
dir_path = os.path.dirname(os.path.realpath(__file__))

class Database:
    '''
    Database class is a singleton class that handles the MySQL database connection.
    
    Attributes:
        instance: Database object
        connection: Database connection object
        credentials: MySQL credentials
        
    Methods:
        connect: Connect to the MySQL database
    '''
    
    connection = None

    def __new__(cls):
        '''
        Singleton pattern to ensure only one instance of the Database class is created
        :param cls: Database class
        :return: Database object
        '''
        if not hasattr(cls, 'instance'):
            cls.instance = super(Database, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        '''
        Constructor for Database
        :return: None
        '''
        return
    
    def connect(self):
        '''
        Connect to the MySQL database
        :return: Database connection object
        '''
        # Return the connection object if it already exists
        if self.connection is not None:
            return self.connection
        
        # Database connection setup
        else:
            try:
                # import credentials.key file to get MySQL credentials
                with open(os.path.join(dir_path, "../private/credential.json"), "r") as file:
                    self.credentials = json.load(file)

                self.connection = mysql.connector.connect(host= self.credentials["MYSQL_HOST"],
                                                user= self.credentials["MYSQL_USER"],
                                                password= self.credentials["MYSQL_PASSWORD"],
                                                database= self.credentials["MYSQL_DATABASE"])
                
                if self.connection.is_connected():
                    print("Connected to MySQL database")
                
                return self.connection
            
            except Error as e:
                print(f"Error connecting to MySQL database: {e}")
                return None


    def __del__(self):
        '''
        Destructor for Database
        :return: None
        '''
        if self.connection is not None:
            self.connection.close()
            print("MySQL connection closed")
    