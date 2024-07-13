import json
import asyncio
import aiohttp
import sys
sys.path.append("../..")
from DAO.ResourceDAO import ResourceDAO

class CoAPClient:

    def __init__(self, resource_dao, payload):
        self.resource_dao = resource_dao
        self.payload = payload

    async def run(self):
        uri = f"coap://{self.resource_dao.get_ip()}/{self.resource_dao.get_resource()}"
        payload_dict = {"action": self.payload}

        async with aiohttp.ClientSession() as session:
            async with session.put(uri, json=payload_dict) as response:
                code = response.status

                if code == 204:  # 2.04 CHANGED
                    await self.resource_dao.update_status(self.payload)
                elif code == 400:  # 4.00 BAD REQUEST
                    print("Internal application error!", file=sys.stderr)
                elif code == 402:  # 4.02 BAD OPTION
                    print("BAD_OPTION error", file=sys.stderr)
                else:
                    print("Actuator error!", file=sys.stderr)
                    await self.resource_dao.change_status("Error")
