import asyncio
from components.CLI import CLI
from components.PollingDB import PollingDB
from components.models import PHSensor, SalinitySensor, SO2Sensor, TempSensor

async def main():
    types = {
        "so2": SO2Sensor(),
        "temp": TempSensor(),
        "ph": PHSensor(),
        "salinity": SalinitySensor()
    }
    cli_task = asyncio.create_task(CLI(types).start())
    polling_db_task = asyncio.create_task(PollingDB(types).start())
    
    await asyncio.gather(cli_task, polling_db_task)

if __name__ == "__main__":
    asyncio.run(main())
