import os
import time
from database.models.database import Database
from models.observer import ObserveSensor
from mysql.connector import Error
from coapthon.client.helperclient import HelperClient

def listOfcommands():
    print("\n|----- AVAILABLE COMMANDS -----|")
    print("| 1. exit                      |")
    print("|------------------------------|\n")

if __name__ == "__main__":

    print(r'''
  _                  _    _                  ____                          
 | |     ___   __ _ | |_ | |__    ___  _ __ / ___|   ___  _ __   ___   ___ 
 | |    / _ \ / _` || __|| '_ \  / _ \| '__|\___ \  / _ \| '_ \ / __| / _ \
 | |___|  __/| (_| || |_ | | | ||  __/| |    ___) ||  __/| | | |\__ \|  __/
 |_____|\___| \__,_| \__||_| |_| \___||_|   |____/  \___||_| |_||___/ \___|
                                                                                                                                                                           
''')

    listOfcommands()
    start = 0

    try:
        while 1:
            command = input("COMMAND> ")
            command = command.lower()

            if command == "help":
                listOfcommands()
            elif command == "exit":
                print("Exiting...")
                break
            else:
                print("Invalid command. Type 'help' for available commands.")

    except KeyboardInterrupt:
        print("SHUTDOWN")
        os._exit(0)