import asyncio
from components.CLI import CLI
from components.PollingDB import PollingDB

async def main():
    cli_task = asyncio.create_task(CLI().start())
    polling_db_task = asyncio.create_task(PollingDB().start())
    
    await asyncio.gather(cli_task, polling_db_task)

if __name__ == "__main__":
    asyncio.run(main())
