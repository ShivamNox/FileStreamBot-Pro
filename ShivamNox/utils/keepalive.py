# Keep-alive service for Render/Heroku

import asyncio
import logging
import aiohttp
from ShivamNox.vars import Var

logger = logging.getLogger(__name__)


async def ping_server():
    """Keep server alive by pinging periodically"""
    
    # Wait for server to fully start before pinging
    logger.info("💓 Keep-alive: Waiting 30s for server to stabilize...")
    await asyncio.sleep(30)
    
    sleep_time = getattr(Var, 'PING_INTERVAL', 300)  # Default 5 minutes
    url = getattr(Var, 'URL', None)
    
    if not url:
        logger.warning("💓 Keep-alive: No URL configured, disabled")
        return
    
    logger.info(f"💓 Keep-alive: Started for {url}")
    
    while True:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    logger.debug(f"💓 Keep-alive ping: {resp.status}")
        except asyncio.CancelledError:
            logger.info("💓 Keep-alive: Stopped")
            break
        except asyncio.TimeoutError:
            logger.debug("💓 Keep-alive: Timeout (normal)")
        except Exception as e:
            logger.debug(f"💓 Keep-alive error: {e}")
        
        await asyncio.sleep(sleep_time)
