import aiohttp


class HttpSession:
    """The HTTP session reused across all requests."""
    
    conn: aiohttp.ClientSession
    
    async def start_http_session(self):
        self.conn = aiohttp.ClientSession(connector=aiohttp.TCPConnector())
    
    async def close_http_session(self):
        if not self.conn.closed:
            await self.conn.close()

http_session = HttpSession()