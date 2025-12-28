# ShivamNox/utils/keepalive.py

import asyncio
import aiohttp
import logging
from ShivamNox.vars import Var

# Suppress aiohttp warnings
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

async def ping_server():
    """
    Keep-alive function to prevent Render/Heroku from sleeping
    """
    # Wait for initial stabilization
    await asyncio.sleep(30)  # Wait 30 seconds before first ping
    
    sleep_time = 300  # 5 minutes between pings (was probably too frequent)
    
    while True:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                url = f"https://{Var.FQDN}/" if hasattr(Var, 'FQDN') and Var.FQDN else None
                
                if url:
                    async with session.get(url) as resp:
                        logger.debug(f"Keep-alive ping: {resp.status}")
                        
        except asyncio.CancelledError:
            break
        except Exception as e:
            # Don't log connection errors as they're expected sometimes
            logger.debug(f"Keep-alive ping failed (normal): {e}")
        
        await asyncio.sleep(sleep_time)
