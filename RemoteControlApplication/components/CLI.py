import os
import time

class CLI:

    async def start(self):

        '''
        This method is used to start the CLI application.
        '''

        print(r'''
            _                  _    _                  ____                          
            | |     ___   __ _ | |_ | |__    ___  _ __ / ___|   ___  _ __   ___   ___ 
            | |    / _ \ / _` || __|| '_ \  / _ \| '__|\___ \  / _ \| '_ \ / __| / _ \
            | |___|  __/| (_| || |_ | | | ||  __/| |    ___) ||  __/| | | |\__ \|  __/
            |_____|\___| \__,_| \__||_| |_| \___||_|   |____/  \___||_| |_||___/ \___|
                                                                                                                                                                                    
        ''')

        CommandList()
        start = 0

        try:
            while 1:
                command = await asyncio.get_event_loop().run_in_executor(None, input)
                await self.handleCommand(command.lower())

        except KeyboardInterrupt:
            print("SHUTDOWN")
            os._exit(0)
    
    async def handleCommand(self, command):
        if command == "configure":
            await self.configure()
        elif command == "status":
            await self.status()
        elif command == "monitor":
            await self.monitor()
        elif command == "help":
            await self.help()
        elif command == "exit":
            print("Exiting...")
            break
        else:
            print("Invalid command. Type 'help' for available commands.")
    
    def CommandList():
        print("\n|----- AVAILABLE COMMANDS -----|")
        print("| 1. configure                 |")
        print("| 2. status                    |")
        print("| 3. monitor                   |")
        print("| 4. help                      |")
        print("| 5. exit                      |")
        print("|------------------------------|\n")
    
    def configure():
        print("\n|----- CONFIGURE ACTUATOR -----|")
        print("| Enter the range for actuator activation.")
        print("|----------------------------------|")
        print("| 1. Enter the minimum value: ")
        min_value = input()
        print("| 2. Enter the maximum value: ")
        max_value = input()
        print("|----------------------------------|")
        print("| Configuration successful.")
        print("|----------------------------------|\n")

    def status():
        print("\n|----- ACTUATOR STATUS -----|")
        print("| Actuator is currently: ON")
        print("|----------------------------|\n")

    def monitor():
        print("\n|----- SENSOR VALUES -----|")
        print("| Temperature: 25.0 C")
        print("| Humidity: 50.0 %")
        print("| Light: 1000 lux")
        print("|-------------------------|\n")

    def help():
        print("\n|----- COMMAND EXPLANATION -----|")
        print("| 1. configure - Configure ranges for actuator activation.")
        print("| 2. status    - Check the actuator status.")
        print("| 3. monitor   - Monitor the sensor values.")
        print("| 4. help      - Display the description of available commands.")
        print("| 5. exit      - Exit the CLI application.")
        print("|--------------------------------|\n")
