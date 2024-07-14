import json
import asyncio
import aiocoap.resource as resource
import aiocoap
import sys

class CoAPClient:

    def __init__(self, resource_dao, payload):
        self.resource_dao = resource_dao
        self.payload = payload

    async def run(self):
        context = await aiocoap.Context.create_client_context()

        uri = f"coap://{self.resource_dao.get_ip()}/{self.resource_dao.get_resource()}"
        payload_dict = {"action": self.payload}

        request = aiocoap.Message(code=aiocoap.PUT, uri=uri, payload=json.dumps(payload_dict).encode('utf-8'))
        request.opt.accept = aiocoap.numbers.media_types_rev['application/json']

        try:
            response = await context.request(request).response

            if response.code == aiocoap.CHANGED:
                await self.resource_dao.update_status(self.payload)
            elif response.code == aiocoap.BAD_REQUEST:
                print("\nInternal application error!", file=sys.stderr)
            elif response.code == aiocoap.BAD_OPTION:
                print("\nBAD_OPTION error", file=sys.stderr)
            else:
                print(f"\n{self.resource_dao.get_resource()} error changing to {self.payload}!", file=sys.stderr)
                await self.resource_dao.update_status("Error")
        
        except Exception as e:
            print(f"\nFailed to fetch resource: {e}", file=sys.stderr)