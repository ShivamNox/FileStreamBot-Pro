import asyncio
import aiohttp
import logging
from ShivamNox.vars import Var

logger = logging.getLogger(__name__)

async def ping_server():
    """Keep-alive to prevent Render from sleeping"""
    
    # Initial delay
    await asyncio.sleep(30)
    
    url = f"https://{Var.FQDN}/" if Var.FQDN else None
    
    if not url:
        logger.warning("No FQDN set, keep-alive disabled")
        return
    
    logger.info(f"🏓 Keep-alive started for {url}")
    
    while True:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    logger.debug(f"Keep-alive ping: {resp.status}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Keep-alive error (normal): {e}")
        
        await asyncio.sleep(300)  # 5 minutes
