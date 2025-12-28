import asyncio
import logging
import aiohttp
from ShivamNox.vars import Var

logger = logging.getLogger(__name__)


async def ping_server():
    """Keep server alive"""
    # Wait for server to start
    await asyncio.sleep(30)
    
    sleep_time = getattr(Var, 'PING_INTERVAL', 300)
    url = getattr(Var, 'URL', None)
    
    if not url:
        return
    
    logger.info(f"Keep-alive started for {url}")
    
    while True:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    logger.debug(f"Ping: {resp.status}")
        except:
            pass
        
        await asyncio.sleep(sleep_time)
