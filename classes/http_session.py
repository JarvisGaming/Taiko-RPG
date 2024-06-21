import aiohttp


class HttpSession:
    """The HTTP session reused across all requests."""
    
    conn: aiohttp.ClientSession
    
    async def start_http_session(self):
        self.conn = aiohttp.ClientSession()