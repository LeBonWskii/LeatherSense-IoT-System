import asyncio
from components.CLI import CLI
from components.CLI import ShutDownRequest
from components.PollingDB import PollingDB
from components.models.SO2Sensor import SO2Sensor
from components.models.TempSensor import TempSensor
from components.models.PHSensor import PHSensor
from components.models.SalinitySensor import SalinitySensor

async def main():
    types = {
        "SO2": SO2Sensor(),
        "temperature": TempSensor(),
        "pH": PHSensor(),
        "salinity": SalinitySensor()
    }
    try:
        cli_task = asyncio.create_task(CLI(types).start())
        polling_db_task = asyncio.create_task(PollingDB(types).start())
        await asyncio.gather(cli_task, polling_db_task)
    except ShutDownRequest:
        print("\nShutting down...")

if __name__ == "__main__":
    asyncio.run(main())
