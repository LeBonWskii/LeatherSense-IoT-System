import asyncio
from components.CLI import CLI
from components.CLI import ShutDownRequest

async def main():
    try:
        cli_task = asyncio.create_task(CLI().start())
        await cli_task
    except ShutDownRequest:
        print("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
