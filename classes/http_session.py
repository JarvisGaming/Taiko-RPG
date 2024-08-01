import aiohttp


class HttpSession:
    """The HTTP session reused across all requests."""
    
    interface: aiohttp.ClientSession
    
    async def start_http_session(self):
        self.interface = aiohttp.ClientSession(connector=aiohttp.TCPConnector())
    
    async def close_http_session(self):
        if not self.interface.closed:
            await self.interface.close()

http_session = HttpSession()